import os
import sqlite3
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Epoch helpers
CHROME_EPOCH_DIFF_MICROS = 11644473600000000

def to_chrome_time(dt: datetime) -> int:
    unix_sec = dt.replace(tzinfo=timezone.utc).timestamp()
    return int(unix_sec * 1000000) + CHROME_EPOCH_DIFF_MICROS

def to_firefox_time(dt: datetime) -> int:
    unix_sec = dt.replace(tzinfo=timezone.utc).timestamp()
    return int(unix_sec * 1000000)

def build_sample_repository():
    base_dir = Path("sample")
    base_dir.mkdir(parents=True, exist_ok=True)

    chromium_dir = base_dir / "chromium"
    firefox_dir = base_dir / "firefox"
    chromium_dir.mkdir(parents=True, exist_ok=True)
    firefox_dir.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)

    # ==============================================================
    # 1. BUILD CHROMIUM ARTIFACTS (History, Cookies, Bookmarks, Preferences)
    # ==============================================================
    print("[*] Generating Chromium sample artifacts (History, Cookies, Bookmarks)...")
    
    # Target directories: both root sample/ and sample/chromium/
    target_chrome_dirs = [base_dir, chromium_dir]

    for c_dir in target_chrome_dirs:
        # A. History Database
        hist_path = c_dir / "History"
        if hist_path.exists():
            hist_path.unlink()

        conn = sqlite3.connect(hist_path)
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

        # Sample URLs
        chrome_urls = [
            (1, "https://accounts.google.com/signin/v2/identifier", "Google Accounts Login", 4, 2, timedelta(hours=24)),
            (2, "https://github.com/torvalds/linux", "Linux Kernel Source Tree - GitHub", 8, 3, timedelta(hours=20)),
            (3, "https://internal-portal.corp.enterprise.local/dashboard", "Enterprise Executive Intranet", 6, 1, timedelta(hours=14)),
            (4, "https://secure-transfer.cloud-drop.net/files/confidential_financials_2026.pdf", "Secure File Transfer Download Portal", 2, 0, timedelta(hours=5)),
            (5, "https://stackoverflow.com/questions/sqlite-read-only-forensics", "Python SQLite Read-Only Analysis - Stack Overflow", 3, 1, timedelta(hours=3)),
            (6, "https://pastebin.com/raw/secret_payload_sample", "Pastebin Encrypted Paste Dump", 1, 0, timedelta(minutes=45))
        ]

        for u in chrome_urls:
            dt_v = now - u[5]
            ts_c = to_chrome_time(dt_v)
            cur.execute("INSERT INTO urls VALUES (?, ?, ?, ?, ?, ?, 0)", (u[0], u[1], u[2], u[3], u[4], ts_c))
            cur.execute("INSERT INTO visits VALUES (?, ?, ?, 0, 805306368, 0, 30000000)", (u[0], u[0], ts_c))

        # Sample Download
        dl_start = to_chrome_time(now - timedelta(hours=4, minutes=58))
        dl_end = to_chrome_time(now - timedelta(hours=4, minutes=55))
        cur.execute("""
            INSERT INTO downloads VALUES (
                1, 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
                'C:\\Users\\User\\Downloads\\confidential_financials_2026.pdf',
                'C:\\Users\\User\\Downloads\\confidential_financials_2026.pdf',
                ?, ?, 3145728, 3145728, 1, 0, 0,
                'application/pdf', 'application/pdf',
                'https://secure-transfer.cloud-drop.net/files/confidential_financials_2026.pdf',
                'https://internal-portal.corp.enterprise.local/dashboard'
            )
        """, (dl_start, dl_end))
        cur.execute("INSERT INTO downloads_url_chains VALUES (1, 0, 'https://secure-transfer.cloud-drop.net/files/confidential_financials_2026.pdf')")

        conn.commit()
        conn.close()

        # B. Cookies Database
        cookie_path = c_dir / "Cookies"
        if cookie_path.exists():
            cookie_path.unlink()

        conn_c = sqlite3.connect(cookie_path)
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

        c_created = to_chrome_time(now - timedelta(days=5))
        c_expires = to_chrome_time(now + timedelta(days=90))
        cur_c.execute("""
            INSERT INTO cookies VALUES (?, '.enterprise.local', '', 'CORP_AUTH_TOKEN', '', X'01000000D08C9DDF0115D1118C7A00C04FC297EB', '/', ?, 1, 1, ?, 1, 1, 1, 1, 2)
        """, (c_created, c_expires, c_created))
        cur_c.execute("""
            INSERT INTO cookies VALUES (?, '.cloud-drop.net', '', 'guest_session', '', X'01000000D08C9DDF0115D1118C7A00C04FC297EB', '/', ?, 1, 0, ?, 1, 1, 1, 1, 2)
        """, (c_created, c_expires, c_created))
        cur_c.execute("""
            INSERT INTO cookies VALUES (?, '.github.com', '', 'user_session', '', X'01000000D08C9DDF0115D1118C7A00C04FC297EB', '/', ?, 1, 1, ?, 1, 1, 1, 1, 2)
        """, (c_created, c_expires, c_created))

        conn_c.commit()
        conn_c.close()

        # C. Bookmarks JSON
        bm_path = c_dir / "Bookmarks"
        bm_time = str(to_chrome_time(now - timedelta(days=10)))
        bm_tree = {
            "checksum": "a8f7c9e1234567890abcdef123456789",
            "roots": {
                "bookmark_bar": {
                    "children": [
                        {
                            "date_added": bm_time,
                            "id": "1",
                            "name": "Enterprise Intranet",
                            "type": "url",
                            "url": "https://internal-portal.corp.enterprise.local/dashboard"
                        },
                        {
                            "date_added": bm_time,
                            "id": "2",
                            "name": "Cloud Storage Portal",
                            "type": "url",
                            "url": "https://secure-transfer.cloud-drop.net"
                        },
                        {
                            "children": [
                                {
                                    "date_added": bm_time,
                                    "id": "4",
                                    "name": "Linux Repository",
                                    "type": "url",
                                    "url": "https://github.com/torvalds/linux"
                                }
                            ],
                            "date_added": bm_time,
                            "id": "3",
                            "name": "Research Folders",
                            "type": "folder"
                        }
                    ],
                    "name": "Bookmarks bar",
                    "type": "folder"
                }
            },
            "version": 1
        }
        with open(bm_path, "w", encoding="utf-8") as f:
            json.dump(bm_tree, f, indent=2)

        # D. Preferences JSON
        pref_path = c_dir / "Preferences"
        pref_data = {
            "account_info": [{"email": "investigation.sample@corp.local", "full_name": "Sample Subject"}],
            "download": {"default_directory": "C:\\Users\\User\\Downloads"},
            "profile": {"name": "Default"}
        }
        with open(pref_path, "w", encoding="utf-8") as f:
            json.dump(pref_data, f, indent=2)

    # ==============================================================
    # 2. BUILD FIREFOX ARTIFACTS (places.sqlite, cookies.sqlite, prefs.js)
    # ==============================================================
    print("[*] Generating Firefox sample artifacts (places.sqlite, cookies.sqlite)...")
    
    target_ff_dirs = [base_dir, firefox_dir]

    for f_dir in target_ff_dirs:
        # A. places.sqlite
        places_path = f_dir / "places.sqlite"
        if places_path.exists():
            places_path.unlink()

        conn_ff = sqlite3.connect(places_path)
        cur_ff = conn_ff.cursor()
        cur_ff.execute("""
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
        cur_ff.execute("""
            CREATE TABLE moz_historyvisits (
                id INTEGER PRIMARY KEY,
                from_visit INTEGER,
                place_id INTEGER,
                visit_date INTEGER,
                visit_type INTEGER,
                session INTEGER
            )
        """)
        cur_ff.execute("""
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

        firefox_urls = [
            (1, "https://internal-portal.corp.enterprise.local/dashboard", "Enterprise Executive Intranet", 5, timedelta(hours=18)),
            (2, "https://proton.me/mail", "Proton Mail - Encrypted Webmail", 7, timedelta(hours=12)),
            (3, "https://secure-transfer.cloud-drop.net/files/confidential_financials_2026.pdf", "Secure File Transfer Download Portal", 2, timedelta(hours=4)),
            (4, "https://duckduckgo.com/?q=how+to+wipe+usb+drive+permanently", "DuckDuckGo Search: wipe usb drive permanently", 2, timedelta(hours=2)),
            (5, "https://malicious-paste.demo-leak.net/raw/leak_9481.txt", "Raw Document Paste Dump", 1, timedelta(minutes=30))
        ]

        for u in firefox_urls:
            dt_v = now - u[4]
            ts_ff = to_firefox_time(dt_v)
            cur_ff.execute("INSERT INTO moz_places VALUES (?, ?, ?, '', ?, 0, 0, 150, ?)", (u[0], u[1], u[2], u[3], ts_ff))
            cur_ff.execute("INSERT INTO moz_historyvisits VALUES (?, 0, ?, ?, 1, 0)", (u[0], u[0], ts_ff))

        # Add Firefox download (visit_type = 7)
        dl_ff_time = to_firefox_time(now - timedelta(hours=3, minutes=58))
        cur_ff.execute("INSERT INTO moz_places VALUES (6, 'https://secure-transfer.cloud-drop.net/files/confidential_financials_2026.pdf', 'Download: confidential_financials_2026.pdf', '', 1, 0, 0, 200, ?)", (dl_ff_time,))
        cur_ff.execute("INSERT INTO moz_historyvisits VALUES (6, 0, 6, ?, 7, 0)", (dl_ff_time,))

        # Add bookmark
        bm_ff_time = to_firefox_time(now - timedelta(days=7))
        cur_ff.execute("INSERT INTO moz_bookmarks VALUES (1, 1, 1, 2, 0, 'Enterprise Intranet Portal', ?, ?)", (bm_ff_time, bm_ff_time))
        cur_ff.execute("INSERT INTO moz_bookmarks VALUES (2, 1, 2, 2, 1, 'Proton Secure Webmail', ?, ?)", (bm_ff_time, bm_ff_time))

        conn_ff.commit()
        conn_ff.close()

        # B. cookies.sqlite
        cookies_ff_path = f_dir / "cookies.sqlite"
        if cookies_ff_path.exists():
            cookies_ff_path.unlink()

        conn_cff = sqlite3.connect(cookies_ff_path)
        cur_cff = conn_cff.cursor()
        cur_cff.execute("""
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

        ff_c_created = to_firefox_time(now - timedelta(days=4))
        ff_c_access = to_firefox_time(now - timedelta(hours=2))
        ff_c_exp = int((now + timedelta(days=60)).timestamp())

        cur_cff.execute("""
            INSERT INTO moz_cookies VALUES (1, '', 'SSID_PROTECTED', 'ENCRYPTED_AUTH_BLOB', '.enterprise.local', '/', ?, ?, ?, 1, 1, 0, 1, 1)
        """, (ff_c_exp, ff_c_access, ff_c_created))
        cur_cff.execute("""
            INSERT INTO moz_cookies VALUES (2, '', 'token', 'ENCRYPTED_DROP_TOKEN', '.cloud-drop.net', '/', ?, ?, ?, 1, 0, 0, 1, 1)
        """, (ff_c_exp, ff_c_access, ff_c_created))

        conn_cff.commit()
        conn_cff.close()

        # C. prefs.js
        with open(f_dir / "prefs.js", "w", encoding="utf-8") as f:
            f.write('user_pref("browser.download.dir", "C:\\\\Users\\\\User\\\\Downloads");\n')
            f.write('user_pref("browser.download.folderList", 2);\n')
            f.write('user_pref("privacy.clearOnShutdown.history", false);\n')

    print("\n[+] SUCCESS! Sample forensic evidence generated in:")
    print(f"    - Root Folder:     {base_dir.resolve()}")
    print(f"    - Chromium Subdir: {chromium_dir.resolve()}")
    print(f"    - Firefox Subdir:  {firefox_dir.resolve()}")

if __name__ == "__main__":
    build_sample_repository()
