import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

PST = ZoneInfo("America/Los_Angeles")

st.set_page_config(page_title="Daily Catalyst Brief", layout="wide")

ALPHAVANTAGE_KEY = st.secrets.get("ALPHAVANTAGE_KEY", os.getenv("ALPHAVANTAGE_KEY", ""))
MARKETAUX_KEY = st.secrets.get("MARKETAUX_KEY", os.getenv("MARKETAUX_KEY", ""))
TRADING_ECONOMICS_KEY = st.secrets.get("TRADING_ECONOMICS_KEY", os.getenv("TRADING_ECONOMICS_KEY", ""))

st.markdown(
    """
<style>
.block-container {
    padding-top: 1rem;
    max-width: 1280px;
}
html, body, [class*="css"] {
    background: #000000;
    color: #f5f5f5;
}
.section-card {
    background: #111111;
    border: 1px solid #222222;
    border-radius: 16px;
    padding: 16px 18px;
    margin-bottom: 18px;
}
.item-card {
    background: #111111;
    border: 1px solid #222222;
    border-left: 4px solid #9ca3af;
    border-radius: 14px;
    padding: 14px 16px;
    margin-top: 12px;
}
.item-card.bullish {
    border-left-color: #22c55e;
}
.item-card.bearish {
    border-left-color: #ef4444;
}
.item-title {
    font-size: 1.02rem;
    font-weight: 700;
    color: #f5f5f5;
    line-height: 1.35;
}
.item-meta {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;
}
.badge {
    display: inline-block;
    padding: 2px 8px;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: .04em;
}
.badge.bullish {
    background: rgba(34, 197, 94, 0.12);
    color: #22c55e;
    border: 1px solid #22c55e;
}
.badge.bearish {
    background: rgba(239, 68, 68, 0.12);
    color: #ef4444;
    border: 1px solid #ef4444;
}
.badge.neutral {
    background: #1a1a1a;
    color: #9ca3af;
    border: 1px solid #333333;
}
.badge.notable {
    background: rgba(245, 158, 11, 0.10);
    color: #f59e0b;
    border: 1px solid #f59e0b;
}
.badge.moderate {
    background: #1a1a1a;
    color: #c9c9c9;
    border: 1px solid #333333;
}
.badge.high {
    background: rgba(239, 68, 68, 0.12);
    color: #ef4444;
    border: 1px solid #ef4444;
}
.badge.medium {
    background: rgba(245, 158, 11, 0.10);
    color: #f59e0b;
    border: 1px solid #f59e0b;
}
.badge.low {
    background: #1a1a1a;
    color: #9ca3af;
    border: 1px solid #333333;
}
.topic {
    color: #9ca3af;
    font-weight: 700;
    text-transform: uppercase;
    font-size: .72rem;
    letter-spacing: .08em;
}
.subtle {
    color: #8a8a8a;
    font-size: .85rem;
}
.small-muted {
    color: #8a8a8a;
    font-size: .9rem;
}
</style>
""",
    unsafe_allow_html=True,
)

st.title("DAILY CATALYST BRIEF")


def classify_thesis(title: str) -> str:
    t = (title or "").lower()
    bullish = [
        "beats", "beat", "raises", "raised", "upgrade", "upgrades", "bullish", "surge",
        "record", "buy", "strong", "top pick", "approval", "approved", "expands", "growth",
        "overweight", "outperform", "positive"
    ]
    bearish = [
        "misses", "miss", "cuts", "cut", "downgrade", "downgrades", "bearish", "plunge",
        "weak", "warning", "sell", "lawsuit", "investigation", "recall", "slumps", "slump",
        "probe", "underweight", "underperform", "negative"
    ]
    if any(k in t for k in bullish):
        return "Bullish"
    if any(k in t for k in bearish):
        return "Bearish"
    return "Neutral"


def classify_importance(row) -> str:
    txt = " ".join(str(row.get(c, "")) for c in ["title", "sentiment", "tickers"]).lower()
    score = 0
    for k in [
        "earnings", "guidance", "fda", "sec", "merger", "acquisition", "upgrade",
        "downgrade", "rates", "inflation", "jobs", "cpi", "fed", "split", "ipo",
        "approval", "bankruptcy", "lawsuit", "deal", "conference", "meeting minutes"
    ]:
        if k in txt:
            score += 1
    return "Notable" if score >= 2 else "Moderate"


def badge(text, cls):
    return f'<span class="badge {cls}">{text}</span>'


def money(v):
    if pd.isna(v) or v in ("", None):
        return "—"
    return str(v)


def fmt_time(v):
    if not v or pd.isna(v):
        return ""
    try:
        dt = pd.to_datetime(str(v), utc=True)
        return dt.tz_convert(PST).strftime("%-I:%M %p")
    except Exception:
        return str(v)


@st.cache_data(ttl=300)
def get_alpha_news():
    if not ALPHAVANTAGE_KEY:
        return pd.DataFrame()
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "apikey": ALPHAVANTAGE_KEY,
        "topics": "earnings,ipo,m&a,financial_markets,economy",
        "limit": 50,
    }
    try:
        r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        rows = []
        for x in r.json().get("feed", []):
            rows.append({
                "time": x.get("time_published"),
                "title": x.get("title"),
                "source": x.get("source"),
                "url": x.get("url"),
                "sentiment": x.get("overall_sentiment_label"),
                "tickers": ",".join([t.get("ticker", "") for t in x.get("ticker_sentiment", [])[:5]]),
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_marketaux_news():
    if not MARKETAUX_KEY:
        return pd.DataFrame()
    url = "https://api.marketaux.com/v1/news/all"
    params = {
        "api_token": MARKETAUX_KEY,
        "language": "en",
        "limit": 50,
        "group_similar": "true",
    }
    try:
        r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        rows = []
        for x in r.json().get("data", []):
            rows.append({
                "time": x.get("published_at"),
                "title": x.get("title"),
                "source": x.get("source"),
                "url": x.get("url"),
                "sentiment": x.get("sentiment"),
                "tickers": ",".join([e.get("symbol", "") for e in x.get("entities", [])[:5]]),
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_economic_calendar():
    if not TRADING_ECONOMICS_KEY:
        return pd.DataFrame()
    url = "https://api.tradingeconomics.com/calendar"
    params = {"c": TRADING_ECONOMICS_KEY, "f": "json"}
    try:
        r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
        r.raise_for_status()
        rows = []
        for x in r.json():
            rows.append({
                "time": x.get("Date"),
                "country": x.get("Country"),
                "event": x.get("Event"),
                "importance": x.get("Importance"),
                "actual": x.get("Actual"),
                "forecast": x.get("Forecast"),
                "previous": x.get("Previous"),
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_yahoo_unusual_volume():
    url = "https://finance.yahoo.com/research-hub/screener/unusual-volume-stocks/"
    try:
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
        return pd.read_html(html)[0]
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_finviz_premarket():
    url = "https://finviz.com/screener.ashx?v=111&f=exch_nasd,idx_sp500"
    try:
        html = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=30).text
        tables = pd.read_html(html)
        return tables[0] if tables else pd.DataFrame()
    except Exception:
        return pd.DataFrame()


news = get_marketaux_news()
alpha = get_alpha_news()
econ = get_economic_calendar()
unusual = get_yahoo_unusual_volume()
premarket = get_finviz_premarket()

df = news if not news.empty else alpha
if not df.empty:
    df = df.copy()
    df["thesis"] = df["title"].apply(classify_thesis)
    df["importance"] = df.apply(classify_importance, axis=1)

last_update = datetime.now(PST).strftime("%-I:%M %p")
st.markdown(
    f'<div class="small-muted">{len(df)} catalyst articles found - {len(econ)} calendar items - Last updated: {last_update}</div>',
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
c1.metric("Catalysts", len(df))
c2.metric("Economic events", len(econ))
c3.metric("Updated", f"{last_update} PST")

st.markdown("---")
st.markdown(
    '<div class="section-card"><div class="topic">Economic calendar</div><div class="small-muted">today\'s high-impact events</div></div>',
    unsafe_allow_html=True,
)

if not econ.empty:
    for _, r in econ.head(5).iterrows():
        imp = str(r.get("importance", "")).upper()
        imp_cls = "high" if "high" in imp else "medium" if "medium" in imp else "low"
        st.markdown(
            f'''<div class="item-card">
<div class="item-meta">{badge(fmt_time(r.get("time")), "neutral")} {badge(str(r.get("country","")).upper(), "neutral")} {badge(imp if imp else "EVENT", imp_cls)}</div>
<div class="item-title">{r.get("event","")}</div>
<div class="subtle">Actual: {money(r.get("actual"))} - Forecast: {money(r.get("forecast"))} - Previous: {money(r.get("previous"))}</div>
</div>''',
            unsafe_allow_html=True,
        )
else:
    st.info("Add a Trading Economics API key to show today's calendar.")

st.markdown("---")
st.markdown(
    '<div class="section-card"><div class="topic">Upgrades / downgrades</div><div class="small-muted">analyst moves</div></div>',
    unsafe_allow_html=True,
)

if not df.empty:
    analyst = df[df["title"].str.contains("upgrade|downgrade|initiated|price target|rating", case=False, na=False)].copy().head(5)
    if not analyst.empty:
        for _, r in analyst.iterrows():
            thesis = r.get("thesis", "Neutral")
            imp = r.get("importance", "Moderate")
            tcls = "bullish" if thesis == "Bullish" else "bearish" if thesis == "Bearish" else "neutral"
            icls = "notable" if imp == "Notable" else "moderate"
            st.markdown(
                f'''<div class="item-card">
<div class="item-meta">{badge(r.get("tickers", ""), "neutral")} {badge(r.get("source",""), "neutral")} {badge(thesis.upper(), tcls)} {badge(imp.upper(), icls)} <span class="subtle">{fmt_time(r.get("time"))}</span></div>
<div class="item-title">{r.get("title","")}</div>
</div>''',
                unsafe_allow_html=True,
            )
    else:
        st.info("No analyst-action headlines found in the current feed.")
else:
    st.info("Connect a news feed to populate analyst actions.")

st.markdown("---")
st.markdown(
    '<div class="section-card"><div class="topic">Top catalysts</div><div class="small-muted">key news driving activity</div></div>',
    unsafe_allow_html=True,
)

if not df.empty:
    for _, r in df.head(8).iterrows():
        thesis = r.get("thesis", "Neutral")
        imp = r.get("importance", "Moderate")
        tcls = "bullish" if thesis == "Bullish" else "bearish" if thesis == "Bearish" else "neutral"
        icls = "notable" if imp == "Notable" else "moderate"
        row_class = "item-card bullish" if thesis == "Bullish" else "item-card bearish" if thesis == "Bearish" else "item-card"
        st.markdown(
            f'''<div class="{row_class}">
<div class="item-meta">{badge(r.get("tickers", ""), "neutral")} {badge(thesis.upper(), tcls)} {badge(imp.upper(), icls)} <span class="subtle">{fmt_time(r.get("time"))}</span></div>
<div class="item-title">{r.get("title","")}</div>
<div class="subtle">{r.get("source","")}</div>
</div>''',
            unsafe_allow_html=True,
        )
else:
    st.info("Add a finance news API key to show catalysts.")

st.markdown("---")
cols = st.columns(2)

with cols[0]:
    st.markdown('<div class="section-card"><div class="topic">Pre-market movers</div></div>', unsafe_allow_html=True)
    if not premarket.empty:
        for _, r in premarket.head(8).iterrows():
            sym = r.iloc[0] if len(r) > 0 else ""
            row_txt = " - ".join(str(x) for x in r.values)
            st.markdown(
                f'''<div class="item-card">
<div class="item-meta">{badge(str(sym), "neutral")}</div>
<div class="item-title">{row_txt}</div>
</div>''',
                unsafe_allow_html=True,
            )
    else:
        st.info("No pre-market table loaded yet.")

with cols[1]:
    st.markdown('<div class="section-card"><div class="topic">High volume / unusual volume</div></div>', unsafe_allow_html=True)
    if not unusual.empty:
        for _, r in unusual.head(8).iterrows():
            sym = r.iloc[0] if len(r) > 0 else ""
            row_txt = " - ".join(str(x) for x in r.values)
            st.markdown(
                f'''<div class="item-card">
<div class="item-meta">{badge(str(sym), "neutral")}</div>
<div class="item-title">{row_txt}</div>
</div>''',
                unsafe_allow_html=True,
            )
    else:
        st.info("No unusual-volume table loaded yet.")

st.markdown(
    '<div class="small-muted">Tip: this version uses black as the base, green for bullish signals, and red for bearish signals.</div>',
    unsafe_allow_html=True,
)
