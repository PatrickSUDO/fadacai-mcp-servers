"""Technical Indicators MCP Server."""

import json

from mcp.server.fastmcp import FastMCP

from indicators import (
    get_batch_indicators as _get_batch_indicators,
    get_support_resistance as _get_support_resistance,
    get_technical_indicators as _get_technical_indicators,
)
from sector_rotation import get_sector_rotation as _get_sector_rotation

server = FastMCP(
    "technical-indicators",
    instructions="""
# Technical Indicators MCP Server

Provides technical analysis indicators for stocks.

Available tools:
- get_technical_indicators: Full technical analysis (RSI, MACD, Bollinger Bands, ATR, moving averages, momentum score, trend) for a single ticker.
- get_support_resistance: Support/resistance levels, pivot points, and 52-week range for a single ticker.
- get_batch_indicators: Compact technical summary (RSI, trend, momentum, volatility) for multiple tickers at once.
- get_sector_rotation: Sector rotation analysis with relative strength vs benchmark. Shows multi-period returns, excess returns vs SPY, RS momentum, and signal classification (leading/improving/weakening/lagging) for all major sectors or custom ETF list.
""",
)


@server.tool()
def get_technical_indicators(ticker: str, period: str = "6mo") -> str:
    """Get full technical analysis for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g. "NVDA")
        period: yfinance period format (e.g. "3mo", "6mo", "1y")

    Returns:
        JSON with RSI, MACD, Bollinger Bands, ATR, moving averages,
        momentum score (-100 to +100), volatility regime, and trend.
    """
    result = _get_technical_indicators(ticker, period)
    return json.dumps(result, indent=2)


@server.tool()
def get_support_resistance(ticker: str, period: str = "3mo") -> str:
    """Get support/resistance levels for a ticker.

    Args:
        ticker: Stock ticker symbol (e.g. "NVDA")
        period: yfinance period format (e.g. "3mo", "6mo")

    Returns:
        JSON with support levels, resistance levels, 52-week high/low,
        and distance percentages.
    """
    result = _get_support_resistance(ticker, period)
    return json.dumps(result, indent=2)


@server.tool()
def get_batch_indicators(tickers: list[str], period: str = "3mo") -> str:
    """Get compact technical summary for multiple tickers.

    Args:
        tickers: List of ticker symbols (e.g. ["NVDA", "AMD", "META"])
        period: yfinance period format (e.g. "3mo", "6mo")

    Returns:
        JSON array with RSI, trend, momentum score, volatility regime
        for each ticker.
    """
    result = _get_batch_indicators(tickers, period)
    return json.dumps(result, indent=2)


@server.tool()
def get_sector_rotation(
    period: str = "3mo",
    benchmark: str = "SPY",
    sectors: list[str] | None = None,
) -> str:
    """Analyze sector rotation with relative strength vs benchmark.

    Args:
        period: yfinance period format (e.g. "3mo", "6mo", "1y")
        benchmark: Benchmark ETF ticker (default "SPY")
        sectors: Optional list of ETF tickers (e.g. ["SMH","GDX","URA"]).
                 If not provided, analyzes all 15 default sectors (GICS 11 + themes).

    Returns:
        JSON with per-sector returns, excess returns vs benchmark,
        RS momentum (accelerating/decelerating/stable),
        signal (leading/improving/weakening/lagging),
        plus overall ranking, leaders, and laggards.
    """
    result = _get_sector_rotation(period=period, benchmark=benchmark, sectors=sectors)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    server.run(transport="stdio")
