"""EODHD MCP Server — Sentiment Analysis."""

import json

from mcp.server.fastmcp import FastMCP

from eodhd_client import (
    get_news_sentiment as _get_news_sentiment,
    get_sentiment_trend as _get_sentiment_trend,
)

server = FastMCP(
    "eodhd",
    instructions="""
# EODHD MCP Server

Provides sentiment analysis data from EODHD API.

Available tools:
- get_news_sentiment: Recent news articles with AI sentiment scores (polarity, positive, negative, neutral) for a ticker.
- get_sentiment_trend: Aggregated daily sentiment trajectory over time (-1 to +1), with trend classification (improving/declining/stable).

Note: Tickers use EODHD format — append exchange suffix (e.g. "AAPL.US", "TSLA.US", "TSM.US").
""",
)


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


if __name__ == "__main__":
    server.run(transport="stdio")
