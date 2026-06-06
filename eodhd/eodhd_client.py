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


def _f(v):
    """Coerce an EODHD numeric value (often a string like "6.1726", or None)
    to float. Returns None for blank/None/non-numeric so callers can guard."""
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


# High-impact US macro events worth surfacing by default in a briefing.
HIGH_IMPACT_EVENTS = [
    "CPI", "Inflation Rate", "Core Inflation", "Nonfarm", "Payroll",
    "Fed Interest Rate", "Interest Rate Decision", "FOMC", "Fed Press Conference",
    "PCE", "Unemployment Rate", "GDP", "PPI", "Retail Sales", "ISM",
    "Initial Jobless", "Powell",
]


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


def get_news(ticker: str, days: int = 7, limit: int = 10) -> list[dict]:
    """Get recent raw news articles (full content body + symbols + tags) for a ticker.

    Unlike get_news_sentiment which only returns sentiment scores, this function
    preserves the full article body (truncated to 1500 chars), symbols co-mentioned,
    and topic tags — enabling quantitative signal extraction (wafer starts, capex,
    ASP trends, etc.) for thesis derivation (P3 signal-inference).

    Args:
        ticker: EODHD ticker format (e.g. "AAPL.US")
        days: Number of days back to search (default 7)
        limit: Max number of articles to return (default 10)

    Returns:
        List of news articles with title, date, link, source, content (body, up to
        1500 chars), symbols (tickers mentioned), tags (topic tags), and sentiment scores.
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
        content_raw = article.get("content") or ""
        results.append({
            "title": article.get("title", ""),
            "date": article.get("date", ""),
            "link": article.get("link", ""),
            "source": article.get("source", ""),
            "content": content_raw[:1500],      # truncate for MCP context size
            "symbols": article.get("symbols") or [],
            "tags": article.get("tags") or [],
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


def get_earnings_history(ticker: str, quarters: int = 8) -> dict:
    """Get historical EPS estimate/actual/surprise + next upcoming earnings.

    Feeds first-principles base rates (beat ratio, average surprise %) for the
    probability-honesty-checker workflow.

    Args:
        ticker: EODHD ticker format (e.g. "NVDA.US")
        quarters: How many reported quarters to return (default 8)

    Returns:
        Dict with reported[] (most recent first), upcoming[], and a
        base_rate summary (beats/misses/inline, beat_pct, avg_surprise_pct).
    """
    date_from = (datetime.now() - timedelta(days=quarters * 100 + 120)).strftime("%Y-%m-%d")
    date_to = (datetime.now() + timedelta(days=120)).strftime("%Y-%m-%d")
    data = _get("calendar/earnings", params={
        "symbols": ticker,
        "from": date_from,
        "to": date_to,
    })
    rows = data.get("earnings", []) if isinstance(data, dict) else []

    reported, upcoming = [], []
    for r in rows:
        entry = {
            "report_date": r.get("report_date", ""),
            "fiscal_date": r.get("date", ""),
            "timing": r.get("before_after_market", ""),
            "actual": r.get("actual"),
            "estimate": r.get("estimate"),
            "difference": r.get("difference"),
            "surprise_pct": r.get("percent"),
        }
        if entry["actual"] is not None:
            reported.append(entry)
        else:
            upcoming.append(entry)

    reported.sort(key=lambda x: x["report_date"], reverse=True)
    upcoming.sort(key=lambda x: x["report_date"])
    reported = reported[:quarters]

    # Base-rate summary over the reported quarters that have both actual + estimate.
    beats = misses = inline = 0
    surprises = []
    for e in reported:
        if e["actual"] is None or e["estimate"] is None:
            continue
        if e["surprise_pct"] is not None:
            surprises.append(e["surprise_pct"])
        if e["actual"] > e["estimate"]:
            beats += 1
        elif e["actual"] < e["estimate"]:
            misses += 1
        else:
            inline += 1
    total = beats + misses + inline

    return {
        "ticker": ticker,
        "base_rate": {
            "quarters_counted": total,
            "beats": beats,
            "misses": misses,
            "inline": inline,
            "beat_pct": round(beats / total * 100, 1) if total else None,
            "avg_surprise_pct": round(sum(surprises) / len(surprises), 2) if surprises else None,
        },
        "next_earnings": upcoming[0] if upcoming else None,
        "reported": reported,
        "upcoming": upcoming,
    }


# Forward-looking period codes in Earnings::Trend → friendly label.
# (0q = current quarter, +1q = next quarter, 0y = current FY, +1y = next FY)
_FORWARD_PERIOD_LABELS = {"0q": "curr_q", "+1q": "next_q", "0y": "curr_fy", "+1y": "next_fy"}


def _shape_trend_entry(date_str: str, period: str, e: dict) -> dict:
    """Reshape one raw Earnings::Trend entry → clean consensus + revision momentum.

    All raw values arrive as strings (or None); _f() coerces them. The EPS
    revision momentum compares the current consensus EPS vs 30 days ago — an
    upward drift is a leading sign of post-guidance analyst upgrades.
    """
    eps_cur = _f(e.get("epsTrendCurrent"))
    eps_30d = _f(e.get("epsTrend30daysAgo"))
    rev_30d_pct = None
    if eps_cur is not None and eps_30d not in (None, 0):
        rev_30d_pct = round((eps_cur - eps_30d) / abs(eps_30d) * 100, 2)
    return {
        "period": period,
        "date": date_str,
        "eps_avg": _f(e.get("earningsEstimateAvg")),
        "eps_low": _f(e.get("earningsEstimateLow")),
        "eps_high": _f(e.get("earningsEstimateHigh")),
        "eps_num_analysts": _f(e.get("earningsEstimateNumberOfAnalysts")),
        "eps_growth": _f(e.get("earningsEstimateGrowth")),
        "rev_avg": _f(e.get("revenueEstimateAvg")),
        "rev_growth": _f(e.get("revenueEstimateGrowth")),
        "eps_revision_30d_pct": rev_30d_pct,
        "revisions_up_30d": _f(e.get("epsRevisionsUpLast30days")),
        "revisions_down_30d": _f(e.get("epsRevisionsDownLast30days")),
    }


def get_earnings_trend(ticker: str) -> dict:
    """Get analyst forward consensus estimates (the closest proxy to guidance).

    Pulls the Earnings::Trend section of the fundamentals payload — sell-side
    consensus EPS/revenue for the next quarter, current FY and next FY, plus
    EPS-revision momentum. Use as the "analyst-implied" forward EPS for the A3
    valuation anchor, and the revision drift as a P3 signal-inference input.

    Args:
        ticker: EODHD ticker format (e.g. "MRVL.US")

    Returns:
        Dict with forward_estimates keyed by next_q / curr_fy / next_fy
        (+ curr_q): each has consensus eps_avg/low/high, # analysts, eps_growth,
        rev_avg, rev_growth, and revision momentum (eps_revision_30d_pct,
        revisions_up_30d, revisions_down_30d).
    """
    data = _get(f"fundamentals/{ticker}", params={"filter": "Earnings::Trend"})
    if not isinstance(data, dict):
        return {"ticker": ticker, "error": "unexpected response", "forward_estimates": {}}

    # The section is keyed by fiscal date and contains many historical 0q/0y
    # rows; for each forward period code keep only the entry with the latest date.
    latest_by_period: dict[str, tuple[str, dict]] = {}
    for date_key, entry in data.items():
        if not isinstance(entry, dict):
            continue
        period = entry.get("period")
        if period not in _FORWARD_PERIOD_LABELS:
            continue
        cur = latest_by_period.get(period)
        if cur is None or date_key > cur[0]:
            latest_by_period[period] = (date_key, entry)

    forward = {}
    for period, (date_key, entry) in latest_by_period.items():
        forward[_FORWARD_PERIOD_LABELS[period]] = _shape_trend_entry(date_key, period, entry)

    return {"ticker": ticker, "forward_estimates": forward}


def get_economic_calendar(
    from_date: str | None = None,
    to_date: str | None = None,
    country: str = "US",
    high_impact_only: bool = False,
    limit: int = 100,
) -> dict:
    """Get the economic events calendar (CPI / NFP / FOMC, etc.) with forecasts.

    High-frequency macro catalysts with forecast vs previous vs actual — feeds
    the briefing macro snapshot and event-driven watchlist gates.

    Args:
        from_date: Start date YYYY-MM-DD (default: today)
        to_date: End date YYYY-MM-DD (default: today + 14 days)
        country: 2-letter country code (default "US")
        high_impact_only: If True, keep only CPI/NFP/FOMC/PCE/GDP-class events
        limit: Max events fetched from the API (default 100)

    Returns:
        Dict with date range and events[] (date, type, period, actual,
        previous, estimate/forecast).
    """
    from_date = from_date or datetime.now().strftime("%Y-%m-%d")
    to_date = to_date or (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
    data = _get("economic-events", params={
        "country": country,
        "from": from_date,
        "to": to_date,
        "limit": limit,
    })
    rows = data if isinstance(data, list) else []

    events = []
    for r in rows:
        etype = r.get("type") or ""
        if high_impact_only and not any(k.lower() in etype.lower() for k in HIGH_IMPACT_EVENTS):
            continue
        events.append({
            "date": r.get("date", ""),
            "type": etype,
            "period": r.get("period", ""),
            "actual": r.get("actual"),
            "forecast": r.get("estimate"),
            "previous": r.get("previous"),
            "change_pct": r.get("change_percentage"),
        })

    events.sort(key=lambda x: x["date"])
    return {
        "country": country,
        "date_from": from_date,
        "date_to": to_date,
        "high_impact_only": high_impact_only,
        "count": len(events),
        "events": events,
    }


def get_fundamentals_snapshot(ticker: str) -> dict:
    """Get a compact fundamentals snapshot (valuation + analyst + key stats).

    Pulls only the useful sections via the API `filter` param to avoid the
    massive full-fundamentals payload.

    Args:
        ticker: EODHD ticker format (e.g. "MU.US")

    Returns:
        Dict with name/sector/industry, highlights, valuation, analyst_ratings,
        and selected technicals (52w range, beta, moving averages).
    """
    data = _get(f"fundamentals/{ticker}", params={
        "filter": ",".join([
            "General::Name", "General::Sector", "General::Industry",
            "Highlights", "Valuation", "AnalystRatings", "Technicals", "SharesStats",
        ]),
    })
    if not isinstance(data, dict):
        return {"ticker": ticker, "error": "unexpected response"}

    hl = data.get("Highlights") or {}
    tech = data.get("Technicals") or {}
    shares = data.get("SharesStats") or {}

    return {
        "ticker": ticker,
        "name": data.get("General::Name"),
        "sector": data.get("General::Sector"),
        "industry": data.get("General::Industry"),
        "highlights": {
            "market_cap": hl.get("MarketCapitalization"),
            "pe_ratio": hl.get("PERatio"),
            "peg_ratio": hl.get("PEGRatio"),
            "eps_ttm": hl.get("EarningsShare"),
            "profit_margin": hl.get("ProfitMargin"),
            "operating_margin_ttm": hl.get("OperatingMarginTTM"),
            "roe_ttm": hl.get("ReturnOnEquityTTM"),
            "revenue_ttm": hl.get("RevenueTTM"),
            "quarterly_revenue_growth_yoy": hl.get("QuarterlyRevenueGrowthYOY"),
            "quarterly_earnings_growth_yoy": hl.get("QuarterlyEarningsGrowthYOY"),
            "wall_street_target": hl.get("WallStreetTargetPrice"),
            "dividend_yield": hl.get("DividendYield"),
        },
        "valuation": data.get("Valuation") or {},
        "analyst_ratings": data.get("AnalystRatings") or {},
        "technicals": {
            "beta": tech.get("Beta"),
            "52w_high": tech.get("52WeekHigh"),
            "52w_low": tech.get("52WeekLow"),
            "sma_50d": tech.get("50DayMA"),
            "sma_200d": tech.get("200DayMA"),
            "short_percent_float": tech.get("ShortPercent"),
        },
        "shares_outstanding": shares.get("SharesOutstanding"),
    }


def get_macro_indicator(
    country: str = "USA",
    indicator: str = "inflation_consumer_prices_annual",
    limit: int = 12,
) -> dict:
    """Get a macroeconomic indicator time series for a country (regime context).

    Lower-frequency (annual/quarterly) World Bank-style macro data — for
    cycle/regime framing, not high-frequency trading catalysts (use
    get_economic_calendar for those).

    Common indicators:
      inflation_consumer_prices_annual, real_interest_rate, gdp_growth_annual,
      gdp_current_usd, unemployment_total_percent, population_total,
      gov_debt_percent_gdp, current_account_pct_gdp

    Args:
        country: 3-letter ISO country code (default "USA")
        indicator: EODHD macro indicator key (see common list above)
        limit: Number of most-recent data points to return (default 12)

    Returns:
        Dict with country, indicator name, period, and data[] (date, value),
        most recent first.
    """
    data = _get(f"macro-indicator/{country}", params={"indicator": indicator})
    rows = data if isinstance(data, list) else []
    rows = [r for r in rows if r.get("Value") is not None]
    rows.sort(key=lambda x: x.get("Date", ""), reverse=True)

    return {
        "country": country,
        "indicator": indicator,
        "indicator_name": rows[0].get("Indicator") if rows else None,
        "period": rows[0].get("Period") if rows else None,
        "data": [
            {"date": r.get("Date"), "value": r.get("Value")}
            for r in rows[:limit]
        ],
    }
