from typing import Dict, Any
from app.browser_adapters.chrome import ChromeBrowserAdapter

class EdgeBrowserAdapter(ChromeBrowserAdapter):
    """
    Forensic parser for Microsoft Edge (Chromium-based).
    Inherits Chromium storage structures while customizing Edge-specific metadata,
    identification, and profile context.
    """

    browser_name = "EDGE"
    parser_version = "1.2.0"

    def get_browser_metadata(self) -> Dict[str, Any]:
        meta = super().get_browser_metadata()
        meta["browser_flavor"] = "Microsoft Edge (Chromium)"
        meta["edge_features"] = "SmartScreen & Collections enabled profile"
        return meta
