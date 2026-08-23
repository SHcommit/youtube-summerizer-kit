"""Explicit, local-only YouTube browser-session storage for caption retrieval."""

from __future__ import annotations

import os
from collections.abc import Callable
from http.cookiejar import Cookie, CookieJar, MozillaCookieJar
from importlib import import_module
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import cast

SUPPORTED_BROWSERS = frozenset({"chrome", "chromium", "firefox"})


class YouTubeAuthError(RuntimeError):
    """A user-actionable error while connecting a local YouTube session."""


def extract_cookies_from_browser(browser: str) -> CookieJar:
    """Load yt-dlp only when the optional login operation is requested."""

    try:
        extractor = cast(Callable[[str], CookieJar], import_module("yt_dlp.cookies").extract_cookies_from_browser)
    except ImportError as error:
        raise YouTubeAuthError("yt-dlp is required. Install: pip install 'youtube-summarizer-kit[youtube]'") from error
    return extractor(browser)


def _is_youtube_domain(domain: str) -> bool:
    normalized = domain.lstrip(".").lower()
    return normalized == "youtube.com" or normalized.endswith(".youtube.com")


def _write_netscape_cookie_file(destination: Path, cookies: list[Cookie]) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".txt",
            prefix="youtube-cookies-",
            dir=destination.parent,
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
        jar = MozillaCookieJar(str(temporary_path))
        for cookie in cookies:
            jar.set_cookie(cookie)
        jar.save(ignore_discard=True, ignore_expires=True)
        temporary_path.chmod(0o600)
        temporary_path.replace(destination)
        temporary_path = None
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)


class YouTubeAuthStore:
    """Own the filtered, local credential used only by yt-dlp caption requests."""

    def __init__(self, data_directory: Path) -> None:
        self.cookie_path = data_directory / "credentials" / "youtube-cookies.txt"

    def connect_from_browser(self, browser: str) -> Path:
        if browser not in SUPPORTED_BROWSERS:
            choices = ", ".join(sorted(SUPPORTED_BROWSERS))
            raise YouTubeAuthError(f"Unsupported browser: {browser}. Choose one of: {choices}.")
        try:
            browser_cookies = extract_cookies_from_browser(browser)
        except YouTubeAuthError:
            raise
        except Exception as error:
            raise YouTubeAuthError(
                f"Could not access {browser} cookies. Close the browser and try again, or set youtube_cookie_file manually."
            ) from error
        cookies = [cookie for cookie in browser_cookies if _is_youtube_domain(cookie.domain)]
        if not cookies:
            raise YouTubeAuthError("No YouTube login cookies found. Sign in at youtube.com, then try again.")
        _write_netscape_cookie_file(self.cookie_path, cookies)
        os.chmod(self.cookie_path, 0o600)
        return self.cookie_path

    def cookie_file(self) -> Path | None:
        return self.cookie_path if self.cookie_path.is_file() else None

    def clear(self) -> bool:
        if self.cookie_path.is_file():
            self.cookie_path.unlink()
            return True
        return False
