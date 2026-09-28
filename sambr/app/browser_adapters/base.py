from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse

class BaseBrowserAdapter(ABC):
    """
    Standardized abstract base adapter for browser forensic parsers.
    Ensures consistent extraction across Chrome, Edge, Firefox, and future browser additions.
    """

    browser_name: str = "GENERIC"
    parser_version: str = "1.0.0"

    def __init__(self, profile_path: Path | str):
        self.profile_path = Path(profile_path)
        self.warnings: List[str] = []

    def record_warning(self, msg: str):
        self.warnings.append(msg)

    @staticmethod
    def extract_domain(url: Optional[str]) -> Optional[str]:
        """Safely extract hostname/domain from URL."""
        if not url:
            return None
        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split("/")[0]
            # Strip port if present
            if ":" in domain:
                domain = domain.split(":")[0]
            return domain.lower() if domain else None
        except Exception:
            return None

    @abstractmethod
    def parse_history(self) -> List[Dict[str, Any]]:
        """Extract browsing history events."""
        pass

    @abstractmethod
    def parse_downloads(self) -> List[Dict[str, Any]]:
        """Extract file download events."""
        pass

    @abstractmethod
    def parse_cookies(self) -> List[Dict[str, Any]]:
        """Extract cookie metadata (without decrypting secrets)."""
        pass

    @abstractmethod
    def parse_bookmarks(self) -> List[Dict[str, Any]]:
        """Extract bookmark hierarchy and records."""
        pass

    @abstractmethod
    def parse_sessions(self) -> List[Dict[str, Any]]:
        """Extract recoverable open sessions and tabs."""
        pass

    @abstractmethod
    def parse_cache(self) -> List[Dict[str, Any]]:
        """Extract cache index and metadata entries."""
        pass

    @abstractmethod
    def get_browser_metadata(self) -> Dict[str, Any]:
        """Extract profile preferences and browser metadata."""
        pass

    def collect_all_artifacts(self) -> Dict[str, List[Dict[str, Any]]]:
        """Convenience method to execute all parsers with graceful fault-tolerance."""
        results: Dict[str, List[Dict[str, Any]]] = {
            "history": [],
            "downloads": [],
            "cookies": [],
            "bookmarks": [],
            "sessions": [],
            "cache": []
        }

        try:
            results["history"] = self.parse_history()
        except Exception as e:
            self.record_warning(f"History parsing failure: {str(e)}")

        try:
            results["downloads"] = self.parse_downloads()
        except Exception as e:
            self.record_warning(f"Downloads parsing failure: {str(e)}")

        try:
            results["cookies"] = self.parse_cookies()
        except Exception as e:
            self.record_warning(f"Cookies parsing failure: {str(e)}")

        try:
            results["bookmarks"] = self.parse_bookmarks()
        except Exception as e:
            self.record_warning(f"Bookmarks parsing failure: {str(e)}")

        try:
            results["sessions"] = self.parse_sessions()
        except Exception as e:
            self.record_warning(f"Sessions parsing failure: {str(e)}")

        try:
            results["cache"] = self.parse_cache()
        except Exception as e:
            self.record_warning(f"Cache parsing failure: {str(e)}")

        return results
