"""Sector rotation analysis — relative strength across market sectors."""

from datetime import datetime

import yfinance as yf

from indicators import calc_rsi, calc_macd, calc_moving_averages, determine_trend, fetch_data

DEFAULT_SECTORS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLB": "Materials",
    "XLC": "Communication Services",
    "SMH": "Semiconductors",
    "GDX": "Gold Miners",
    "URA": "Uranium/Nuclear",
    "ITA": "Aerospace & Defense",
}

RETURN_WINDOWS = {
    "1w": 5,
    "1mo": 21,
    "3mo": 63,
}


def _calc_return(closes, days: int) -> float | None:
    """Calculate return over N trading days."""
    if len(closes) <= days:
        return None
    return round((closes.iloc[-1] / closes.iloc[-1 - days] - 1) * 100, 2)


def _rs_momentum(vs_spy: dict) -> str:
    """Determine RS momentum from short vs medium excess return."""
    w1 = vs_spy.get("1w")
    m1 = vs_spy.get("1mo")
    if w1 is None or m1 is None:
        return "stable"
    # Normalize 1w to monthly scale for comparison
    weekly_annualized = w1 * 4
    if weekly_annualized > m1 + 1:
        return "accelerating"
    elif weekly_annualized < m1 - 1:
        return "decelerating"
    return "stable"


def _classify_signal(vs_spy: dict, rs_momentum: str) -> str:
    """Classify sector signal based on relative performance and momentum."""
    excess_1mo = vs_spy.get("1mo", 0)
    if excess_1mo is None:
        excess_1mo = 0

    outperforming = excess_1mo > 0
    if outperforming and rs_momentum == "accelerating":
        return "leading"
    elif not outperforming and rs_momentum == "accelerating":
        return "improving"
    elif outperforming and rs_momentum == "decelerating":
        return "weakening"
    else:
        return "lagging"


def get_sector_rotation(
    period: str = "3mo",
    benchmark: str = "SPY",
    sectors: list[str] | None = None,
) -> dict:
    """Analyze sector rotation with relative strength vs benchmark.

    Args:
        period: yfinance period for fetching data (e.g. "3mo", "6mo").
        benchmark: Benchmark ETF ticker (default "SPY").
        sectors: Optional list of ETF tickers. If None, uses full default list.

    Returns:
        Dict with sector analysis, rankings, leaders, and laggards.
    """
    # Resolve sector list
    if sectors:
        sector_map = {s.upper(): DEFAULT_SECTORS.get(s.upper(), s.upper()) for s in sectors}
    else:
        sector_map = dict(DEFAULT_SECTORS)

    # Fetch extra data so longest lookback (63 trading days) has room
    fetch_period_map = {"1mo": "3mo", "3mo": "6mo", "6mo": "1y", "1y": "2y"}
    fetch_period = fetch_period_map.get(period, "1y")

    # Fetch benchmark data
    bench_df = fetch_data(benchmark, fetch_period)
    bench_closes = bench_df["Close"]
    bench_returns = {}
    for label, days in RETURN_WINDOWS.items():
        bench_returns[label] = _calc_return(bench_closes, days)

    results = []
    for etf, name in sector_map.items():
        try:
            df = fetch_data(etf, fetch_period)
            closes = df["Close"]
            price = round(float(closes.iloc[-1]), 2)

            # Multi-period returns
            returns = {}
            for label, days in RETURN_WINDOWS.items():
                returns[label] = _calc_return(closes, days)

            # Excess returns vs benchmark
            vs_spy = {}
            for label in RETURN_WINDOWS:
                r = returns.get(label)
                br = bench_returns.get(label)
                if r is not None and br is not None:
                    vs_spy[label] = round(r - br, 2)
                else:
                    vs_spy[label] = None

            # RS momentum
            rs_mom = _rs_momentum(vs_spy)

            # RSI + trend (reuse indicators.py)
            rsi_data = calc_rsi(df)
            macd_data = calc_macd(df)
            ma_data = calc_moving_averages(df)
            trend = determine_trend(ma_data, rsi_data, macd_data)

            # Volume ratio (5d vs 20d)
            vol_5d = float(df["Volume"].tail(5).mean())
            vol_20d = float(df["Volume"].tail(20).mean())
            volume_ratio = round(vol_5d / vol_20d, 2) if vol_20d > 0 else 1.0

            signal = _classify_signal(vs_spy, rs_mom)

            results.append({
                "etf": etf,
                "name": name,
                "price": price,
                "returns": returns,
                "vs_spy": vs_spy,
                "rs_momentum": rs_mom,
                "rsi": rsi_data["value"],
                "trend": trend,
                "volume_ratio": volume_ratio,
                "signal": signal,
            })
        except Exception as e:
            results.append({"etf": etf, "name": name, "error": str(e)})

    # Rank by 1mo excess return (descending), errors go last
    def sort_key(x):
        if "error" in x:
            return -9999
        return x["vs_spy"].get("1mo") or -9999

    results.sort(key=sort_key, reverse=True)
    ranking = [r["etf"] for r in results if "error" not in r]

    # Leaders / laggards
    valid = [r for r in results if "error" not in r]
    leaders = [r["etf"] for r in valid if r["signal"] == "leading"][:5]
    laggards = [r["etf"] for r in valid if r["signal"] == "lagging"][:5]

    return {
        "benchmark": benchmark.upper(),
        "period": period,
        "as_of": datetime.now().strftime("%Y-%m-%d"),
        "sectors": results,
        "ranking": ranking,
        "leaders": leaders,
        "laggards": laggards,
    }
