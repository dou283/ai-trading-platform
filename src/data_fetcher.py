import logging
import time
import pandas as pd
import numpy as np
import yfinance as yf
from typing import Dict, Optional, Tuple
import ta
from src.config import DEFAULT_SYMBOLS, USD_TRY_SYMBOL

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

DEFAULT_USD_TRY_RATE = 35.0
_SNAPSHOT_CACHE: Dict[str, Tuple[float, Dict]] = {}
CACHE_TTL_SECONDS = 30

def get_usd_try_rate() -> float:
    """Fetches current USD/TRY exchange rate with fallback and caching."""
    cache_key = "USD_TRY"
    now = time.time()
    if cache_key in _SNAPSHOT_CACHE and (now - _SNAPSHOT_CACHE[cache_key][0] < 120):
        return _SNAPSHOT_CACHE[cache_key][1]["rate"]

    try:
        ticker = yf.Ticker(USD_TRY_SYMBOL)
        hist = ticker.history(period="5d")
        if not hist.empty:
            rate = float(hist["Close"].iloc[-1])
            _SNAPSHOT_CACHE[cache_key] = (now, {"rate": rate})
            return rate
    except Exception as e:
        logger.warning(f"USD/TRY kuru alınamadı ({e}), yedek değer {DEFAULT_USD_TRY_RATE} kullanılıyor.")

    return DEFAULT_USD_TRY_RATE

def fetch_ohlcv(symbol: str, period: str = "3mo", interval: str = "1d", max_retries: int = 2) -> Optional[pd.DataFrame]:
    """Fetches historical OHLCV data with retry and clean data sanitation."""
    for attempt in range(max_retries):
        try:
            ticker = yf.Ticker(symbol)
            df = ticker.history(period=period, interval=interval)
            if df is not None and not df.empty and len(df) >= 15:
                df = df[["Open", "High", "Low", "Close", "Volume"]].copy()
                df.dropna(inplace=True)
                if len(df) >= 15:
                    return df
        except Exception as e:
            logger.warning(f"{symbol} veri çekme denemesi {attempt + 1} başarısız: {e}")
            time.sleep(0.5)

    logger.error(f"{symbol} için yeterli veri alınamadı.")
    return None

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates comprehensive technical, regime, and manipulation anomaly indicators."""
    if df is None or len(df) < 15:
        return df

    data = df.copy()
    close = data["Close"]
    open_p = data["Open"]
    high = data["High"]
    low = data["Low"]
    volume = data["Volume"]

    # 1. EMAs
    data["EMA_9"] = ta.trend.EMAIndicator(close=close, window=9).ema_indicator().fillna(close)
    data["EMA_21"] = ta.trend.EMAIndicator(close=close, window=21).ema_indicator().fillna(close)
    data["EMA_50"] = ta.trend.EMAIndicator(close=close, window=50).ema_indicator().fillna(close)
    if len(data) >= 200:
        data["EMA_200"] = ta.trend.EMAIndicator(close=close, window=200).ema_indicator().fillna(close)
    else:
        data["EMA_200"] = ta.trend.EMAIndicator(close=close, window=min(50, len(data))).ema_indicator().fillna(close)

    # 2. Momentum: RSI & MACD
    data["RSI_14"] = ta.momentum.RSIIndicator(close=close, window=14).rsi().fillna(50.0)
    macd = ta.trend.MACD(close=close, window_slow=26, window_fast=12, window_sign=9)
    data["MACD"] = macd.macd().fillna(0.0)
    data["MACD_SIGNAL"] = macd.macd_signal().fillna(0.0)
    data["MACD_DIFF"] = macd.macd_diff().fillna(0.0)

    # 3. Volatility: Bollinger Bands & ATR
    bollinger = ta.volatility.BollingerBands(close=close, window=20, window_dev=2)
    data["BB_HIGH"] = bollinger.bollinger_hband().fillna(close * 1.05)
    data["BB_MID"] = bollinger.bollinger_mavg().fillna(close)
    data["BB_LOW"] = bollinger.bollinger_lband().fillna(close * 0.95)
    data["BB_WID"] = ((data["BB_HIGH"] - data["BB_LOW"]) / data["BB_MID"]).fillna(0.05)

    atr = ta.volatility.AverageTrueRange(high=high, low=low, close=close, window=14)
    data["ATR_14"] = atr.average_true_range().fillna(close * 0.02)

    # 4. Trend Strength: ADX
    try:
        adx = ta.trend.ADXIndicator(high=high, low=low, close=close, window=14)
        data["ADX_14"] = adx.adx().fillna(20.0)
        data["ADX_POS"] = adx.adx_pos().fillna(20.0)
        data["ADX_NEG"] = adx.adx_neg().fillna(20.0)
    except Exception:
        data["ADX_14"] = 20.0
        data["ADX_POS"] = 20.0
        data["ADX_NEG"] = 20.0

    # 5. Volume Analysis
    data["VOL_SMA20"] = ta.trend.SMAIndicator(close=volume, window=min(20, len(data))).sma_indicator().fillna(volume)
    data["VOL_RATIO"] = (data["Volume"] / data["VOL_SMA20"].replace(0, np.nan)).fillna(1.0)

    # 6. Spekülasyon & Manipülasyon Anomali İndikatörleri
    candle_range = (high - low).replace(0, np.nan).fillna(0.01)
    body_top = np.maximum(close, open_p)
    body_bottom = np.minimum(close, open_p)
    
    data["UPPER_WICK_RATIO"] = ((high - body_top) / candle_range).fillna(0.0)
    data["LOWER_WICK_RATIO"] = ((body_bottom - low) / candle_range).fillna(0.0)

    # Fiyat Değişim Yüzdesi
    prev_close = close.shift(1).fillna(close)
    data["PCT_CHANGE"] = ((close - prev_close) / prev_close * 100.0).fillna(0.0)

    return data

def get_symbol_market_snapshot(symbol: str, usd_try_rate: float, use_cache: bool = True) -> Optional[Dict]:
    """Retrieves snapshot for a single symbol with caching."""
    now = time.time()
    if use_cache and symbol in _SNAPSHOT_CACHE:
        cached_time, cached_data = _SNAPSHOT_CACHE[symbol]
        if now - cached_time < CACHE_TTL_SECONDS:
            return cached_data

    df = fetch_ohlcv(symbol)
    if df is None:
        return None

    df_calc = calculate_indicators(df)
    latest = df_calc.iloc[-1]
    prev = df_calc.iloc[-2] if len(df_calc) > 1 else latest

    current_price_native = float(latest["Close"])
    is_try_native = symbol.endswith(".IS")
    price_try = current_price_native if is_try_native else current_price_native * usd_try_rate
    prev_price_native = float(prev["Close"])
    daily_change_pct = ((current_price_native - prev_price_native) / prev_price_native) * 100.0 if prev_price_native > 0 else 0.0

    snapshot = {
        "symbol": symbol,
        "is_try_native": is_try_native,
        "price_native": round(current_price_native, 4),
        "price_try": round(price_try, 2),
        "daily_change_pct": round(daily_change_pct, 2),
        "df": df_calc,
        "latest": latest.to_dict(),
        "prev": prev.to_dict(),
    }

    _SNAPSHOT_CACHE[symbol] = (now, snapshot)
    return snapshot

def fetch_all_markets(symbols_dict: Dict[str, list] = None) -> Dict[str, Dict]:
    if symbols_dict is None:
        symbols_dict = DEFAULT_SYMBOLS

    usd_try_rate = get_usd_try_rate()
    results = {}

    for market_category, symbol_list in symbols_dict.items():
        for symbol in symbol_list:
            snapshot = get_symbol_market_snapshot(symbol, usd_try_rate)
            if snapshot:
                snapshot["category"] = market_category
                results[symbol] = snapshot

    return results
