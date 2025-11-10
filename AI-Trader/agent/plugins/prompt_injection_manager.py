"""
Prompt injection manager responsible for loading prompt injection rules
and returning the messages that should be injected for the current context.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, time
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class InjectionContext:
    """Runtime context used to resolve which prompt injections are active."""

    stage: str
    signature: Optional[str] = None
    trading_date: Optional[str] = None
    current_dt: Optional[datetime] = None


class PromptInjectionManager:
    """
    Loads prompt injection definitions from JSON and provides helpers to
    retrieve the messages that should be injected for a given stage.
    """

    def __init__(
        self,
        config_path: str | Path,
        *,
        auto_reload: bool = True,
        default_timezone: str = "UTC",
    ) -> None:
        self.config_path = Path(config_path)
        self.auto_reload = auto_reload
        self.default_timezone = default_timezone

        self._config: Dict[str, Any] = {}
        self._last_mtime: Optional[float] = None

        if not self.config_path.exists():
            raise FileNotFoundError(f"Prompt injection config not found: {self.config_path}")

        self._load_config()

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #
    def get_injections(self, context: InjectionContext) -> List[Dict[str, str]]:
        """
        Return the messages that should be injected for the supplied context.
        """
        self._maybe_reload()

        cfg = self._config
        defaults = cfg.get("defaults", {})
        default_tz = defaults.get("timezone", self.default_timezone)
        base_timezone = ZoneInfo(default_tz)

        current_dt = context.current_dt
        if current_dt is None:
            inferred_dt = None
            if context.trading_date:
                inferred_dt = self._parse_date_like(context.trading_date)
            if inferred_dt is not None:
                if inferred_dt.tzinfo is None:
                    inferred_dt = inferred_dt.replace(tzinfo=base_timezone)
                current_dt = inferred_dt
            else:
                current_dt = datetime.now(tz=base_timezone)
        elif current_dt.tzinfo is None:
            current_dt = current_dt.replace(tzinfo=base_timezone)
        else:
            current_dt = current_dt.astimezone(base_timezone)

        messages: List[Dict[str, str]] = []

        for entry in cfg.get("injections", []):
            if not entry.get("enabled", True):
                continue
            if entry.get("stage") != context.stage:
                continue

            match_constraints: Dict[str, Any] = entry.get("match", {})
            if not self._matches_signature(match_constraints, context.signature):
                continue
            if not self._matches_trading_date(match_constraints, context.trading_date):
                continue
            if not self._matches_datetime(match_constraints, current_dt):
                continue

            for msg in entry.get("messages", []):
                role = msg.get("role", "user")
                content = msg.get("content")
                if not content:
                    continue
                messages.append({"role": role, "content": content})

        return messages

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #
    def _load_config(self) -> None:
        with self.config_path.open("r", encoding="utf-8") as fh:
            self._config = json.load(fh)
        try:
            self._last_mtime = self.config_path.stat().st_mtime
        except FileNotFoundError:
            self._last_mtime = None

    def _maybe_reload(self) -> None:
        if not self.auto_reload:
            return

        try:
            current_mtime = self.config_path.stat().st_mtime
        except FileNotFoundError:
            return

        if self._last_mtime is None or current_mtime > self._last_mtime:
            self._load_config()

    # Match helpers ------------------------------------------------------- #
    def _matches_signature(self, match: Dict[str, Any], signature: Optional[str]) -> bool:
        signatures = match.get("signature") or match.get("signatures")
        if signatures is None:
            return True
        if signature is None:
            return False
        if isinstance(signatures, str):
            return signature == signatures
        return signature in set(signatures)

    def _matches_trading_date(self, match: Dict[str, Any], trading_date: Optional[str]) -> bool:
        dates = match.get("dates")
        if dates:
            if trading_date is None:
                return False
            candidates = self._normalize_trading_date(trading_date)
            if isinstance(dates, str):
                return dates in candidates
            return any(date in candidates for date in dates)

        start_date = match.get("start_date")
        end_date = match.get("end_date")
        if start_date or end_date:
            if trading_date is None:
                return False
            trading_dt = self._parse_date_like(trading_date)
            if trading_dt is None:
                return False
            if start_date:
                start_dt = self._parse_date_like(start_date)
                if start_dt and trading_dt < start_dt:
                    return False
            if end_date:
                end_dt = self._parse_date_like(end_date)
                if end_dt and trading_dt > end_dt:
                    return False

        return True

    def _matches_datetime(self, match: Dict[str, Any], current_dt: datetime) -> bool:
        local_dt = current_dt
        tz_name = match.get("timezone")
        if tz_name:
            try:
                local_dt = current_dt.astimezone(ZoneInfo(tz_name))
            except Exception:
                # Fallback to the original timezone if timezone string is invalid
                local_dt = current_dt

        datetime_range = match.get("datetime_range")
        if datetime_range:
            start_dt = self._parse_iso_datetime(datetime_range.get("start"), local_dt.tzinfo)
            end_dt = self._parse_iso_datetime(datetime_range.get("end"), local_dt.tzinfo)
            if start_dt and local_dt < start_dt:
                return False
            if end_dt and local_dt > end_dt:
                return False

        time_range = match.get("time_range")
        if time_range:
            start_time = self._parse_hhmm(time_range.get("start"), local_dt.tzinfo)
            end_time = self._parse_hhmm(time_range.get("end"), local_dt.tzinfo)
            local_time = local_dt.timetz().replace(second=0, microsecond=0)
            if start_time and local_time < start_time:
                return False
            if end_time and local_time > end_time:
                return False

        times = match.get("times")
        if times:
            parsed_times = {
                self._parse_hhmm(t, local_dt.tzinfo) for t in self._as_iterable(times)
            }
            parsed_times = {t for t in parsed_times if t is not None}
            local_time = local_dt.timetz().replace(second=0, microsecond=0)
            if parsed_times and local_time not in parsed_times:
                return False

        weekdays = match.get("weekdays")
        if weekdays:
            weekday_index = local_dt.weekday()
            normalized = {
                value for value in (self._normalize_weekday(w) for w in self._as_iterable(weekdays))
                if value is not None
            }
            if normalized and weekday_index not in normalized:
                return False

        return True

    # Parsing helpers ----------------------------------------------------- #
    def _parse_iso_datetime(self, value: Optional[str], default_tz: Optional[ZoneInfo]) -> Optional[datetime]:
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
        if dt.tzinfo is None and default_tz is not None:
            dt = dt.replace(tzinfo=default_tz)
        return dt

    def _parse_hhmm(self, value: Optional[str], tz: Optional[ZoneInfo]) -> Optional[time]:
        if not value:
            return None
        try:
            hour, minute = value.split(":")
            return time(hour=int(hour), minute=int(minute), tzinfo=tz)
        except Exception:
            return None

    def _as_iterable(self, value: Any) -> Iterable[Any]:
        if value is None:
            return []
        if isinstance(value, (list, tuple, set)):
            return value
        return [value]

    def _normalize_weekday(self, value: Any) -> Optional[int]:
        if isinstance(value, int):
            return value % 7
        if isinstance(value, str):
            value = value.strip().lower()
            lookup = {
                "mon": 0,
                "monday": 0,
                "tue": 1,
                "tues": 1,
                "tuesday": 1,
                "wed": 2,
                "wednesday": 2,
                "thu": 3,
                "thur": 3,
                "thurs": 3,
                "thursday": 3,
                "fri": 4,
                "friday": 4,
                "sat": 5,
                "saturday": 5,
                "sun": 6,
                "sunday": 6,
            }
            return lookup.get(value)
        return None

    def _normalize_trading_date(self, trading_date: str) -> List[str]:
        """
        Return list of candidate date strings that should match configuration.
        """
        values = [trading_date]
        if " " in trading_date:
            date_only = trading_date.split(" ", 1)[0]
            if date_only not in values:
                values.append(date_only)
        return values

    def _parse_date_like(self, value: str) -> Optional[datetime]:
        """
        Parse a date or datetime string into a datetime object for comparison.
        """
        formats = ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d")
        for fmt in formats:
            try:
                dt = datetime.strptime(value, fmt)
                return dt
            except ValueError:
                continue
        return None


