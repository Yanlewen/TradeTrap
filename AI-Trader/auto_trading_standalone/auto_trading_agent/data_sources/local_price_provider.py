"""Local price provider that reads historical OHLCV data from data/*.json files."""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple

import pandas as pd

logger = logging.getLogger(__name__)


class LocalPriceProvider:
    """Load OHLCV data for stocks/crypto from local JSON files."""

    _HOURLY_KEY = "60min"
    _DAILY_KEY = "1d"

    def __init__(self, data_dir: Optional[Path] = None):
        project_root = Path(__file__).resolve().parents[3]
        self.data_dir = Path(data_dir) if data_dir else project_root / "data"
        self._cache: Dict[str, Dict[str, pd.DataFrame]] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def get_price(self, symbol: str, target: Optional[datetime] = None) -> Optional[float]:
        """Return close price up to the given timestamp (or latest if None)."""
        df = self._get_series(symbol, self._HOURLY_KEY) or self._get_series(symbol, self._DAILY_KEY)
        if df is None or df.empty:
            # Use debug level to reduce noise - summary will be shown at agent level
            logger.debug("No local data available for %s", symbol)
            return None

        if target is None:
            row = df.iloc[-1]
            return float(row["Close"])

        target = self._normalize_dt(target)
        subset = df[df.index <= target]
        if subset.empty:
            # Use debug level to reduce noise
            logger.debug("No local data for %s before %s", symbol, target)
            return None
        return float(subset["Close"].iloc[-1])

    def get_history(
        self,
        symbol: str,
        start: Optional[datetime],
        end: Optional[datetime],
        interval: str = "60min",
    ) -> pd.DataFrame:
        """Return OHLCV dataframe between start and end (inclusive).
        
        If start is before the earliest available data, uses the earliest available data instead.
        This allows backtesting to work even when period requests more history than available.
        """
        interval_key = self._normalize_interval(interval)
        df = self._get_series(symbol, interval_key)
        if df is None:
            raise ValueError(f"No local data for {symbol} ({interval})")

        # If start is before earliest data, use earliest available data
        if start is not None and not df.empty:
            earliest_data = df.index.min()
            normalized_start = self._normalize_dt(start)
            if normalized_start < earliest_data:
                # Use earliest available data instead
                start = earliest_data
                logger.debug(f"Requested start date {normalized_start} is before earliest data {earliest_data} for {symbol}, using {earliest_data} instead")

        if start is not None:
            df = df[df.index >= self._normalize_dt(start)]
        if end is not None:
            df = df[df.index <= self._normalize_dt(end)]
        return df.copy()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_series(self, symbol: str, interval: str) -> Optional[pd.DataFrame]:
        symbol = symbol.upper()
        if symbol not in self._cache:
            self._load_symbol(symbol)
        return self._cache.get(symbol, {}).get(interval)

    def _load_symbol(self, symbol: str) -> None:
        hourly, daily = self._read_symbol_files(symbol)
        data: Dict[str, pd.DataFrame] = {}
        if hourly is not None:
            data[self._HOURLY_KEY] = hourly
        if daily is not None:
            data[self._DAILY_KEY] = daily
        if not data:
            # Use debug level to reduce noise - summary will be shown at agent level
            logger.debug("No usable local data for symbol %s", symbol)
        self._cache[symbol] = data

    def _read_symbol_files(self, symbol: str) -> Tuple[Optional[pd.DataFrame], Optional[pd.DataFrame]]:
        file_path = self.data_dir / f"daily_prices_{symbol.upper()}.json"
        if not file_path.exists():
            # Use debug level to reduce noise - summary will be shown at agent level
            logger.debug("Local data file not found for %s (%s)", symbol, file_path)
            return None, None

        with file_path.open("r", encoding="utf-8") as f:
            raw = json.load(f)

        hourly_df = self._build_dataframe(raw.get("Time Series (60min)"))
        daily_df = self._build_dataframe(raw.get("Time Series (Daily)"))

        if daily_df is None and hourly_df is not None:
            daily_df = self._resample_daily(hourly_df)

        return hourly_df, daily_df

    @staticmethod
    def _build_dataframe(series: Optional[Dict[str, Dict[str, str]]]) -> Optional[pd.DataFrame]:
        if not series:
            return None

        rows = []
        for ts, payload in series.items():
            rows.append(
                {
                    "timestamp": pd.to_datetime(ts),
                    "Open": float(payload.get("1. open") or payload.get("1. buy price")),
                    "High": float(payload.get("2. high")),
                    "Low": float(payload.get("3. low")),
                    "Close": float(payload.get("4. close") or payload.get("4. sell price")),
                    "Volume": float(payload.get("5. volume", 0.0)),
                }
            )

        df = pd.DataFrame(rows).sort_values("timestamp").set_index("timestamp")
        return df

    @staticmethod
    def _resample_daily(hourly_df: pd.DataFrame) -> pd.DataFrame:
        daily = hourly_df.resample("1D").agg(
            {
                "Open": "first",
                "High": "max",
                "Low": "min",
                "Close": "last",
                "Volume": "sum",
            }
        )
        return daily.dropna()

    @staticmethod
    def _normalize_interval(interval: str) -> str:
        interval = interval.lower()
        if interval in {"60min", "1h", "1hour", "hour"}:
            return LocalPriceProvider._HOURLY_KEY
        if interval in {"1d", "daily", "day"}:
            return LocalPriceProvider._DAILY_KEY
        raise ValueError(f"Unsupported interval '{interval}'. Use '60min' or '1d'.")

    @staticmethod
    def _normalize_dt(value: datetime | str) -> datetime:
        if isinstance(value, datetime):
            return value
        if " " in value:
            return datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
        return datetime.strptime(value, "%Y-%m-%d") + timedelta(hours=23, minutes=59, seconds=59)

