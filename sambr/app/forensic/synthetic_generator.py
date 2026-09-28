import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List

# Epoch conversion constants
CHROME_EPOCH_DIFF_MICROS = 11644473600000000

def dt_to_chrome_epoch(dt: datetime) -> int:
    unix_sec = dt.replace(tzinfo=timezone.utc).timestamp()
    return int(unix_sec * 1000000) + CHROME_EPOCH_DIFF_MICROS

def dt_to_firefox_epoch(dt: datetime) -> int:
    unix_sec = dt.replace(tzinfo=timezone.utc).timestamp()
    return int(unix_sec * 1000000)

class SyntheticForensicEvidenceGenerator:
    """
    Generates realistic, synthetically populated browser evidence directories
    for Chrome, Edge, and Firefox.
    All data is clearly labeled as synthetic/fictional for testing and demonstration.
    """

    @classmethod
    def generate_all(cls, base_dir: Path | str) -> Dict[str, Path]:
        base = Path(base_dir)
        base.mkdir(parents=True, exist_ok=True)

        chrome_path = base / "synthetic_chrome_profile"
        edge_path = base / "synthetic_edge_profile"
        firefox_path = base / "synthetic_firefox_profile"

        cls.create_chromium_profile(chrome_path, "Google Chrome", "Default")
        cls.create_chromium_profile(edge_path, "Microsoft Edge", "Default")
        cls.create_firefox_profile(firefox_path, "Mozilla Firefox", "profile.default-release")

        return {
            "CHROME": chrome_path,
            "EDGE": edge_path,
            "FIREFOX": firefox_path
        }

    @classmethod
    def create_chromium_profile(cls, profile_dir: Path, browser_name: str, profile_name: str = "Default"):
        profile_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)

        # 1. History SQLite DB
        hist_db = profile_dir / "History"
        if hist_db.exists():
            hist_db.unlink()

        conn = sqlite3.connect(hist_db)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE urls (
                id INTEGER PRIMARY KEY,
                url TEXT,
                title TEXT,
                visit_count INTEGER DEFAULT 0,
                typed_count INTEGER DEFAULT 0,
                last_visit_time INTEGER DEFAULT 0,
                hidden INTEGER DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE TABLE visits (
                id INTEGER PRIMARY KEY,
                url INTEGER,
                visit_time INTEGER NOT NULL,
                from_visit INTEGER,
                transition INTEGER DEFAULT 0,
                segment_id INTEGER DEFAULT 0,
                visit_duration INTEGER DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE TABLE downloads (
                id INTEGER PRIMARY KEY,
                guid TEXT,
                current_path TEXT,
                target_path TEXT,
                start_time INTEGER NOT NULL,
                end_time INTEGER NOT NULL,
                total_bytes INTEGER NOT NULL,
                received_bytes INTEGER NOT NULL,
                state INTEGER DEFAULT 1,
                danger_type INTEGER DEFAULT 0,
                interrupt_reason INTEGER DEFAULT 0,
                mime_type TEXT,
                original_mime_type TEXT,
                tab_url TEXT,
                tab_referrer_url TEXT
            )
        """)

        cur.execute("""
            CREATE TABLE downloads_url_chains (
                id INTEGER,
                chain_index INTEGER,
                url TEXT
            )
        """)

        # Insert realistic synthetic URLs and visits
        urls_data = [
            (1, "https://cloud-portal.demo-corp.internal/login", "Internal Corp Portal Login", 3, 1),
            (2, "https://secure-vault.demo-corp.internal/api/v1/tokens", "Vault Token Management", 2, 0),
            (3, "https://github.com/synthetic-sec/incident-response-toolkit", "Incident Response Toolkit Repo", 5, 2),
            (4, "https://malicious-paste.demo-leak.net/raw/leak_9481.txt", "Raw Document Paste Dump", 1, 0),
            (5, "https://file-share.demo-cloud.net/download?id=payroll_2026.xlsx", "Payroll Spreadsheet 2026", 1, 0),
            (6, "https://search-engine.demo/search?q=how+to+clear+browser+cache", "Search: Clear browser cache", 2, 1)
        ]

        for u in urls_data:
            dt_visit = now - timedelta(hours=(10 - u[0]), minutes=u[0] * 7)
            t_chrome = dt_to_chrome_epoch(dt_visit)
            cur.execute("INSERT INTO urls VALUES (?, ?, ?, ?, ?, ?, 0)", (u[0], u[1], u[2], u[3], u[4], t_chrome))
            cur.execute("INSERT INTO visits VALUES (?, ?, ?, 0, 805306368, 0, 15000000)", (u[0], u[0], t_chrome))

        # Insert synthetic download
        dl_time = dt_to_chrome_epoch(now - timedelta(hours=3, minutes=12))
        dl_end = dt_to_chrome_epoch(now - timedelta(hours=3, minutes=10))
        cur.execute("""
            INSERT INTO downloads VALUES (
                1, 'c25091a1-872f-41e1-b4d4-28b96d92ec32',
                'C:\\Users\\Investigator\\Downloads\\payroll_2026.xlsx',
                'C:\\Users\\Investigator\\Downloads\\payroll_2026.xlsx',
                ?, ?, 1048576, 1048576, 1, 0, 0,
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'https://file-share.demo-cloud.net/download?id=payroll_2026.xlsx',
                'https://cloud-portal.demo-corp.internal/login'
            )
        """, (dl_time, dl_end))

        cur.execute("INSERT INTO downloads_url_chains VALUES (1, 0, 'https://file-share.demo-cloud.net/download?id=payroll_2026.xlsx')")

        conn.commit()
        conn.close()

        # 2. Cookies SQLite DB
        cookie_db = profile_dir / "Cookies"
        if cookie_db.exists():
            cookie_db.unlink()

        conn_c = sqlite3.connect(cookie_db)
        cur_c = conn_c.cursor()
        cur_c.execute("""
            CREATE TABLE cookies (
                creation_utc INTEGER NOT NULL,
                host_key TEXT NOT NULL,
                top_frame_site_key TEXT DEFAULT '',
                name TEXT NOT NULL,
                value TEXT NOT NULL,
                encrypted_value BLOB,
                path TEXT NOT NULL,
                expires_utc INTEGER NOT NULL,
                is_secure INTEGER NOT NULL,
                is_httponly INTEGER NOT NULL,
                last_access_utc INTEGER NOT NULL,
                has_expires INTEGER DEFAULT 1,
                is_persistent INTEGER DEFAULT 1,
                priority INTEGER DEFAULT 1,
                samesite INTEGER DEFAULT 1,
                source_scheme INTEGER DEFAULT 2
            )
        """)

        c_time = dt_to_chrome_epoch(now - timedelta(days=2))
        exp_time = dt_to_chrome_epoch(now + timedelta(days=30))
        cur_c.execute("""
            INSERT INTO cookies VALUES (?, '.demo-corp.internal', '', 'SESSION_AUTH', '', X'01000000D08C9DDF0115D1118C7A00C04FC297EB', '/', ?, 1, 1, ?, 1, 1, 1, 1, 2)
        """, (c_time, exp_time, c_time))

        cur_c.execute("""
            INSERT INTO cookies VALUES (?, '.demo-leak.net', '', 'cf_clearance', '', X'01000000D08C9DDF0115D1118C7A00C04FC297EB', '/', ?, 1, 0, ?, 1, 1, 1, 1, 2)
        """, (c_time, exp_time, c_time))

        conn_c.commit()
        conn_c.close()

        # 3. Bookmarks JSON
        bm_file = profile_dir / "Bookmarks"
        bm_time = str(dt_to_chrome_epoch(now - timedelta(days=5)))
        bm_data = {
            "checksum": "d41d8cd98f00b204e9800998ecf8427e",
            "roots": {
                "bookmark_bar": {
                    "children": [
                        {
                            "date_added": bm_time,
                            "id": "1",
                            "name": "Corporate Portal",
                            "type": "url",
                            "url": "https://cloud-portal.demo-corp.internal/login"
                        },
                        {
                            "date_added": bm_time,
                            "id": "2",
                            "name": "Investigation Repository",
                            "type": "url",
                            "url": "https://github.com/synthetic-sec/incident-response-toolkit"
                        }
                    ],
                    "name": "Bookmarks bar",
                    "type": "folder"
                }
            },
            "version": 1
        }
        with open(bm_file, "w", encoding="utf-8") as f:
            json.dump(bm_data, f, indent=2)

        # 4. Preferences JSON
        pref_file = profile_dir / "Preferences"
        pref_data = {
            "account_info": [{"email": "investigator-demo@forensic.local", "full_name": "Demo Analyst"}],
            "download": {"default_directory": "C:\\Users\\Investigator\\Downloads"},
            "profile": {"name": profile_name}
        }
        with open(pref_file, "w", encoding="utf-8") as f:
            json.dump(pref_data, f, indent=2)

    @classmethod
    def create_firefox_profile(cls, profile_dir: Path, browser_name: str, profile_name: str = "default-release"):
        profile_dir.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)

        # 1. places.sqlite
        places_db = profile_dir / "places.sqlite"
        if places_db.exists():
            places_db.unlink()

        conn = sqlite3.connect(places_db)
        cur = conn.cursor()

        cur.execute("""
            CREATE TABLE moz_places (
                id INTEGER PRIMARY KEY,
                url TEXT,
                title TEXT,
                rev_host TEXT,
                visit_count INTEGER DEFAULT 0,
                hidden INTEGER DEFAULT 0,
                typed INTEGER DEFAULT 0,
                frecency INTEGER DEFAULT 0,
                last_visit_date INTEGER DEFAULT 0
            )
        """)

        cur.execute("""
            CREATE TABLE moz_historyvisits (
                id INTEGER PRIMARY KEY,
                from_visit INTEGER,
                place_id INTEGER,
                visit_date INTEGER,
                visit_type INTEGER,
                session INTEGER
            )
        """)

        cur.execute("""
            CREATE TABLE moz_bookmarks (
                id INTEGER PRIMARY KEY,
                type INTEGER,
                fk INTEGER,
                parent INTEGER,
                position INTEGER,
                title TEXT,
                dateAdded INTEGER,
                lastModified INTEGER
            )
        """)

        ff_urls = [
            (1, "https://cloud-portal.demo-corp.internal/login", "Internal Corp Portal Login", 4),
            (2, "https://torproject.demo/download", "Tor Browser Download Page", 1),
            (3, "https://malicious-paste.demo-leak.net/raw/leak_9481.txt", "Raw Document Paste Dump", 2),
            (4, "https://cryptomixer.demo-finance.biz/transact", "Instant Crypto Tumbler Service", 1)
        ]

        for u in ff_urls:
            dt_visit = now - timedelta(hours=(8 - u[0]), minutes=u[0] * 5)
            t_ff = dt_to_firefox_epoch(dt_visit)
            cur.execute("INSERT INTO moz_places VALUES (?, ?, ?, '', ?, 0, 0, 100, ?)", (u[0], u[1], u[2], u[3], t_ff))
            # Regular visit
            cur.execute("INSERT INTO moz_historyvisits VALUES (?, 0, ?, ?, 1, 0)", (u[0], u[0], t_ff))

        # Add bookmark in places
        bm_time = dt_to_firefox_epoch(now - timedelta(days=3))
        cur.execute("INSERT INTO moz_bookmarks VALUES (1, 1, 1, 2, 0, 'Internal Corp Portal', ?, ?)", (bm_time, bm_time))

        conn.commit()
        conn.close()

        # 2. cookies.sqlite
        cookies_db = profile_dir / "cookies.sqlite"
        if cookies_db.exists():
            cookies_db.unlink()

        conn_c = sqlite3.connect(cookies_db)
        cur_c = conn_c.cursor()
        cur_c.execute("""
            CREATE TABLE moz_cookies (
                id INTEGER PRIMARY KEY,
                originAttributes TEXT DEFAULT '',
                name TEXT,
                value TEXT,
                host TEXT,
                path TEXT,
                expiry INTEGER,
                lastAccessed INTEGER,
                creationTime INTEGER,
                isSecure INTEGER,
                isHttpOnly INTEGER,
                inBrowserElement INTEGER DEFAULT 0,
                sameSite INTEGER DEFAULT 0,
                rawSameSite INTEGER DEFAULT 0
            )
        """)

        c_time = dt_to_firefox_epoch(now - timedelta(days=2))
        exp_time = int((now + timedelta(days=14)).timestamp())
        cur_c.execute("""
            INSERT INTO moz_cookies VALUES (1, '', 'auth_session_id', 'REDACTED_PROTECTED', '.demo-corp.internal', '/', ?, ?, ?, 1, 1, 0, 1, 1)
        """, (exp_time, c_time, c_time))

        conn_c.commit()
        conn_c.close()

        # 3. prefs.js
        with open(profile_dir / "prefs.js", "w", encoding="utf-8") as f:
            f.write('user_pref("browser.download.dir", "C:\\\\Users\\\\Investigator\\\\Downloads");\n')
            f.write('user_pref("privacy.clearOnShutdown.history", false);\n')
