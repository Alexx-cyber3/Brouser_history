import sqlite3
import shutil
import tempfile
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from app.browser_adapters.base import BaseBrowserAdapter
from app.forensic.timestamp_engine import ForensicTimestampEngine

class FirefoxBrowserAdapter(BaseBrowserAdapter):
    """
    Forensic parser for Mozilla Firefox.
    Extracts History, Bookmarks, and Downloads from 'places.sqlite',
    Cookies metadata from 'cookies.sqlite', Sessions, and Cache.
    Strictly read-only; clones database files to temporary directories to prevent locking.
    """

    browser_name = "FIREFOX"
    parser_version = "1.2.0"

    def _safe_sqlite_query(self, db_file_rel: str, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        target_path = self.profile_path / db_file_rel
        if not target_path.exists():
            return []

        temp_dir = tempfile.mkdtemp(prefix="tracefusion_ff_")
        temp_db = Path(temp_dir) / target_path.name

        try:
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
            self.record_warning(f"Error querying Firefox database '{db_file_rel}': {str(e)}")
            return []
        finally:
            try:
                shutil.rmtree(temp_dir, ignore_errors=True)
            except Exception:
                pass

    def parse_history(self) -> List[Dict[str, Any]]:
        """Extract browsing history events from places.sqlite."""
        events: List[Dict[str, Any]] = []

        query = """
            SELECT 
                v.id AS visit_id,
                p.id AS place_id,
                p.url,
                p.title,
                v.visit_date,
                p.visit_count,
                v.visit_type
            FROM moz_historyvisits v
            JOIN moz_places p ON v.place_id = p.id
            WHERE v.visit_type != 7 -- exclude downloads
            ORDER BY v.visit_date DESC
        """
        rows = self._safe_sqlite_query("places.sqlite", query)

        if not rows:
            # Fallback query
            fallback_query = """
                SELECT id AS place_id, url, title, last_visit_date AS visit_date, visit_count 
                FROM moz_places 
                WHERE last_visit_date > 0 
                ORDER BY last_visit_date DESC
            """
            rows = self._safe_sqlite_query("places.sqlite", fallback_query)

        for row in rows:
            raw_time = row.get("visit_date")
            utc_dt, raw_str, warn = ForensicTimestampEngine.normalize_timestamp(raw_time, "FIREFOX")
            if warn:
                self.record_warning(warn)

            url = row.get("url") or ""
            domain = self.extract_domain(url)
            title = row.get("title") or domain or "Untitled Visit"

            metadata = {
                "visit_id": row.get("visit_id"),
                "place_id": row.get("place_id"),
                "visit_count": row.get("visit_count"),
                "visit_type": row.get("visit_type")
            }

            events.append({
                "record_identifier": f"ff_hist_{row.get('visit_id') or row.get('place_id')}",
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
                "source_file": "places.sqlite",
                "metadata": metadata
            })

        return events

    def parse_downloads(self) -> List[Dict[str, Any]]:
        """Extract download events from places.sqlite (visit_type = 7) or moz_annos."""
        events: List[Dict[str, Any]] = []

        # In Firefox, visit_type = 7 indicates a download event in moz_historyvisits
        query = """
            SELECT 
                v.id AS visit_id,
                p.id AS place_id,
                p.url,
                p.title,
                v.visit_date
            FROM moz_historyvisits v
            JOIN moz_places p ON v.place_id = p.id
            WHERE v.visit_type = 7
            ORDER BY v.visit_date DESC
        """
        rows = self._safe_sqlite_query("places.sqlite", query)

        for row in rows:
            raw_time = row.get("visit_date")
            utc_dt, raw_str, warn = ForensicTimestampEngine.normalize_timestamp(raw_time, "FIREFOX")
            if warn:
                self.record_warning(warn)

            url = row.get("url") or ""
            domain = self.extract_domain(url)
            filename = url.split("/")[-1] if "/" in url else "Download"

            events.append({
                "record_identifier": f"ff_dl_{row.get('visit_id')}",
                "browser": self.browser_name,
                "profile": self.profile_path.name,
                "artifact_type": "DOWNLOAD",
                "event_type": "DOWNLOAD",
                "url": url,
                "domain": domain,
                "title": f"Download: {filename}",
                "file_path": filename,
                "timestamp_raw": raw_str,
                "timestamp_utc": utc_dt,
                "confidence": "DIRECT",
                "source_file": "places.sqlite",
                "metadata": {
                    "visit_id": row.get("visit_id"),
                    "place_id": row.get("place_id"),
                    "download_url": url
                }
            })

        return events

    def parse_cookies(self) -> List[Dict[str, Any]]:
        """Extract cookie metadata from cookies.sqlite without exposing secrets."""
        events: List[Dict[str, Any]] = []

        query = """
            SELECT 
                id,
                name,
                host,
                path,
                expiry,
                lastAccessed,
                creationTime,
                isSecure,
                isHttpOnly,
                sameSite
            FROM moz_cookies
            ORDER BY creationTime DESC
        """
        rows = self._safe_sqlite_query("cookies.sqlite", query)

        for row in rows:
            raw_time = row.get("creationTime")
            utc_dt, raw_str, _ = ForensicTimestampEngine.normalize_timestamp(raw_time, "FIREFOX")

            host = row.get("host") or ""
            domain = host.lstrip(".")
            name = row.get("name") or "cookie"

            # Parse expiry (Unix seconds in Firefox) and lastAccessed (PRTime)
            exp_dt, _, _ = ForensicTimestampEngine.normalize_timestamp(row.get("expiry"), "UNIX")
            acc_dt, _, _ = ForensicTimestampEngine.normalize_timestamp(row.get("lastAccessed"), "FIREFOX")

            metadata = {
                "cookie_id": row.get("id"),
                "name": name,
                "host": host,
                "path": row.get("path"),
                "is_secure": bool(row.get("isSecure")),
                "is_httponly": bool(row.get("isHttpOnly")),
                "sameSite": row.get("sameSite"),
                "expires_utc": ForensicTimestampEngine.format_utc_iso(exp_dt),
                "last_access_utc": ForensicTimestampEngine.format_utc_iso(acc_dt),
                "protection_status": "Encrypted/Protected"
            }

            events.append({
                "record_identifier": f"ff_cookie_{row.get('id')}",
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
                "source_file": "cookies.sqlite",
                "metadata": metadata
            })

        return events

    def parse_bookmarks(self) -> List[Dict[str, Any]]:
        """Extract bookmarks from places.sqlite."""
        events: List[Dict[str, Any]] = []

        query = """
            SELECT 
                b.id,
                b.title,
                p.url,
                b.dateAdded,
                b.lastModified,
                b.parent
            FROM moz_bookmarks b
            LEFT JOIN moz_places p ON b.fk = p.id
            WHERE b.type = 1 AND p.url IS NOT NULL
            ORDER BY b.dateAdded DESC
        """
        rows = self._safe_sqlite_query("places.sqlite", query)

        for row in rows:
            raw_time = row.get("dateAdded")
            utc_dt, raw_str, _ = ForensicTimestampEngine.normalize_timestamp(raw_time, "FIREFOX")

            url = row.get("url") or ""
            domain = self.extract_domain(url)
            title = row.get("title") or domain or "Bookmark"

            events.append({
                "record_identifier": f"ff_bm_{row.get('id')}",
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
                "source_file": "places.sqlite",
                "metadata": {
                    "bookmark_id": row.get("id"),
                    "parent_folder_id": row.get("parent"),
                    "date_added_raw": raw_time,
                    "date_modified_raw": row.get("lastModified")
                }
            })

        return events

    def parse_sessions(self) -> List[Dict[str, Any]]:
        """Extract recoverable session metadata."""
        events: List[Dict[str, Any]] = []
        candidates = [
            self.profile_path / "sessionstore.jsonlz4",
            self.profile_path / "sessionstore-backups" / "recovery.jsonlz4",
            self.profile_path / "sessionstore-backups" / "previous.jsonlz4"
        ]

        for cand in candidates:
            if cand.exists():
                try:
                    stat = cand.stat()
                    mod_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                    events.append({
                        "record_identifier": f"ff_sess_{cand.name}",
                        "browser": self.browser_name,
                        "profile": self.profile_path.name,
                        "artifact_type": "SESSION",
                        "event_type": "SESSION_OPENED",
                        "url": None,
                        "domain": None,
                        "title": f"Firefox Session: {cand.name}",
                        "file_path": str(cand),
                        "file_size": stat.st_size,
                        "timestamp_raw": str(stat.st_mtime),
                        "timestamp_utc": mod_dt,
                        "confidence": "DERIVED",
                        "source_file": cand.name,
                        "metadata": {
                            "session_file": cand.name,
                            "file_size": stat.st_size,
                            "last_modified": mod_dt.isoformat(),
                            "compression": "Mozilla LZ4 container"
                        }
                    })
                except Exception as e:
                    self.record_warning(f"Error reading session file {cand.name}: {str(e)}")

        return events

    def parse_cache(self) -> List[Dict[str, Any]]:
        """Extract cache metadata from cache2 directory."""
        events: List[Dict[str, Any]] = []
        cache_entries_dir = self.profile_path / "cache2" / "entries"
        if not cache_entries_dir.exists() or not cache_entries_dir.is_dir():
            return events

        try:
            count = 0
            for item in cache_entries_dir.iterdir():
                if item.is_file() and count < 100:
                    stat = item.stat()
                    mod_dt = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
                    events.append({
                        "record_identifier": f"ff_cache_{item.name}",
                        "browser": self.browser_name,
                        "profile": self.profile_path.name,
                        "artifact_type": "CACHE",
                        "event_type": "CACHE_ACTIVITY",
                        "url": None,
                        "domain": None,
                        "title": f"Cache Entry: {item.name}",
                        "file_path": str(item),
                        "file_size": stat.st_size,
                        "timestamp_raw": str(stat.st_mtime),
                        "timestamp_utc": mod_dt,
                        "confidence": "DIRECT",
                        "source_file": f"cache2/entries/{item.name}",
                        "metadata": {
                            "cache_key": item.name,
                            "file_size": stat.st_size
                        }
                    })
                    count += 1
        except Exception as e:
            self.record_warning(f"Error inspecting Firefox cache2: {str(e)}")

        return events

    def get_browser_metadata(self) -> Dict[str, Any]:
        return {
            "browser": self.browser_name,
            "profile_name": self.profile_path.name,
            "profile_path": str(self.profile_path),
            "flavor": "Mozilla Firefox Gecko"
        }
