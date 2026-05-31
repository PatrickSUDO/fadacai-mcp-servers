"""Technical indicator calculations using pandas-ta and yfinance."""

import numpy as np
import pandas as pd
import pandas_ta as ta
import yfinance as yf


def fetch_data(ticker: str, period: str = "6mo") -> pd.DataFrame:
    """Fetch OHLCV data from yfinance."""
    stock = yf.Ticker(ticker)
    df = stock.history(period=period)
    if df.empty:
        raise ValueError(f"No data found for {ticker}")
    return df


def calc_rsi(df: pd.DataFrame, length: int = 14) -> dict:
    rsi_series = ta.rsi(df["Close"], length=length)
    if rsi_series is None or rsi_series.empty:
        return {"value": None, "status": "N/A"}
    val = round(float(rsi_series.iloc[-1]), 2)
    if val > 70:
        status = "overbought"
    elif val < 30:
        status = "oversold"
    else:
        status = "neutral"
    return {"value": val, "status": status}


def calc_macd(df: pd.DataFrame) -> dict:
    macd_df = ta.macd(df["Close"])
    if macd_df is None or macd_df.empty:
        return {"line": None, "signal": None, "histogram": None, "crossover": "N/A"}
    line = round(float(macd_df.iloc[-1, 0]), 4)
    signal = round(float(macd_df.iloc[-1, 1]), 4)
    hist = round(float(macd_df.iloc[-1, 2]), 4)
    prev_hist = float(macd_df.iloc[-2, 2]) if len(macd_df) >= 2 else 0
    if hist > 0 and prev_hist <= 0:
        crossover = "golden_cross"
    elif hist < 0 and prev_hist >= 0:
        crossover = "death_cross"
    else:
        crossover = "none"
    return {"line": line, "signal": signal, "histogram": hist, "crossover": crossover}


def calc_bbands(df: pd.DataFrame, length: int = 20) -> dict:
    bb = ta.bbands(df["Close"], length=length)
    if bb is None or bb.empty:
        return {"upper": None, "middle": None, "lower": None, "pct_b": None, "bandwidth": None}
    price = float(df["Close"].iloc[-1])
    # Column order: BBL (lower), BBM (middle), BBU (upper), BBB (bandwidth), BBP (%B)
    lower = round(float(bb.iloc[-1, 0]), 2)
    middle = round(float(bb.iloc[-1, 1]), 2)
    upper = round(float(bb.iloc[-1, 2]), 2)
    bandwidth = round(float(bb.iloc[-1, 3]), 4) if bb.shape[1] > 3 else round((upper - lower) / middle, 4)
    pct_b = round(float(bb.iloc[-1, 4]), 4) if bb.shape[1] > 4 else round((price - lower) / (upper - lower), 4)
    return {"upper": upper, "middle": middle, "lower": lower, "pct_b": pct_b, "bandwidth": bandwidth}


def calc_atr(df: pd.DataFrame, length: int = 14) -> dict:
    atr_series = ta.atr(df["High"], df["Low"], df["Close"], length=length)
    if atr_series is None or atr_series.empty:
        return {"value": None, "normalized_pct": None, "regime": "N/A"}
    val = round(float(atr_series.iloc[-1]), 2)
    price = float(df["Close"].iloc[-1])
    norm = round(val / price * 100, 2)
    # Determine vol regime based on ATR percentile over the period
    pctile = atr_series.rank(pct=True).iloc[-1]
    if pctile > 0.75:
        regime = "high"
    elif pctile < 0.25:
        regime = "low"
    else:
        regime = "medium"
    return {"value": val, "normalized_pct": norm, "regime": regime}


def calc_volume(df: pd.DataFrame) -> dict:
    vol = int(df["Volume"].iloc[-1])
    avg_20 = int(df["Volume"].tail(20).mean())
    ratio = round(vol / avg_20, 2) if avg_20 > 0 else 0
    return {"current": vol, "avg_20d": avg_20, "ratio": ratio}


def calc_moving_averages(df: pd.DataFrame) -> dict:
    price = float(df["Close"].iloc[-1])
    result = {}
    for period in [20, 50, 200]:
        if len(df) >= period:
            ma_val = round(float(df["Close"].tail(period).mean()), 2)
            pct = round((price - ma_val) / ma_val * 100, 2)
            result[f"sma{period}"] = ma_val
            result[f"vs_sma{period}_pct"] = pct
        else:
            result[f"sma{period}"] = None
            result[f"vs_sma{period}_pct"] = None
    result["price"] = round(price, 2)
    return result


def calc_momentum_score(rsi: dict, macd: dict, ma: dict, volume: dict) -> int:
    """Composite momentum score from -100 to +100."""
    # RSI score: map 0-100 to -100~+100
    rsi_score = 0
    if rsi["value"] is not None:
        rsi_score = (rsi["value"] - 50) * 2  # 50->0, 70->40, 30->-40

    # MACD score: based on histogram sign and magnitude
    macd_score = 0
    if macd["histogram"] is not None:
        hist = macd["histogram"]
        if macd["crossover"] == "golden_cross":
            macd_score = 60
        elif macd["crossover"] == "death_cross":
            macd_score = -60
        else:
            macd_score = max(-100, min(100, hist * 100))  # rough normalization

    # MA score: based on price position relative to 50/200 MA
    ma_score = 0
    vs50 = ma.get("vs_sma50_pct")
    vs200 = ma.get("vs_sma200_pct")
    if vs50 is not None:
        ma_score += max(-50, min(50, vs50 * 5))
    if vs200 is not None:
        ma_score += max(-50, min(50, vs200 * 3))

    # Volume score
    vol_score = 0
    ratio = volume.get("ratio", 1)
    if ratio > 1.5:
        vol_score = 40
    elif ratio > 1.2:
        vol_score = 20
    elif ratio < 0.5:
        vol_score = -30
    elif ratio < 0.8:
        vol_score = -15

    raw = rsi_score * 0.25 + macd_score * 0.25 + ma_score * 0.30 + vol_score * 0.20
    return int(max(-100, min(100, raw)))


def determine_trend(ma: dict, rsi: dict, macd: dict) -> str:
    """Determine overall trend."""
    signals = 0
    vs50 = ma.get("vs_sma50_pct")
    vs200 = ma.get("vs_sma200_pct")
    if vs50 is not None:
        signals += 1 if vs50 > 2 else (-1 if vs50 < -2 else 0)
    if vs200 is not None:
        signals += 1 if vs200 > 5 else (-1 if vs200 < -5 else 0)
    if rsi["value"] is not None:
        signals += 1 if rsi["value"] > 55 else (-1 if rsi["value"] < 45 else 0)
    if macd["histogram"] is not None:
        signals += 1 if macd["histogram"] > 0 else (-1 if macd["histogram"] < 0 else 0)

    if signals >= 3:
        return "strong_uptrend"
    elif signals >= 1:
        return "pullback_correction" if vs50 is not None and vs50 < 0 else "mild_uptrend"
    elif signals <= -3:
        return "strong_downtrend"
    elif signals <= -1:
        return "weak_downtrend"
    else:
        return "consolidation"


def get_technical_indicators(ticker: str, period: str = "6mo") -> dict:
    """Full technical analysis for a single ticker."""
    df = fetch_data(ticker, period)
    rsi = calc_rsi(df)
    macd = calc_macd(df)
    bbands = calc_bbands(df)
    atr = calc_atr(df)
    volume = calc_volume(df)
    ma = calc_moving_averages(df)
    momentum = calc_momentum_score(rsi, macd, ma, volume)
    trend = determine_trend(ma, rsi, macd)

    return {
        "ticker": ticker.upper(),
        "price": ma["price"],
        "rsi": rsi,
        "macd": macd,
        "bollinger_bands": bbands,
        "atr": atr,
        "volume": volume,
        "moving_averages": ma,
        "momentum_score": momentum,
        "volatility_regime": atr["regime"],
        "trend": trend,
    }


def get_support_resistance(ticker: str, period: str = "3mo") -> dict:
    """Calculate support and resistance levels."""
    df = fetch_data(ticker, period)
    price = float(df["Close"].iloc[-1])
    high_52w = float(df["High"].max())
    low_52w = float(df["Low"].min())

    # Pivot points (classic)
    h = float(df["High"].iloc[-1])
    l = float(df["Low"].iloc[-1])
    c = float(df["Close"].iloc[-1])
    pivot = (h + l + c) / 3
    s1 = 2 * pivot - h
    s2 = pivot - (h - l)
    r1 = 2 * pivot - l
    r2 = pivot + (h - l)

    # Find price clusters from historical data for additional S/R
    hist_levels = _find_price_clusters(df)
    supports = sorted([lv for lv in hist_levels if lv < price], reverse=True)[:3]
    resistances = sorted([lv for lv in hist_levels if lv > price])[:3]

    # Add pivot-based levels if not already covered
    for s in [s1, s2]:
        s = round(s, 2)
        if s < price and s not in supports:
            supports.append(s)
    for r in [r1, r2]:
        r = round(r, 2)
        if r > price and r not in resistances:
            resistances.append(r)

    supports = sorted(supports, reverse=True)[:3]
    resistances = sorted(resistances)[:3]

    return {
        "ticker": ticker.upper(),
        "price": round(price, 2),
        "supports": [{"level": round(s, 2), "distance_pct": round((price - s) / price * 100, 2)} for s in supports],
        "resistances": [{"level": round(r, 2), "distance_pct": round((r - price) / price * 100, 2)} for r in resistances],
        "week_52_high": round(high_52w, 2),
        "week_52_low": round(low_52w, 2),
        "from_52w_high_pct": round((price - high_52w) / high_52w * 100, 2),
        "from_52w_low_pct": round((price - low_52w) / low_52w * 100, 2),
    }


def _find_price_clusters(df: pd.DataFrame, n_bins: int = 50) -> list[float]:
    """Find price levels where trading activity clusters (potential S/R)."""
    prices = pd.concat([df["High"], df["Low"]]).values
    hist, bin_edges = np.histogram(prices, bins=n_bins)
    # Find bins with above-average frequency
    threshold = np.mean(hist) * 1.2
    cluster_indices = np.where(hist > threshold)[0]
    levels = []
    for idx in cluster_indices:
        level = (bin_edges[idx] + bin_edges[idx + 1]) / 2
        levels.append(round(float(level), 2))
    return levels


def get_batch_indicators(tickers: list[str], period: str = "3mo") -> list[dict]:
    """Compact technical summary for multiple tickers."""
    results = []
    for ticker in tickers:
        try:
            df = fetch_data(ticker, period)
            rsi = calc_rsi(df)
            macd = calc_macd(df)
            ma = calc_moving_averages(df)
            volume = calc_volume(df)
            atr = calc_atr(df)
            momentum = calc_momentum_score(rsi, macd, ma, volume)
            trend = determine_trend(ma, rsi, macd)
            results.append({
                "ticker": ticker.upper(),
                "price": ma["price"],
                "rsi": rsi["value"],
                "rsi_status": rsi["status"],
                "macd_crossover": macd["crossover"],
                "momentum_score": momentum,
                "trend": trend,
                "vol_regime": atr["regime"],
                "volume_ratio": volume["ratio"],
            })
        except Exception as e:
            results.append({"ticker": ticker.upper(), "error": str(e)})
    return results
