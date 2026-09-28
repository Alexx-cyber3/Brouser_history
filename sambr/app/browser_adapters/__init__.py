from app.browser_adapters.base import BaseBrowserAdapter
from app.browser_adapters.chrome import ChromeBrowserAdapter
from app.browser_adapters.edge import EdgeBrowserAdapter
from app.browser_adapters.firefox import FirefoxBrowserAdapter

def get_adapter_for_browser(browser_type: str, profile_path) -> BaseBrowserAdapter:
    b = (browser_type or "").upper()
    if b in ("CHROME", "GOOGLE CHROME"):
        return ChromeBrowserAdapter(profile_path)
    elif b in ("EDGE", "MICROSOFT EDGE"):
        return EdgeBrowserAdapter(profile_path)
    elif b in ("FIREFOX", "MOZILLA FIREFOX"):
        return FirefoxBrowserAdapter(profile_path)
    else:
        # Default fallback to Chromium adapter
        return ChromeBrowserAdapter(profile_path)

__all__ = [
    "BaseBrowserAdapter",
    "ChromeBrowserAdapter",
    "EdgeBrowserAdapter",
    "FirefoxBrowserAdapter",
    "get_adapter_for_browser"
]
