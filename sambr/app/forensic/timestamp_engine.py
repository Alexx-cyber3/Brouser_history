from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional, Any

# Chrome / WebKit epoch difference: 1601-01-01 to 1970-01-01 in microseconds
# 11644473600 seconds * 1,000,000 microseconds/sec
CHROME_EPOCH_DIFF_MICROS = 11644473600000000

class ForensicTimestampEngine:
    """
    Forensic timestamp normalization engine.
    Accurately handles:
      - Chrome / Chromium / Edge WebKit epoch (microseconds since 1601-01-01 00:00:00 UTC)
      - Mozilla Firefox PRTime (microseconds since 1970-01-01 00:00:00 UTC)
      - Unix epoch (seconds, milliseconds, microseconds)
      - Windows FILETIME (100-nanosecond intervals since 1601-01-01)
      - ISO-8601 strings
    Never silently discards malformed timestamps; returns warnings.
    """

    @staticmethod
    def parse_chrome_time(raw_val: Any) -> Tuple[Optional[datetime], str, Optional[str]]:
        """Convert Chromium / WebKit microsecond timestamp (since 1601-01-01) to UTC datetime."""
        if raw_val is None or raw_val == 0 or raw_val == "":
            return None, str(raw_val), None
        try:
            micros = int(raw_val)
            if micros <= 0:
                return None, str(raw_val), None
            # If value is exceptionally large or small, validate sanity
            # Unix timestamp equivalent: (micros - CHROME_EPOCH_DIFF_MICROS) / 1,000,000
            unix_micros = micros - CHROME_EPOCH_DIFF_MICROS
            if unix_micros < -62135596800000000: # before year 0001
                return None, str(raw_val), f"Chrome timestamp {micros} out of lower bound"
            unix_sec = unix_micros / 1000000.0
            dt = datetime.fromtimestamp(unix_sec, tz=timezone.utc)
            return dt, str(raw_val), None
        except Exception as e:
            return None, str(raw_val), f"Failed to parse Chrome timestamp: {str(e)}"

    @staticmethod
    def parse_firefox_prtime(raw_val: Any) -> Tuple[Optional[datetime], str, Optional[str]]:
        """Convert Firefox PRTime (microseconds since 1970-01-01) to UTC datetime."""
        if raw_val is None or raw_val == 0 or raw_val == "":
            return None, str(raw_val), None
        try:
            val = int(raw_val)
            if val <= 0:
                return None, str(raw_val), None
            unix_sec = val / 1000000.0
            dt = datetime.fromtimestamp(unix_sec, tz=timezone.utc)
            return dt, str(raw_val), None
        except Exception as e:
            return None, str(raw_val), f"Failed to parse Firefox PRTime: {str(e)}"

    @staticmethod
    def parse_unix_epoch(raw_val: Any) -> Tuple[Optional[datetime], str, Optional[str]]:
        """Convert Unix seconds, milliseconds, or microseconds to UTC datetime."""
        if raw_val is None or raw_val == 0 or raw_val == "":
            return None, str(raw_val), None
        try:
            val = float(raw_val)
            if val <= 0:
                return None, str(raw_val), None
            
            # Auto-detect scale based on magnitude
            if val > 1e15: # Microseconds
                unix_sec = val / 1000000.0
            elif val > 1e11: # Milliseconds
                unix_sec = val / 1000.0
            else: # Seconds
                unix_sec = val

            dt = datetime.fromtimestamp(unix_sec, tz=timezone.utc)
            return dt, str(raw_val), None
        except Exception as e:
            return None, str(raw_val), f"Failed to parse Unix timestamp: {str(e)}"

    @classmethod
    def normalize_timestamp(cls, raw_val: Any, browser_hint: str = "UNKNOWN") -> Tuple[Optional[datetime], str, Optional[str]]:
        """
        Smart normalizer utilizing browser hints and numeric magnitude.
        Always preserves raw representation and returns warnings if parsing fails.
        """
        if raw_val is None or raw_val == "" or raw_val == 0:
            return None, str(raw_val) if raw_val is not None else "", None

        browser_upper = (browser_hint or "").upper()
        raw_str = str(raw_val)

        # Check if already ISO string
        if isinstance(raw_val, str) and ("T" in raw_val or "-" in raw_val):
            try:
                # Handle standard ISO-8601 formats
                clean_iso = raw_val.replace("Z", "+00:00")
                dt = datetime.fromisoformat(clean_iso)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                else:
                    dt = dt.astimezone(timezone.utc)
                return dt, raw_str, None
            except Exception:
                pass

        try:
            num = int(float(raw_val))
        except (ValueError, TypeError):
            return None, raw_str, f"Unrecognized non-numeric timestamp format: {raw_str}"

        if browser_upper in ("CHROME", "EDGE", "CHROMIUM"):
            # Typical Chrome timestamp is > 11644473600000000 (around 1.3e17)
            if num > 1e16:
                return cls.parse_chrome_time(num)
            else:
                # Fallback to unix if chrome epoch isn't matched
                return cls.parse_unix_epoch(num)

        elif browser_upper in ("FIREFOX", "MOZILLA"):
            # Firefox PRTime is typically microseconds since 1970 (e.g. 1.7e15)
            if num > 1e14:
                return cls.parse_firefox_prtime(num)
            else:
                return cls.parse_unix_epoch(num)

        # Unknown / Auto heuristic
        if num > 1e16:
            return cls.parse_chrome_time(num)
        elif num > 1e14:
            return cls.parse_firefox_prtime(num)
        else:
            return cls.parse_unix_epoch(num)

    @staticmethod
    def format_utc_iso(dt: Optional[datetime]) -> str:
        if not dt:
            return ""
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    @staticmethod
    def format_display(dt: Optional[datetime], tz_offset_hours: float = 0.0) -> str:
        if not dt:
            return "N/A"
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        target_tz = timezone(timedelta(hours=tz_offset_hours))
        local_dt = dt.astimezone(target_tz)
        tz_sign = "+" if tz_offset_hours >= 0 else "-"
        tz_label = f"UTC{tz_sign}{abs(int(tz_offset_hours)):02d}:00" if tz_offset_hours != 0 else "UTC"
        return f"{local_dt.strftime('%Y-%m-%d %H:%M:%S')} ({tz_label})"
