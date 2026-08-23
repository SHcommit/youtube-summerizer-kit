"""Non-secret local browser selection for authenticated YouTube captions."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

SUPPORTED_BROWSERS = frozenset({"chrome", "chromium", "firefox"})


class YouTubeAuthError(RuntimeError):
    """A user-actionable error while selecting a local YouTube browser profile."""


@dataclass(frozen=True, slots=True)
class YouTubeBrowserProfile:
    browser: str
    profile: str


class YouTubeAuthStore:
    """Persist browser/profile metadata only; browser credentials are never stored."""

    def __init__(self, data_directory: Path, *, home_directory: Path | None = None) -> None:
        self.profile_path = data_directory / "credentials" / "youtube-browser-profile.json"
        self.home_directory = home_directory or Path.home()

    def available_profiles(self, browser: str) -> tuple[str, ...]:
        """List Chromium profile names from metadata only, never from cookie storage."""

        normalized_browser = browser.lower().strip()
        if normalized_browser not in {"chrome", "chromium"}:
            return ("Default",)
        local_state = self._chromium_local_state_path(normalized_browser)
        if local_state is None or not local_state.is_file():
            return ("Default",)
        try:
            payload = json.loads(local_state.read_text(encoding="utf-8"))
            profiles = payload["profile"]["info_cache"]
        except (KeyError, TypeError, ValueError, OSError):
            return ("Default",)
        if not isinstance(profiles, dict):
            return ("Default",)
        names = tuple(sorted(name for name in profiles if isinstance(name, str) and name))
        return names or ("Default",)

    def _chromium_local_state_path(self, browser: str) -> Path | None:
        if sys.platform == "darwin":
            directory = "Google/Chrome" if browser == "chrome" else "Chromium"
            return self.home_directory / "Library" / "Application Support" / directory / "Local State"
        return None

    def connect_from_browser(self, browser: str, profile: str) -> YouTubeBrowserProfile:
        normalized_browser = browser.lower().strip()
        normalized_profile = profile.strip()
        if normalized_browser not in SUPPORTED_BROWSERS:
            choices = ", ".join(sorted(SUPPORTED_BROWSERS))
            raise YouTubeAuthError(f"Unsupported browser: {browser}. Choose one of: {choices}.")
        if not normalized_profile:
            raise YouTubeAuthError("Profile must not be empty.")
        selected = YouTubeBrowserProfile(browser=normalized_browser, profile=normalized_profile)
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                suffix=".json",
                prefix="youtube-browser-profile-",
                dir=self.profile_path.parent,
                delete=False,
            ) as temporary:
                temporary_path = Path(temporary.name)
                json.dump({"browser": selected.browser, "profile": selected.profile}, temporary, sort_keys=True)
                temporary.write("\n")
            temporary_path.chmod(0o600)
            temporary_path.replace(self.profile_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        return selected

    def profile(self) -> YouTubeBrowserProfile | None:
        if not self.profile_path.is_file():
            return None
        try:
            payload = json.loads(self.profile_path.read_text(encoding="utf-8"))
            browser = payload["browser"]
            profile = payload["profile"]
        except (KeyError, TypeError, ValueError, OSError):
            return None
        if not isinstance(browser, str) or not isinstance(profile, str):
            return None
        if browser not in SUPPORTED_BROWSERS or not profile:
            return None
        return YouTubeBrowserProfile(browser=browser, profile=profile)

    def clear(self) -> bool:
        if self.profile_path.is_file():
            self.profile_path.unlink()
            return True
        return False
