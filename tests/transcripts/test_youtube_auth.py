from __future__ import annotations

import stat
from http.cookiejar import Cookie, CookieJar

import pytest

from chew.transcripts.youtube_auth import YouTubeAuthError, YouTubeAuthStore


def _cookie(domain: str, name: str, value: str) -> Cookie:
    return Cookie(
        version=0,
        name=name,
        value=value,
        port=None,
        port_specified=False,
        domain=domain,
        domain_specified=True,
        domain_initial_dot=domain.startswith("."),
        path="/",
        path_specified=True,
        secure=True,
        expires=None,
        discard=False,
        comment=None,
        comment_url=None,
        rest={},
        rfc2109=False,
    )


def _mixed_cookie_jar(_: str) -> CookieJar:
    jar = CookieJar()
    jar.set_cookie(_cookie(".youtube.com", "SID", "youtube-secret"))
    jar.set_cookie(_cookie(".example.com", "session", "not-youtube"))
    return jar


def test_connect_filters_non_youtube_domains_and_restricts_file_mode(
    tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("chew.transcripts.youtube_auth.extract_cookies_from_browser", _mixed_cookie_jar)

    path = YouTubeAuthStore(tmp_path).connect_from_browser("chrome")

    content = path.read_text(encoding="utf-8")
    assert ".youtube.com" in content
    assert "example.com" not in content
    assert "not-youtube" not in content
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_connect_rejects_unsupported_browser_without_creating_cookie_file(tmp_path) -> None:
    store = YouTubeAuthStore(tmp_path)

    with pytest.raises(YouTubeAuthError, match="Unsupported browser"):
        store.connect_from_browser("safari")

    assert store.cookie_file() is None


def test_connect_requires_youtube_login_cookie(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "chew.transcripts.youtube_auth.extract_cookies_from_browser",
        lambda _: CookieJar(),
    )

    with pytest.raises(YouTubeAuthError, match="No YouTube login cookies"):
        YouTubeAuthStore(tmp_path).connect_from_browser("chrome")


def test_clear_is_idempotent(tmp_path) -> None:
    store = YouTubeAuthStore(tmp_path)
    assert store.clear() is False
    store.cookie_path.parent.mkdir(parents=True)
    store.cookie_path.write_text("# Netscape HTTP Cookie File\n", encoding="utf-8")

    assert store.clear() is True
    assert store.clear() is False
