from datetime import datetime, timezone
from app.forensic.timestamp_engine import ForensicTimestampEngine

def test_chrome_time_conversion():
    # Chrome timestamp for 2026-01-01 00:00:00 UTC
    # 2026-01-01 00:00:00 UTC in Unix is 1767225600 seconds
    # In Chrome microseconds: 1767225600 * 1,000,000 + 11644473600000000 = 13411699200000000
    chrome_ts = 13411699200000000
    dt, raw, warn = ForensicTimestampEngine.parse_chrome_time(chrome_ts)
    assert warn is None
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 1
    assert dt.day == 1
    assert dt.hour == 0

def test_firefox_prtime_conversion():
    # 2026-01-01 00:00:00 UTC in PRTime (microseconds since 1970)
    # 1767225600 * 1,000,000 = 1767225600000000
    ff_ts = 1767225600000000
    dt, raw, warn = ForensicTimestampEngine.parse_firefox_prtime(ff_ts)
    assert warn is None
    assert dt is not None
    assert dt.year == 2026
    assert dt.month == 1
    assert dt.day == 1

def test_unix_epoch_conversion():
    unix_sec = 1767225600 # 2026-01-01
    dt, raw, warn = ForensicTimestampEngine.parse_unix_epoch(unix_sec)
    assert warn is None
    assert dt is not None
    assert dt.year == 2026

    # Unix millis
    unix_millis = 1767225600000
    dt_m, _, _ = ForensicTimestampEngine.parse_unix_epoch(unix_millis)
    assert dt_m == dt

def test_zero_and_empty_timestamps():
    dt, raw, warn = ForensicTimestampEngine.normalize_timestamp(0)
    assert dt is None
    assert warn is None

    dt, raw, warn = ForensicTimestampEngine.normalize_timestamp(None)
    assert dt is None

def test_malformed_timestamp_captured():
    dt, raw, warn = ForensicTimestampEngine.normalize_timestamp("invalid-string-12345XYZ")
    assert dt is None
    assert warn is not None
    assert "Unrecognized" in warn
