import os
import sqlite3
import json
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.browser_adapters.base import BaseBrowserAdapter
from app.forensic.timestamp_engine import ForensicTimestampEngine

class ChromeBrowserAdapter(BaseBrowserAdapter):
    """
    Forensic parser for Google Chrome and Chromium-based browsers.
    Extracts History, Downloads, Cookies metadata, Bookmarks, Preferences, and Cache.
    Strictly read-only; clones files to temporary workspace to bypass SQLite locking and WAL journal locks.
    """

    browser_name = "CHROME"
    parser_version = "1.2.0"

    def _safe_sqlite_query(self, db_file_rel: str, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """
        Safely query SQLite database in read-only mode.
        If locked or in use, copies database and WAL/SHM to a temp directory.
        """
        target_path = self.profile_path / db_file_rel
        if not target_path.exists():
            return []

        temp_dir = tempfile.mkdtemp(prefix="tracefusion_chr_")
        temp_db = Path(temp_dir) / target_path.name

        try:
            # Copy main db and WAL/SHM if they exist
            shutil.copy2(target_path, temp_db)
            wal_file = target_path.with_name(target_path.name + "-wal")
            shm_file = target_path.with_name(target_path.name + "-shm")
            if wal_file.exists():
                shutil.copy2(wal_file, temp_dir / wal_file.name)
            if shm_file.exists():
                shutil.copy2(shm_file, temp_dir / shm_file.name)

            uri_path = f"file:{temp_db.as_posix()}?mode=ro"
            conn = sqlite3.connect(uri_path, uri=True, timeout=5.0)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = [dict(row) for row in cursor.fetchall()]
            conn.close()
            return rows
        except Exception as e:
            self.record_warning(f"Error querying Chrome database '{db_file_rel}': {str(e)}")
            return []
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def parse_history(self) -> List[Dict[str, Any]]:
        """Extract browsing history events from the 'History' SQLite database."""
        events: List[Dict[str, Any]] = []

        query = """
            SELECT 
                v.id AS visit_id,
                u.id AS url_id,
                u.url,
                u.title,
                v.visit_time,
                u.visit_count,
                u.typed_count,
                v.transition,
                v.visit_duration
            FROM visits v
            JOIN urls u ON v.url = u.id
            ORDER BY v.visit_time DESC
        """
        rows = self._safe_sqlite_query("History", query)

        # Fallback if visits join fails (e.g. older schema or corrupted visits table)
        if not rows:
            fallback_query = "SELECT id AS url_id, url, title, last_visit_time AS visit_time, visit_count FROM urls WHERE last_visit_time > 0"
            rows = self._safe_sqlite_query("History", fallback_query)

        for row in rows:
            raw_time = row.get("visit_time")
            utc_dt, raw_str, warn = ForensicTimestampEngine.normalize_timestamp(raw_time, "CHROME")
            if warn:
                self.record_warning(warn)

            url = row.get("url") or ""
            domain = self.extract_domain(url)
            title = row.get("title") or domain or "Untitled Visit"

            metadata = {
                "visit_id": row.get("visit_id"),
                "url_id": row.get("url_id"),
                "visit_count": row.get("visit_count"),
                "typed_count": row.get("typed_count"),
                "transition": row.get("transition"),
                "visit_duration_microseconds": row.get("visit_duration")
            }

            events.append({
                "record_identifier": f"hist_{row.get('visit_id') or row.get('url_id')}",
                "browser": self.browser_name,
                "profile": self.profile_path.name,
                "artifact_type": "HISTORY",
                "event_type": "VISIT",
                "url": url,
                "domain": domain,
                "title": title,
                "timestamp_raw": raw_str,
                "timestamp_utc": utc_dt,
                "confidence": "DIRECT",
                "source_file": "History",
                "metadata": metadata
            })

        return events

    def parse_downloads(self) -> List[Dict[str, Any]]:
        """Extract file download events from 'History' downloads table."""
        events: List[Dict[str, Any]] = []

        query = """
            SELECT 
                d.id,
                d.guid,
                d.current_path,
                d.target_path,
                d.start_time,
                d.end_time,
                d.total_bytes,
                d.received_bytes,
                d.state,
                d.danger_type,
                d.interrupt_reason,
                d.mime_type,
                d.original_mime_type,
                d.tab_url,
                d.tab_referrer_url,
                (SELECT c.url FROM downloads_url_chains c WHERE c.id = d.id ORDER BY c.chain_index ASC LIMIT 1) AS chain_url
            FROM downloads d
            ORDER BY d.start_time DESC
        """
        rows = self._safe_sqlite_query("History", query)

        # Fallback if downloads_url_chains does not exist in schema
        if not rows:
            fallback_query = "SELECT id, target_path, start_time, end_time, total_bytes, state, mime_type, tab_url FROM downloads ORDER BY start_time DESC"
            rows = self._safe_sqlite_query("History", fallback_query)

        for row in rows:
            raw_start = row.get("start_time")
            utc_dt, raw_str, warn = ForensicTimestampEngine.normalize_timestamp(raw_start, "CHROME")
            if warn:
                self.record_warning(warn)

            target_path_str = row.get("target_path") or row.get("current_path") or "Unknown"
            filename = Path(target_path_str).name if target_path_str else "Downloaded File"
            download_url = row.get("chain_url") or row.get("tab_url") or ""
            domain = self.extract_domain(download_url)

            metadata = {
                "download_id": row.get("id"),
                "guid": row.get("guid"),
                "target_path": target_path_str,
                "total_bytes": row.get("total_bytes"),
                "received_bytes": row.get("received_bytes"),
                "state": row.get("state"),
                "referrer": row.get("tab_referrer_url"),
                "mime_type": row.get("mime_type") or row.get("original_mime_type")
            }

            events.append({
                "record_identifier": f"dl_{row.get('id')}",
                "browser": self.browser_name,
                "profile": self.profile_path.name,
                "artifact_type": "DOWNLOAD",
                "event_type": "DOWNLOAD",
                "url": download_url,
                "domain": domain,
                "title": f"Download: {filename}",
                "file_path": target_path_str,
                "file_size": row.get("total_bytes"),
                "mime_type": row.get("mime_type") or row.get("original_mime_type"),
                "timestamp_raw": raw_str,
                "timestamp_utc": utc_dt,
                "confidence": "DIRECT",
                "source_file": "History",
                "metadata": metadata
            })

        return events

    def parse_cookies(self) -> List[Dict[str, Any]]:
        """Extract cookie metadata without exposing or attempting to decrypt sensitive secrets."""
        events: List[Dict[str, Any]] = []

        cookie_rel_paths = ["Network/Cookies", "Cookies"]
        rows = []
        source_rel = "Cookies"
        for rel in cookie_rel_paths:
            if (self.profile_path / rel).exists():
                source_rel = rel
                query = """
                    SELECT 
                        host_key,
                        name,
                        path,
                        creation_utc,
                        expires_utc,
                        last_access_utc,
                        is_secure,
                        is_httponly,
                        samesite,
                        source_scheme
                    FROM cookies
                    ORDER BY creation_utc DESC
                """
                rows = self._safe_sqlite_query(rel, query)
                if rows:
                    break

        for idx, row in enumerate(rows):
            raw_time = row.get("creation_utc")
            utc_dt, raw_str, warn = ForensicTimestampEngine.normalize_timestamp(raw_time, "CHROME")

            host_key = row.get("host_key") or ""
            domain = host_key.lstrip(".")
            name = row.get("name") or f"cookie_{idx}"

            # Parse last access if present
            last_access_dt, _, _ = ForensicTimestampEngine.normalize_timestamp(row.get("last_access_utc"), "CHROME")
            expires_dt, _, _ = ForensicTimestampEngine.normalize_timestamp(row.get("expires_utc"), "CHROME")

            metadata = {
                "host_key": host_key,
                "name": name,
                "path": row.get("path"),
                "is_secure": bool(row.get("is_secure")),
                "is_httponly": bool(row.get("is_httponly")),
                "samesite": row.get("samesite"),
                "source_scheme": row.get("source_scheme"),
                "expires_utc": ForensicTimestampEngine.format_utc_iso(expires_dt),
                "last_access_utc": ForensicTimestampEngine.format_utc_iso(last_access_dt),
                "protection_status": "Encrypted/Protected"
            }

            events.append({
                "record_identifier": f"cookie_{domain}_{name}_{idx}",
                "browser": self.browser_name,
                "profile": self.profile_path.name,
                "artifact_type": "COOKIE",
                "event_type": "COOKIE_CREATED",
                "url": f"https://{domain}{row.get('path') or '/'}",
                "domain": domain,
                "title": f"Cookie: {name} ({domain})",
                "timestamp_raw": raw_str,
                "timestamp_utc": utc_dt,
                "is_encrypted": True,
                "confidence": "DIRECT",
                "source_file": source_rel,
                "metadata": metadata
            })

        return events

    def parse_bookmarks(self) -> List[Dict[str, Any]]:
        """Extract bookmarks hierarchy from the Bookmarks JSON file."""
        events: List[Dict[str, Any]] = []
        bm_file = self.profile_path / "Bookmarks"
        if not bm_file.exists():
            return events

        try:
            with open(bm_file, "r", encoding="utf-8", errors="ignore") as f:
                data = json.load(f)

            roots = data.get("roots", {})

            def _traverse(node: Dict[str, Any], folder_path: str = ""):
                node_type = node.get("type")
                if node_type == "url":
                    raw_time = node.get("date_added")
                    utc_dt, raw_str, _ = ForensicTimestampEngine.normalize_timestamp(raw_time, "CHROME")
                    url = node.get("url") or ""
                    title = node.get("name") or "Bookmark"
                    domain = self.extract_domain(url)

                    events.append({
                        "record_identifier": f"bm_{node.get('id', len(events))}",
                        "browser": self.browser_name,
                        "profile": self.profile_path.name,
                        "artifact_type": "BOOKMARK",
                        "event_type": "BOOKMARK_CREATED",
                        "url": url,
                        "domain": domain,
                        "title": title,
                        "timestamp_raw": raw_str,
                        "timestamp_utc": utc_dt,
                        "confidence": "DIRECT",
                        "source_file": "Bookmarks",
                        "metadata": {
                            "bookmark_id": node.get("id"),
                            "folder": folder_path,
                            "date_added_raw": raw_time,
                            "date_modified_raw": node.get("date_modified")
                        }
                    })
                elif node_type == "folder":
                    folder_name = node.get("name") or "Folder"
                    current_path = f"{folder_path}/{folder_name}".strip("/")
                    for child in node.get("children", []):
                        _traverse(child, current_path)

            for root_key, root_val in roots.items():
                if isinstance(root_val, dict):
                    root_name = root_val.get("name") or root_key
                    for child in root_val.get("children", []):
                        _traverse(child, root_name)

        except Exception as e:
            self.record_warning(f"Error parsing Chrome Bookmarks: {str(e)}")

        return events

    def parse_sessions(self) -> List[Dict[str, Any]]:
        """Extract recoverable open sessions and tabs metadata."""
        events: List[Dict[str, Any]] = []
        sessions_dir = self.profile_path / "Sessions"
        if not sessions_dir.exists() or not sessions_dir.is_dir():
            return events

        try:
            for item in sessions_dir.iterdir():
                if item.is_file() and (item.name.startswith("Session_") or item.name.startswith("Tabs_")):
                    stat = item.stat()
                    mod_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                    events.append({
                        "record_identifier": f"sess_{item.name}",
                        "browser": self.browser_name,
                        "profile": self.profile_path.name,
                        "artifact_type": "SESSION",
                        "event_type": "SESSION_OPENED",
                        "url": None,
                        "domain": None,
                        "title": f"Session Store: {item.name}",
                        "file_path": str(item),
                        "file_size": stat.st_size,
                        "timestamp_raw": str(stat.st_mtime),
                        "timestamp_utc": mod_dt,
                        "confidence": "DERIVED",
                        "source_file": f"Sessions/{item.name}",
                        "metadata": {
                            "session_file": item.name,
                            "file_size": stat.st_size,
                            "last_modified": mod_dt.isoformat(),
                            "status": "Binary session store detected"
                        }
                    })
        except Exception as e:
            self.record_warning(f"Error inspecting Chrome Sessions: {str(e)}")

        return events

    def parse_cache(self) -> List[Dict[str, Any]]:
        """Extract cache metadata entries."""
        events: List[Dict[str, Any]] = []
        cache_dir = self.profile_path / "Cache" / "Cache_Data"
        if not cache_dir.exists():
            cache_dir = self.profile_path / "Cache"

        if not cache_dir.exists() or not cache_dir.is_dir():
            return events

        try:
            index_file = cache_dir / "index"
            count = 0
            for item in cache_dir.iterdir():
                if item.is_file() and count < 100: # Index up to 100 primary cache entries for analysis
                    stat = item.stat()
                    mod_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                    events.append({
                        "record_identifier": f"cache_{item.name}",
                        "browser": self.browser_name,
                        "profile": self.profile_path.name,
                        "artifact_type": "CACHE",
                        "event_type": "CACHE_ACTIVITY",
                        "url": None,
                        "domain": None,
                        "title": f"Cache Block: {item.name}",
                        "file_path": str(item),
                        "file_size": stat.st_size,
                        "timestamp_raw": str(stat.st_mtime),
                        "timestamp_utc": mod_dt,
                        "confidence": "DIRECT",
                        "source_file": f"Cache/{item.name}",
                        "metadata": {
                            "cache_file": item.name,
                            "file_size": stat.st_size,
                            "status": "Cache entry metadata extracted"
                        }
                    })
                    count += 1
        except Exception as e:
            self.record_warning(f"Error inspecting Chrome Cache: {str(e)}")

        return events

    def get_browser_metadata(self) -> Dict[str, Any]:
        """Extract browser profile metadata and preferences."""
        meta: Dict[str, Any] = {
            "browser": self.browser_name,
            "profile_name": self.profile_path.name,
            "profile_path": str(self.profile_path)
        }
        pref_file = self.profile_path / "Preferences"
        if pref_file.exists():
            try:
                with open(pref_file, "r", encoding="utf-8", errors="ignore") as f:
                    data = json.load(f)
                    meta["account_info"] = data.get("account_info", [])
                    meta["download_default_directory"] = data.get("download", {}).get("default_directory")
                    meta["extensions"] = list(data.get("extensions", {}).get("settings", {}).keys())
            except Exception as e:
                self.record_warning(f"Error reading Preferences: {str(e)}")
        return meta
