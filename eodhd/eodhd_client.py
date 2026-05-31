"""EODHD API client for sentiment analysis data."""

import os
from datetime import datetime, timedelta

import requests

BASE_URL = "https://eodhd.com/api"
API_TOKEN = os.environ.get("EODHD_API_TOKEN", "")


def _get(endpoint: str, params: dict | None = None) -> dict | list:
    """Make a GET request to the EODHD API."""
    params = params or {}
    params["api_token"] = API_TOKEN
    params["fmt"] = "json"
    resp = requests.get(f"{BASE_URL}/{endpoint}", params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_news_sentiment(ticker: str, days: int = 7, limit: int = 10) -> list[dict]:
    """Get recent news articles with sentiment scores for a ticker.

    Args:
        ticker: EODHD ticker format (e.g. "AAPL.US")
        days: Number of days back to search
        limit: Max number of articles to return

    Returns:
        List of news articles with title, date, sentiment scores.
    """
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    data = _get("news", params={
        "s": ticker,
        "from": date_from,
        "limit": limit,
    })

    results = []
    for article in data:
        sentiment = article.get("sentiment", {})
        results.append({
            "title": article.get("title", ""),
            "date": article.get("date", ""),
            "link": article.get("link", ""),
            "source": article.get("source", ""),
            "sentiment": {
                "polarity": sentiment.get("polarity", 0),
                "neg": sentiment.get("neg", 0),
                "neu": sentiment.get("neu", 0),
                "pos": sentiment.get("pos", 0),
            },
        })
    return results


def get_sentiment_trend(ticker: str, days: int = 30) -> dict:
    """Get aggregated daily sentiment scores over time.

    Args:
        ticker: EODHD ticker format (e.g. "AAPL.US")
        days: Number of days of history

    Returns:
        Dict with ticker, date range, and daily sentiment data.
    """
    date_from = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
    date_to = datetime.now().strftime("%Y-%m-%d")
    data = _get("sentiments", params={
        "s": ticker,
        "from": date_from,
        "to": date_to,
    })

    # data is a dict keyed by ticker, value is a list of daily entries
    daily = []
    if isinstance(data, dict):
        # Get the first (and usually only) ticker's data
        entries = list(data.values())[0] if data else []
        for entry in entries:
            daily.append({
                "date": entry.get("date", ""),
                "count": entry.get("count", 0),
                "normalized": entry.get("normalized", 0),
            })
        daily.sort(key=lambda x: x["date"])

    # Calculate summary stats
    if daily:
        scores = [d["normalized"] for d in daily if d["normalized"] != 0]
        avg_score = sum(scores) / len(scores) if scores else 0
        recent_7d = [d for d in daily[-7:] if d["normalized"] != 0]
        recent_avg = sum(d["normalized"] for d in recent_7d) / len(recent_7d) if recent_7d else 0
        older = [d for d in daily[:-7] if d["normalized"] != 0]
        older_avg = sum(d["normalized"] for d in older) / len(older) if older else 0

        if recent_avg > older_avg + 0.05:
            trend = "improving"
        elif recent_avg < older_avg - 0.05:
            trend = "declining"
        else:
            trend = "stable"
    else:
        avg_score = 0
        recent_avg = 0
        trend = "no_data"

    return {
        "ticker": ticker,
        "period_days": days,
        "date_from": date_from,
        "date_to": date_to,
        "average_sentiment": round(avg_score, 4),
        "recent_7d_sentiment": round(recent_avg, 4),
        "trend": trend,
        "daily": daily,
    }
