from __future__ import annotations

import json

import pytest

from chew.transcripts.youtube_auth import YouTubeAuthError, YouTubeAuthStore, YouTubeBrowserProfile


def test_connect_stores_only_selected_browser_profile(tmp_path) -> None:
    store = YouTubeAuthStore(tmp_path)

    profile = store.connect_from_browser("chrome", "Default")

    assert profile == YouTubeBrowserProfile(browser="chrome", profile="Default")
    assert store.profile() == profile
    assert json.loads(store.profile_path.read_text(encoding="utf-8")) == {
        "browser": "chrome",
        "profile": "Default",
    }


def test_chrome_profiles_are_listed_from_non_secret_local_state(tmp_path) -> None:
    chrome_state = tmp_path / "Library" / "Application Support" / "Google" / "Chrome" / "Local State"
    chrome_state.parent.mkdir(parents=True)
    chrome_state.write_text(
        json.dumps({"profile": {"info_cache": {"Profile 6": {}, "Profile 10": {}}}}),
        encoding="utf-8",
    )

    profiles = YouTubeAuthStore(tmp_path, home_directory=tmp_path).available_profiles("chrome")

    assert profiles == ("Profile 10", "Profile 6")


def test_connect_rejects_unsupported_browser_without_creating_profile(tmp_path) -> None:
    store = YouTubeAuthStore(tmp_path)

    with pytest.raises(YouTubeAuthError, match="Unsupported browser"):
        store.connect_from_browser("safari", "Default")

    assert store.profile() is None


def test_connect_rejects_an_empty_profile(tmp_path) -> None:
    with pytest.raises(YouTubeAuthError, match="Profile must not be empty"):
        YouTubeAuthStore(tmp_path).connect_from_browser("chrome", " ")


def test_clear_is_idempotent(tmp_path) -> None:
    store = YouTubeAuthStore(tmp_path)
    assert store.clear() is False
    store.connect_from_browser("firefox", "default-release")

    assert store.clear() is True
    assert store.clear() is False
