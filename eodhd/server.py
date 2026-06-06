"""EODHD MCP Server — Sentiment, Earnings, Macro & Fundamentals."""

import json

from mcp.server.fastmcp import FastMCP

from eodhd_client import (
    get_news as _get_news,
    get_news_sentiment as _get_news_sentiment,
    get_sentiment_trend as _get_sentiment_trend,
    get_earnings_history as _get_earnings_history,
    get_earnings_trend as _get_earnings_trend,
    get_economic_calendar as _get_economic_calendar,
    get_fundamentals_snapshot as _get_fundamentals_snapshot,
    get_macro_indicator as _get_macro_indicator,
)

server = FastMCP(
    "eodhd",
    instructions="""
# EODHD MCP Server

Provides news, sentiment, earnings, macroeconomic, and fundamentals data from EODHD.

Available tools:
- get_news: Raw news articles with full body content (up to 1500 chars), symbols mentioned, topic tags, and sentiment — for quantitative signal extraction (P3 thesis inference). Use when you need article body/content, not just sentiment scores.
- get_news_sentiment: Recent news articles with AI sentiment scores (polarity, positive, negative, neutral) for a ticker. Sentiment-only — use get_news if you need article body.
- get_sentiment_trend: Aggregated daily sentiment trajectory over time (-1 to +1), with trend classification (improving/declining/stable).
- get_earnings_history: Historical EPS estimate/actual/surprise% + next upcoming earnings, with a base-rate summary (beat ratio, avg surprise) for probability/EV work.
- get_earnings_trend: Analyst forward consensus estimates (next quarter / current FY / next FY) — consensus EPS & revenue (avg/low/high, # analysts) plus EPS-revision momentum. Closest proxy to company guidance; feeds the A3 "analyst-implied" valuation anchor and P3 signal inference.
- get_economic_calendar: High-frequency macro calendar (CPI/NFP/FOMC, etc.) with forecast vs previous vs actual. Use high_impact_only=True for the key prints.
- get_macro_indicator: Lower-frequency macro time series (inflation, GDP, unemployment, real rate) for cycle/regime context.
- get_fundamentals_snapshot: Compact valuation + analyst ratings + key stats (PE/PEG/margins/ROE/52w/beta) in one call.

Note: Tickers use EODHD format — append exchange suffix (e.g. "AAPL.US", "MU.US", "TSM.US").
Macro country codes: economic-events uses 2-letter ("US"); macro-indicator uses 3-letter ("USA").
""",
)


@server.tool()
def get_news(ticker: str, days: int = 7, limit: int = 10) -> str:
    """Get recent raw news articles with full content body for a ticker.

    Unlike get_news_sentiment (sentiment scores only), this returns the full article
    body (up to 1500 chars), symbols co-mentioned, and topic tags — enabling
    quantitative signal extraction (wafer starts, capex, ASP, supply-chain data)
    for thesis derivation (P3 signal-inference workflow).

    Args:
        ticker: EODHD ticker (e.g. "AAPL.US", "MU.US")
        days: Number of days back to search (default 7)
        limit: Max articles to return (default 10)

    Returns:
        JSON array of news articles with title, date, source, link, content (body),
        symbols (co-mentioned tickers), tags (topic tags), and sentiment scores.
    """
    result = _get_news(ticker, days, limit)
    return json.dumps(result, indent=2)


@server.tool()
def get_news_sentiment(ticker: str, days: int = 7, limit: int = 10) -> str:
    """Get recent news with AI sentiment scores for a ticker.

    Args:
        ticker: EODHD ticker (e.g. "AAPL.US", "NVDA.US")
        days: Number of days back to search (default 7)
        limit: Max articles to return (default 10)

    Returns:
        JSON array of news articles with title, date, source,
        and sentiment scores (polarity, pos, neg, neu).
    """
    result = _get_news_sentiment(ticker, days, limit)
    return json.dumps(result, indent=2)


@server.tool()
def get_sentiment_trend(ticker: str, days: int = 30) -> str:
    """Get aggregated daily sentiment trajectory over time.

    Args:
        ticker: EODHD ticker (e.g. "AAPL.US", "NVDA.US")
        days: Number of days of history (default 30)

    Returns:
        JSON with average sentiment (-1 to +1), 7-day recent average,
        trend (improving/declining/stable), and daily breakdown.
    """
    result = _get_sentiment_trend(ticker, days)
    return json.dumps(result, indent=2)


@server.tool()
def get_earnings_history(ticker: str, quarters: int = 8) -> str:
    """Get historical EPS surprises + next earnings + base-rate summary.

    Use this for first-principles base rates (beat ratio, average surprise %)
    required by the probability-honesty-checker workflow.

    Args:
        ticker: EODHD ticker (e.g. "MU.US", "NVDA.US")
        quarters: How many reported quarters to return (default 8)

    Returns:
        JSON with base_rate (beats/misses/inline, beat_pct, avg_surprise_pct),
        next_earnings, reported[], and upcoming[].
    """
    result = _get_earnings_history(ticker, quarters)
    return json.dumps(result, indent=2)


@server.tool()
def get_earnings_trend(ticker: str) -> str:
    """Get analyst forward consensus estimates (closest proxy to guidance).

    Sell-side consensus EPS/revenue for next quarter, current FY and next FY,
    plus EPS-revision momentum (consensus EPS now vs 30 days ago + up/down
    revision counts). Use next_fy.eps_avg as the A3 "analyst-implied" forward
    EPS, and the revision drift as a P3 signal-inference input.

    Args:
        ticker: EODHD ticker (e.g. "MRVL.US", "NOK.US")

    Returns:
        JSON with forward_estimates keyed by next_q / curr_fy / next_fy (+ curr_q):
        consensus eps_avg/low/high, eps_num_analysts, eps_growth, rev_avg,
        rev_growth, eps_revision_30d_pct, revisions_up_30d, revisions_down_30d.
    """
    result = _get_earnings_trend(ticker)
    return json.dumps(result, indent=2)


@server.tool()
def get_economic_calendar(
    from_date: str = "",
    to_date: str = "",
    country: str = "US",
    high_impact_only: bool = False,
    limit: int = 100,
) -> str:
    """Get the economic events calendar with forecasts (CPI/NFP/FOMC, etc.).

    Args:
        from_date: Start date YYYY-MM-DD (default: today)
        to_date: End date YYYY-MM-DD (default: today + 14 days)
        country: 2-letter country code (default "US")
        high_impact_only: If True, keep only CPI/NFP/FOMC/PCE/GDP-class events
        limit: Max events fetched (default 100)

    Returns:
        JSON with date range and events[] (date, type, period, actual,
        forecast, previous).
    """
    result = _get_economic_calendar(
        from_date or None, to_date or None, country, high_impact_only, limit
    )
    return json.dumps(result, indent=2)


@server.tool()
def get_macro_indicator(
    country: str = "USA",
    indicator: str = "inflation_consumer_prices_annual",
    limit: int = 12,
) -> str:
    """Get a macroeconomic indicator time series for regime/cycle context.

    Common indicators: inflation_consumer_prices_annual, real_interest_rate,
    gdp_growth_annual, unemployment_total_percent, gov_debt_percent_gdp.

    Args:
        country: 3-letter ISO country code (default "USA")
        indicator: EODHD macro indicator key
        limit: Number of most-recent data points (default 12)

    Returns:
        JSON with country, indicator name, period, and data[] (date, value).
    """
    result = _get_macro_indicator(country, indicator, limit)
    return json.dumps(result, indent=2)


@server.tool()
def get_fundamentals_snapshot(ticker: str) -> str:
    """Get a compact fundamentals snapshot (valuation + analyst + key stats).

    Args:
        ticker: EODHD ticker (e.g. "MU.US", "AMD.US")

    Returns:
        JSON with name/sector/industry, highlights (PE/PEG/margins/ROE/growth),
        valuation, analyst_ratings, and technicals (52w range, beta, SMAs).
    """
    result = _get_fundamentals_snapshot(ticker)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    server.run(transport="stdio")
