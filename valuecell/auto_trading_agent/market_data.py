"""Market data and technical indicator retrieval - from a trader's perspective"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

import pandas as pd

from .data_sources.local_price_provider import LocalPriceProvider
from .models import TechnicalIndicators

logger = logging.getLogger(__name__)


class MarketDataProvider:
    """
    Fetches and caches market data.

    A trader typically thinks about:
    1. "What's the current price?"
    2. "What are the technical indicators telling me?"
    3. "Is there enough volume for good execution?"
    """

    def __init__(self, cache_ttl_seconds: int = 60, min_bars_daily: int = 20, min_bars_hourly: int = 50):
        """
        Initialize market data provider with optional caching.

        Args:
            cache_ttl_seconds: Time to live for cached data
            min_bars_daily: Minimum number of bars required for daily data analysis
            min_bars_hourly: Minimum number of bars required for hourly data analysis
        """
        self.cache_ttl_seconds = cache_ttl_seconds
        self._cache: Dict[str, tuple] = {}  # {symbol: (data, timestamp)}
        self.current_date: Optional[str] = None  # For historical backtesting
        self._local_provider = LocalPriceProvider()
        self.min_bars_daily = min_bars_daily
        self.min_bars_hourly = min_bars_hourly

    def set_current_date(self, date: str):
        """
        Set current date for historical backtesting.

        Args:
            date: Date string (YYYY-MM-DD or YYYY-MM-DD HH:MM:SS)
        """
        self.current_date = date
        logger.debug(f"MarketDataProvider set current date: {date}")

    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price for a symbol.
        Supports historical backtesting when current_date is set.

        Args:
            symbol: Trading symbol (e.g., BTC-USD)

        Returns:
            Current price or None if fetch fails
        """
        try:
            target_dt: Optional[datetime] = None
            if self.current_date:
                if " " in self.current_date:
                    target_dt = datetime.strptime(self.current_date, "%Y-%m-%d %H:%M:%S")
                else:
                    target_dt = datetime.strptime(self.current_date, "%Y-%m-%d")
            price = self._local_provider.get_price(symbol, target_dt)
            if price is None:
                # Use debug level to reduce noise - summary will be shown at agent level
                logger.debug("No local price available for %s (current_date=%s)", symbol, self.current_date)
            return price
        except Exception as e:
            # Only log unexpected errors, not missing data
            logger.debug(f"Failed to get current price for {symbol}: {e}")
            return None

    def calculate_indicators(
        self, symbol: str, period: str = "5d", interval: str = "60min"
    ) -> Optional[TechnicalIndicators]:
        """
        Calculate all technical indicators for a symbol.
        Supports historical backtesting when current_date is set.

        Args:
            symbol: Trading symbol
            period: Data period (default: 5 days for intraday trading)
            interval: Data interval (default: 1 minute)

        Returns:
            TechnicalIndicators object or None if calculation fails
        """
        try:
            end_dt: Optional[datetime] = None
            if self.current_date:
                if " " in self.current_date:
                    end_dt = datetime.strptime(self.current_date, "%Y-%m-%d %H:%M:%S")
                else:
                    end_dt = datetime.strptime(self.current_date, "%Y-%m-%d")

            start_dt = self._resolve_start_date(end_dt, period)
            df = self._local_provider.get_history(symbol, start_dt, end_dt, interval=interval or "60min")

            # Use configured minimum data requirement based on interval
            min_bars = self.min_bars_daily if interval == "1d" else self.min_bars_hourly
            if df.empty or len(df) < min_bars:
                # Log detailed info for first symbol to help debug
                if symbol == "NVDA":  # Log details for first symbol only
                    logger.warning(
                        f"⚠️  Data issue for {symbol}: got {len(df)} bars, need {min_bars} for {interval}. "
                        f"Data range: {df.index.min() if not df.empty else 'N/A'} to {df.index.max() if not df.empty else 'N/A'}. "
                        f"Requested: {start_dt} to {end_dt}"
                    )
                # Use debug level to reduce noise - summary will be shown at agent level
                logger.debug(f"Insufficient local data for {symbol}: {len(df)} bars (need at least {min_bars} for {interval})")
                return None

            # Calculate all indicators
            self._calculate_moving_averages(df)
            self._calculate_macd(df)
            self._calculate_rsi(df)
            self._calculate_bollinger_bands(df)

            # Get latest values
            return self._extract_latest_indicators(df, symbol)

        except Exception as e:
            # Use debug level to reduce noise - most failures are due to missing data
            # which is already handled and summarized at agent level
            logger.debug(f"Failed to calculate indicators for {symbol}: {e}")
            return None

    @staticmethod
    def _resolve_start_date(end_dt: Optional[datetime], period: str) -> Optional[datetime]:
        """Convert yfinance-like period string to start datetime."""
        if end_dt is None:
            end_dt = datetime.utcnow()

        if period.endswith("d"):
            days = int(period[:-1])
            # For hourly data, reduce buffer days (1 day instead of 2)
            # Check if we're dealing with hourly data by checking if end_dt has time component
            has_time = end_dt.hour != 0 or end_dt.minute != 0 or end_dt.second != 0
            buffer_days = 1 if has_time else 2
            return end_dt - timedelta(days=days + buffer_days)
        if period.endswith("h"):
            hours = int(period[:-1])
            return end_dt - timedelta(hours=hours + 12)
        # default fallback
        return end_dt - timedelta(days=7)

    @staticmethod
    def _calculate_moving_averages(df: pd.DataFrame):
        """Calculate exponential moving averages"""
        df["ema_12"] = df["Close"].ewm(span=12, adjust=False).mean()
        df["ema_26"] = df["Close"].ewm(span=26, adjust=False).mean()
        df["ema_50"] = df["Close"].ewm(span=50, adjust=False).mean()

    @staticmethod
    def _calculate_macd(df: pd.DataFrame):
        """Calculate MACD and signal line"""
        df["ema_12"] = df["Close"].ewm(span=12, adjust=False).mean()
        df["ema_26"] = df["Close"].ewm(span=26, adjust=False).mean()
        df["macd"] = df["ema_12"] - df["ema_26"]
        df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
        df["macd_histogram"] = df["macd"] - df["macd_signal"]

    @staticmethod
    def _calculate_rsi(df: pd.DataFrame, period: int = 14):
        """Calculate Relative Strength Index"""
        delta = df["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        # Avoid division by zero: if loss is 0, RSI = 100 (maximum strength)
        rs = gain / loss.replace(0, float("inf"))
        df["rsi"] = 100 - (100 / (1 + rs))

    @staticmethod
    def _calculate_bollinger_bands(
        df: pd.DataFrame, period: int = 20, std_dev: float = 2
    ):
        """Calculate Bollinger Bands"""
        df["bb_middle"] = df["Close"].rolling(window=period).mean()
        bb_std = df["Close"].rolling(window=period).std()
        df["bb_upper"] = df["bb_middle"] + (bb_std * std_dev)
        df["bb_lower"] = df["bb_middle"] - (bb_std * std_dev)

    @staticmethod
    def _extract_latest_indicators(
        df: pd.DataFrame, symbol: str
    ) -> TechnicalIndicators:
        """Extract latest indicator values from dataframe"""
        latest = df.iloc[-1]

        def safe_float(value):
            """Safely convert to float, handling NaN"""
            return float(value) if pd.notna(value) else None

        return TechnicalIndicators(
            symbol=symbol,
            timestamp=datetime.now(timezone.utc),
            close_price=float(latest["Close"]),
            volume=float(latest["Volume"]),
            macd=safe_float(latest.get("macd")),
            macd_signal=safe_float(latest.get("macd_signal")),
            macd_histogram=safe_float(latest.get("macd_histogram")),
            rsi=safe_float(latest.get("rsi")),
            ema_12=safe_float(latest.get("ema_12")),
            ema_26=safe_float(latest.get("ema_26")),
            ema_50=safe_float(latest.get("ema_50")),
            bb_upper=safe_float(latest.get("bb_upper")),
            bb_middle=safe_float(latest.get("bb_middle")),
            bb_lower=safe_float(latest.get("bb_lower")),
        )



class SignalGenerator:
    """
    Generates trading signals from technical indicators.

    A trader's signal logic:
    1. When to buy? (Entry signals)
    2. When to sell? (Exit signals)
    3. How confident am I?
    """

    from .models import TradeAction, TradeType

    @staticmethod
    def generate_signal(
        indicators: TechnicalIndicators,
    ) -> tuple["SignalGenerator.TradeAction", "SignalGenerator.TradeType"]:
        """
        Generate trading signal based on technical indicators.

        Uses a combination of:
        - MACD for trend direction
        - RSI for momentum/exhaustion
        - Bollinger Bands for volatility and support/resistance

        Args:
            indicators: Technical indicators for analysis

        Returns:
            Tuple of (TradeAction, TradeType)
        """
        from .models import TradeAction, TradeType

        try:
            # Check if we have all required indicators
            if (
                indicators.macd is None
                or indicators.macd_signal is None
                or indicators.rsi is None
            ):
                return (TradeAction.HOLD, TradeType.LONG)

            # Analyze trend direction
            macd_bullish = indicators.macd > indicators.macd_signal
            macd_bearish = indicators.macd < indicators.macd_signal

            # Analyze momentum
            rsi_oversold = indicators.rsi < 30
            rsi_overbought = indicators.rsi > 70

            # Entry signals: Look for mean-reversion opportunities with trend confirmation
            # Long signal: MACD bullish + RSI showing oversold
            if macd_bullish and rsi_oversold:
                return (TradeAction.BUY, TradeType.LONG)

            # Short signal: MACD bearish + RSI showing overbought
            if macd_bearish and rsi_overbought:
                return (TradeAction.BUY, TradeType.SHORT)

            # Exit signals: Close positions when momentum reverses
            # Exit long: MACD turns bearish or RSI gets overbought
            if macd_bearish or rsi_overbought:
                return (TradeAction.SELL, TradeType.LONG)

            # Exit short: MACD turns bullish or RSI gets oversold
            if macd_bullish or rsi_oversold:
                return (TradeAction.SELL, TradeType.SHORT)

            return (TradeAction.HOLD, TradeType.LONG)

        except Exception as e:
            logger.error(f"Failed to generate signal: {e}")
            return (TradeAction.HOLD, TradeType.LONG)

    @staticmethod
    def get_signal_strength(indicators: TechnicalIndicators) -> Dict[str, float]:
        """
        Get quantitative strength of signals.

        Returns:
            Dictionary with various signal strength indicators (0-100)
        """
        strength = {}

        # MACD strength (0-100)
        if indicators.macd is not None and indicators.macd_signal is not None:
            macd_diff = indicators.macd - indicators.macd_signal
            # Normalize to 0-100 scale (assuming typical range)
            strength["macd"] = min(100, max(0, 50 + (macd_diff * 100)))
        else:
            strength["macd"] = 50  # Neutral

        # RSI strength (already 0-100)
        if indicators.rsi is not None:
            strength["rsi"] = indicators.rsi
        else:
            strength["rsi"] = 50  # Neutral

        # Distance from Bollinger Bands (0-100)
        if (
            indicators.bb_lower is not None
            and indicators.bb_upper is not None
            and indicators.bb_middle is not None
        ):
            band_range = indicators.bb_upper - indicators.bb_lower
            if band_range > 0:
                # Distance from middle: 0 = at lower band, 100 = at upper band
                distance = (indicators.close_price - indicators.bb_lower) / band_range
                strength["bollinger"] = min(100, max(0, distance * 100))
            else:
                strength["bollinger"] = 50
        else:
            strength["bollinger"] = 50  # Neutral

        return strength
