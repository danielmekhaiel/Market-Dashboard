import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

PST = ZoneInfo("America/Los_Angeles")
st.set_page_config(page_title="Daily Market Brief", layout="wide")

ALPHAVANTAGE_KEY = st.secrets.get("ALPHAVANTAGE_KEY", os.getenv("ALPHAVANTAGE_KEY", ""))
MARKETAUX_KEY = st.secrets.get("MARKETAUX_KEY", os.getenv("MARKETAUX_KEY", ""))
TRADING_ECONOMICS_KEY = st.secrets.get("TRADING_ECONOMICS_KEY", os.getenv("TRADING_ECONOMICS_KEY", ""))

st.markdown(
    """
<style>
.block-container {padding-top: 1rem; max-width: 1200px;}
html, body, [class*="css"] {background:#000000; color:#f5f5f5;}
.small-muted {color:#8a8a8a; font-size:0.88rem;}
.section-card {background:#111111; border:1px solid #222222; border-radius:14px; padding:12px 14px; margin-bottom:12px;}
.list-head {display:flex; gap:10px; color:#8f8f8f; font-size:0.68rem; text-transform:uppercase; letter-spacing:.09em; padding:0 8px 6px 8px;}
.list-row {display:flex; gap:10px; align-items:center; padding:8px 8px; border-top:1px solid #202020;}
.list-row:first-child {border-top:none;}
.sym {width:56px; font-weight:800; color:#ffffff; font-size:.92rem;}
.sector {width:128px; color:#c9c9c9; font-size:.85rem;}
.thesis {width:78px; font-weight:700; font-size:.72rem;}
.importance {width:86px; font-size:.72rem; font-weight:700;}
.headline {flex:1; color:#f3f3f3; font-size:.88rem; line-height:1.25;}
.badge {display:inline-block; padding:2px 7px; border-radius:999px; font-size:.64rem; font-weight:800; letter-spacing:.04em;}
.badge.bullish {background:rgba(34,197,94,.12); color:#22c55e; border:1px solid #22c55e;}
.badge.bearish {background:rgba(239,68,68,.12); color:#ef4444; border:1px solid #ef4444;}
.badge.neutral {background:#1a1a1a; color:#9ca3af; border:1px solid #333333;}
.badge.notable {background:rgba(245,158,11,.10); color:#f59e0b; border:1px solid #f59e0b;}
.badge.moderate {background:#1a1a1a; color:#c9c9c9; border:1px solid #333333;}
.badge.high {background:rgba(239,68,68,.12); color:#ef4444; border:1px solid #ef4444;}
.badge.medium {background:rgba(245,158,11,.10); color:#f59e0b; border:1px solid #f59e0b;}
.badge.low {background:#1a1a1a; color:#9ca3af; border:1px solid #333333;}
.topic {color:#9ca3af; font-weight:700; text-transform:uppercase; font-size:.68rem; letter-spacing:.08em;}
a.yf {color:#ffffff; text-decoration:none; font-weight:800;}
</style>
""",
    unsafe_allow_html=True,
)

st.title("DAILY MARKET BRIEF")
st.caption("US stocks only - catalysts, analyst moves, and macro events")


def classify_thesis(title: str) -> str:
    t = (title or "").lower()
    bullish = ["beats", "beat", "raises", "raised", "upgrade", "upgrades", "bullish", "surge", "record", "buy", "strong", "top pick", "approval", "approved", "expands", "growth", "overweight", "outperform", "positive"]
    bearish = ["misses", "miss", "cuts", "cut", "downgrade", "downgrades", "bearish", "plunge", "weak", "warning", "sell", "lawsuit", "investigation", "recall", "slumps", "slump", "probe", "underweight", "underperform", "negative"]
    if any(k in t for k in bullish):
        return "Bullish"
    if any(k in t for k in bearish):
        return "Bearish"
    return "Neutral"


def classify_importance(row) -> str:
    txt = " ".join(str(row.get(c, "")) for c in ["title", "sentiment", "tickers"]).lower()
    score = 0
    for k in ["earnings", "guidance", "fda", "sec", "merger", "acquisition", "upgrade", "downgrade", "rates", "inflation", "jobs", "cpi", "fed", "split", "ipo", "approval", "bankruptcy", "lawsuit", "deal", "conference", "meeting minutes"]:
        if k in txt:
            score += 1
    return "Notable" if score >= 2 else "Moderate"


def get_company_label(ticker):
    sec = {
        "AAPL": "Technology",
        "AMZN": "Consumer Disc",
        "AMD": "Technology",
        "META": "Communication",
        "TSLA": "Consumer Disc",
        "NVDA": "Technology",
        "JPM": "Financial",
        "XOM": "Energy",
        "MSFT": "Technology",
        "BA": "Industrials",
    }
    return sec.get(str(ticker).upper(), "US Stock")


def badge(text, cls):
    return f'<span class="badge {cls}">{text}</span>'


def fmt_time(v):
    if not v or pd.isna(v):
        return ""
    try:
        return pd.to_datetime(str(v), utc=True).tz_convert(PST).strftime("%-I:%M %p")
    except Exception:
        return str(v)


def safe_cell(v):
    s = "" if v is None else str(v)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def yahoo_link(ticker):
    ticker = str(ticker).strip()
    return f"https://finance.yahoo.com/quote/{ticker}" if ticker else ""


def sym_html(ticker):
    t = str(ticker).strip()
    return f'<a class="yf" href="{yahoo_link(t)}" target="_blank" rel="noopener noreferrer">{safe_cell(t)}</a>' if t else ""


@st.cache_data(ttl=300)
def get_alpha_news():
    if not ALPHAVANTAGE_KEY:
        return pd.DataFrame()
    url = "https://www.alphavantage.co/query"
    params = {"function": "NEWS_SENTIMENT", "apikey": ALPHAVANTAGE_KEY, "topics": "earnings,ipo,m&a,financial_markets,economy", "limit": 50}
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
    params = {"api_token": MARKETAUX_KEY, "language": "en", "limit": 50, "group_similar": "true"}
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


news = get_marketaux_news()
alpha = get_alpha_news()
econ = get_economic_calendar()

df = news if not news.empty else alpha
if not df.empty:
    df = df.copy()
    df["thesis"] = df["title"].apply(classify_thesis)
    df["importance"] = df.apply(classify_importance, axis=1)
    df["sector"] = df["tickers"].apply(lambda x: get_company_label(str(x).split(",")[0] if str(x) else ""))

last_update = datetime.now(PST).strftime("%-I:%M %p")
st.markdown(f'<div class="small-muted">{len(df)} catalyst articles found - {len(econ)} calendar items - Last updated: {last_update}</div>', unsafe_allow_html=True)

c1, c2, c3 = st.columns(3)
c1.metric("Catalysts", len(df))
c2.metric("Economic events", len(econ))
c3.metric("Updated", f"{last_update} PST")

if alpha.empty:
    st.warning("Alpha Vantage returned no rows.")
if news.empty:
    st.warning("Marketaux returned no rows.")
if econ.empty:
    st.warning("Economic calendar returned no rows.")

st.markdown("---")
st.markdown('<div class="section-card"><div class="topic">Economic calendar</div>', unsafe_allow_html=True)
if not econ.empty:
    st.markdown('<div class="list-head"><div class="sym">TIME</div><div class="sector">COUNTRY</div><div class="thesis">PRIORITY</div><div class="importance">TYPE</div><div class="headline">EVENT</div></div>', unsafe_allow_html=True)
    for _, r in econ.head(5).iterrows():
        imp = str(r.get("importance", "")).upper()
        imp_cls = "high" if "HIGH" in imp else "medium" if "MEDIUM" in imp else "low"
        st.markdown(
            f'<div class="list-row"><div class="sym">{fmt_time(r.get("time"))}</div><div class="sector">US</div><div class="thesis">{badge(imp if imp else "EVENT", imp_cls)}</div><div class="importance">{badge("US", "neutral")}</div><div class="headline">{safe_cell(r.get("event", ""))}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("---")
st.markdown('<div class="section-card"><div class="topic">Top catalysts</div>', unsafe_allow_html=True)
if not df.empty:
    st.markdown('<div class="list-head"><div class="sym">SYM</div><div class="sector">SECTOR</div><div class="thesis">THESIS</div><div class="importance">IMPORTANCE</div><div class="headline">HEADLINE</div></div>', unsafe_allow_html=True)
    for _, r in df.head(15).iterrows():
        thesis = r.get("thesis", "Neutral")
        imp = r.get("importance", "Moderate")
        sym = str(r.get("tickers", "")).split(",")[0] if r.get("tickers") else ""
        sector = r.get("sector", "US Stock")
        tcls = "bullish" if thesis == "Bullish" else "bearish" if thesis == "Bearish" else "neutral"
        icls = "notable" if imp == "Notable" else "moderate"
        st.markdown(
            f'<div class="list-row"><div class="sym">{sym_html(sym)}</div><div class="sector">{safe_cell(sector)}</div><div class="thesis">{badge(thesis.upper(), tcls)}</div><div class="importance">{badge(imp.upper(), icls)}</div><div class="headline">{safe_cell(r.get("title", ""))}</div></div>',
            unsafe_allow_html=True,
        )
else:
    st.info("No catalyst data loaded yet.")

st.markdown('<div class="small-muted">Yahoo links stay clickable, but the app no longer depends on scraping Yahoo or Finviz.</div>', unsafe_allow_html=True)
