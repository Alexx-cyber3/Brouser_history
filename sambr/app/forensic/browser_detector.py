import os
import configparser
from pathlib import Path
from typing import List, Dict, Any, Optional

class BrowserDetector:
    """
    Forensic browser and profile detector.
    Supports Windows standard locations and arbitrary forensic directory images.
    """

    @staticmethod
    def get_system_browser_paths() -> Dict[str, Optional[Path]]:
        local_app_data = os.environ.get("LOCALAPPDATA")
        app_data = os.environ.get("APPDATA")

        paths: Dict[str, Optional[Path]] = {
            "CHROME": None,
            "EDGE": None,
            "FIREFOX": None
        }

        if local_app_data:
            chrome_p = Path(local_app_data) / "Google" / "Chrome" / "User Data"
            if chrome_p.exists():
                paths["CHROME"] = chrome_p

            edge_p = Path(local_app_data) / "Microsoft" / "Edge" / "User Data"
            if edge_p.exists():
                paths["EDGE"] = edge_p

        if app_data:
            firefox_p = Path(app_data) / "Mozilla" / "Firefox"
            if firefox_p.exists():
                paths["FIREFOX"] = firefox_p

        return paths

    @classmethod
    def detect_chromium_profiles(cls, user_data_dir: Path) -> List[Dict[str, Any]]:
        """Scan a Chromium user data directory for profile directories."""
        profiles = []
        if not user_data_dir.exists() or not user_data_dir.is_dir():
            return profiles

        # Check 'Default' profile
        default_dir = user_data_dir / "Default"
        if default_dir.is_dir() and cls._is_chromium_profile_dir(default_dir):
            profiles.append({
                "profile_name": "Default",
                "display_name": "Default Profile",
                "path": str(default_dir),
                "artifacts": cls._catalog_chromium_artifacts(default_dir)
            })

        # Check 'Profile X' or other numbered subdirs
        try:
            for item in user_data_dir.iterdir():
                if item.is_dir() and item.name.startswith("Profile ") and cls._is_chromium_profile_dir(item):
                    profiles.append({
                        "profile_name": item.name,
                        "display_name": item.name,
                        "path": str(item),
                        "artifacts": cls._catalog_chromium_artifacts(item)
                    })
        except Exception:
            pass

        # If user selected profile directory directly (e.g. evidence points straight to Default)
        if not profiles and cls._is_chromium_profile_dir(user_data_dir):
            profiles.append({
                "profile_name": user_data_dir.name,
                "display_name": f"{user_data_dir.name} (Direct)",
                "path": str(user_data_dir),
                "artifacts": cls._catalog_chromium_artifacts(user_data_dir)
            })

        return profiles

    @classmethod
    def detect_firefox_profiles(cls, firefox_dir: Path) -> List[Dict[str, Any]]:
        """Scan Firefox directory using profiles.ini or directory scanning."""
        profiles = []
        if not firefox_dir.exists() or not firefox_dir.is_dir():
            return profiles

        profiles_ini = firefox_dir / "profiles.ini"
        if profiles_ini.is_file():
            try:
                config = configparser.ConfigParser()
                config.read(profiles_ini, encoding="utf-8")
                for section in config.sections():
                    if section.startswith("Profile") or section.startswith("Install"):
                        name = config.get(section, "Name", fallback=section)
                        path_str = config.get(section, "Path", fallback=None)
                        is_relative = config.get(section, "IsRelative", fallback="1") == "1"

                        if path_str:
                            prof_path = (firefox_dir / path_str) if is_relative else Path(path_str)
                            if prof_path.is_dir() and cls._is_firefox_profile_dir(prof_path):
                                profiles.append({
                                    "profile_name": name,
                                    "display_name": f"Firefox: {name}",
                                    "path": str(prof_path),
                                    "artifacts": cls._catalog_firefox_artifacts(prof_path)
                                })
            except Exception:
                pass

        # Fallback directory walk under 'Profiles'
        profiles_subdir = firefox_dir / "Profiles"
        if profiles_subdir.is_dir():
            try:
                for item in profiles_subdir.iterdir():
                    if item.is_dir() and cls._is_firefox_profile_dir(item):
                        if not any(p["path"] == str(item) for p in profiles):
                            profiles.append({
                                "profile_name": item.name,
                                "display_name": f"Firefox Profile: {item.name}",
                                "path": str(item),
                                "artifacts": cls._catalog_firefox_artifacts(item)
                            })
            except Exception:
                pass

        # If user pointed directly to a profile folder
        if not profiles and cls._is_firefox_profile_dir(firefox_dir):
            profiles.append({
                "profile_name": firefox_dir.name,
                "display_name": f"Firefox: {firefox_dir.name} (Direct)",
                "path": str(firefox_dir),
                "artifacts": cls._catalog_firefox_artifacts(firefox_dir)
            })

        return profiles

    @classmethod
    def identify_evidence_source(cls, source_path: Path | str) -> Dict[str, Any]:
        """
        Given any path, determines browser type, profiles, and available artifacts.
        """
        p = Path(source_path)
        result: Dict[str, Any] = {
            "valid": False,
            "browser_type": "UNKNOWN",
            "path": str(p),
            "profiles": [],
            "message": ""
        }

        if not p.exists():
            result["message"] = f"Specified path does not exist: {p}"
            return result

        # Heuristic 1: Firefox detection
        if (p / "places.sqlite").exists() or (p / "profiles.ini").exists() or (p / "Profiles").exists():
            ff_profiles = cls.detect_firefox_profiles(p)
            if ff_profiles:
                result["valid"] = True
                result["browser_type"] = "FIREFOX"
                result["profiles"] = ff_profiles
                result["message"] = f"Detected Mozilla Firefox with {len(ff_profiles)} profile(s)."
                return result

        # Heuristic 2: Chromium detection (Chrome vs Edge)
        # Check if "Edge" is in the path
        path_str = str(p).lower()
        is_edge = "edge" in path_str
        browser_type = "EDGE" if is_edge else "CHROME"

        chromium_profiles = cls.detect_chromium_profiles(p)
        if chromium_profiles:
            result["valid"] = True
            result["browser_type"] = browser_type
            result["profiles"] = chromium_profiles
            result["message"] = f"Detected {browser_type} with {len(chromium_profiles)} profile(s)."
            return result

        result["message"] = "Unable to identify browser profile signatures in the provided directory."
        return result

    @staticmethod
    def _is_chromium_profile_dir(p: Path) -> bool:
        indicators = ["History", "Cookies", "Bookmarks", "Preferences", "Network/Cookies", "Web Data"]
        return any((p / ind).exists() for ind in indicators)

    @staticmethod
    def _catalog_chromium_artifacts(p: Path) -> Dict[str, Optional[str]]:
        artifacts: Dict[str, Optional[str]] = {}
        mapping = {
            "history": "History",
            "cookies": "Network/Cookies" if (p / "Network" / "Cookies").exists() else "Cookies",
            "bookmarks": "Bookmarks",
            "preferences": "Preferences",
            "sessions": "Sessions",
            "cache": "Cache"
        }
        for key, rel in mapping.items():
            full = p / rel
            artifacts[key] = str(full) if full.exists() else None
        return artifacts

    @staticmethod
    def _is_firefox_profile_dir(p: Path) -> bool:
        indicators = ["places.sqlite", "cookies.sqlite", "prefs.js", "sessionstore.jsonlz4", "key4.db"]
        return any((p / ind).exists() for ind in indicators)

    @staticmethod
    def _catalog_firefox_artifacts(p: Path) -> Dict[str, Optional[str]]:
        artifacts: Dict[str, Optional[str]] = {}
        mapping = {
            "places": "places.sqlite",
            "cookies": "cookies.sqlite",
            "sessions": "sessionstore.jsonlz4" if (p / "sessionstore.jsonlz4").exists() else "sessionstore-backups",
            "preferences": "prefs.js",
            "cache": "cache2"
        }
        for key, rel in mapping.items():
            full = p / rel
            artifacts[key] = str(full) if full.exists() else None
        return artifacts
