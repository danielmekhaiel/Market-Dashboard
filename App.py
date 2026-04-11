import os
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

PST = ZoneInfo("America/Los_Angeles")
st.set_page_config(page_title="Daily Market Brief", layout="wide")

FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", os.getenv("FINNHUB_API_KEY", ""))
MARKETAUX_KEY = st.secrets.get("MARKETAUX_KEY", os.getenv("MARKETAUX_KEY", ""))
ALPHAVANTAGE_KEY = st.secrets.get("ALPHAVANTAGE_KEY", os.getenv("ALPHAVANTAGE_KEY", ""))
TRADING_ECONOMICS_KEY = st.secrets.get("TRADING_ECONOMICS_KEY", os.getenv("TRADING_ECONOMICS_KEY", ""))

st.markdown(
    """
<style>
.block-container {padding-top: 1rem; max-width: 1280px;}
html, body, [class*="css"] {background:#000000; color:#f5f5f5;}
.small-muted {color:#8a8a8a; font-size:0.88rem;}
.section-card {background:#111111; border:1px solid #222222; border-radius:14px; padding:12px 14px; margin-bottom:12px;}
.list-head {display:flex; gap:10px; color:#8f8f8f; font-size:0.68rem; text-transform:uppercase; letter-spacing:.09em; padding:0 8px 6px 8px;}
.list-row {display:flex; gap:10px; align-items:center; padding:8px 8px; border-top:1px solid #202020;}
.list-row:first-child {border-top:none;}
.sym {width:64px; font-weight:800; color:#ffffff; font-size:.92rem;}
.sector {width:190px; color:#c9c9c9; font-size:.85rem;}
.thesis {width:78px; font-weight:700; font-size:.72rem;}
.importance {width:92px; font-size:.72rem; font-weight:700;}
.headline {flex:1; color:#f3f3f3; font-size:.88rem; line-height:1.25;}
.badge {display:inline-block; padding:2px 7px; border-radius:999px; font-size:.64rem; font-weight:800; letter-spacing:.04em;}
.badge.bullish {background:rgba(34,197,94,.12); color:#22c55e; border:1px solid #22c55e;}
.badge.bearish {background:rgba(239,68,68,.12); color:#ef4444; border:1px solid #ef4444;}
.badge.neutral {background:#1a1a1a; color:#9ca3af; border:1px solid #333333;}
.badge.notable {background:rgba(245,158,11,.10); color:#f59e0b; border:1px solid #f59e0b;}
.badge.moderate {background:#1a1a1a; color:#c9c9c9; border:1px solid #333333;}
a.yf {color:#ffffff; text-decoration:none; font-weight:800;}
</style>
""",
    unsafe_allow_html=True,
)

st.title("DAILY MARKET BRIEF")
st.caption("Finnhub live quotes + original news sources + Yahoo links")


def badge(text, cls):
    return f'<span class="badge {cls}">{text}</span>'


def safe_cell(v):
    s = "" if v is None else str(v)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def yahoo_link(ticker):
    ticker = str(ticker).strip()
    return f"https://finance.yahoo.com/quote/{ticker}" if ticker else ""


def sym_html(ticker):
    t = str(ticker).strip()
    if not t:
        return ""
    return f'<a class="yf" href="{yahoo_link(t)}" target="_blank" rel="noopener noreferrer">{safe_cell(t)}</a>'


def thesis_from_text(text):
    t = (text or "").lower()
    bullish = ["beat", "beats", "raises", "raised", "upgrade", "upgrades", "buy", "strong", "record", "approval", "approved", "growth", "outperform", "overweight", "positive", "surge"]
    bearish = ["miss", "misses", "cuts", "cut", "downgrade", "downgrades", "sell", "weak", "lawsuit", "investigation", "recall", "slumps", "slump", "probe", "negative", "plunge"]
    if any(k in t for k in bullish):
        return "Bullish"
    if any(k in t for k in bearish):
        return "Bearish"
    return "Neutral"


def importance_from_text(text):
    t = (text or "").lower()
    notable = ["earnings", "guidance", "fda", "sec", "merger", "acquisition", "fed", "cpi", "inflation", "jobs", "rates", "approval", "lawsuit", "deal", "ipo"]
    return "Notable" if any(k in t for k in notable) else "Moderate"


@st.cache_data(ttl=300)
def finnhub_get(path, params=None):
    if not FINNHUB_API_KEY:
        raise ValueError("Missing FINNHUB_API_KEY")
    params = params or {}
    params["token"] = FINNHUB_API_KEY
    url = f"https://finnhub.io/api/v1/{path}"
    r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=3600)
def get_profile(symbol):
    return finnhub_get("stock/profile2", {"symbol": symbol})


@st.cache_data(ttl=300)
def get_quote(symbol):
    return finnhub_get("quote", {"symbol": symbol})


@st.cache_data(ttl=300)
def get_finnhub_news():
    data = finnhub_get("news", {"category": "general"})
    rows = []
    for x in data[:50]:
        rows.append({
            "time": x.get("datetime"),
            "title": x.get("headline"),
            "source": x.get("source"),
            "url": x.get("url"),
            "tickers": x.get("related", ""),
            "feed": "Finnhub",
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def get_marketaux_news():
    if not MARKETAUX_KEY:
        return pd.DataFrame()
    url = "https://api.marketaux.com/v1/news/all"
    params = {"api_token": MARKETAUX_KEY, "language": "en", "limit": 50, "group_similar": "true"}
    r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    rows = []
    for x in r.json().get("data", []):
        rows.append({
            "time": x.get("published_at"),
            "title": x.get("title"),
            "source": x.get("source"),
            "url": x.get("url"),
            "tickers": ",".join([e.get("symbol", "") for e in x.get("entities", [])[:5]]),
            "feed": "MarketAux",
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def get_alpha_news():
    if not ALPHAVANTAGE_KEY:
        return pd.DataFrame()
    url = "https://www.alphavantage.co/query"
    params = {"function": "NEWS_SENTIMENT", "apikey": ALPHAVANTAGE_KEY, "topics": "earnings,ipo,m&a,financial_markets,economy", "limit": 50}
    r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    rows = []
    for x in r.json().get("feed", []):
        rows.append({
            "time": x.get("time_published"),
            "title": x.get("title"),
            "source": x.get("source"),
            "url": x.get("url"),
            "tickers": ",".join([t.get("ticker", "") for t in x.get("ticker_sentiment", [])[:5]]),
            "feed": "AlphaVantage",
        })
    return pd.DataFrame(rows)


@st.cache_data(ttl=300)
def get_economic_calendar():
    if not TRADING_ECONOMICS_KEY:
        return pd.DataFrame()
    url = "https://api.tradingeconomics.com/calendar"
    params = {"c": TRADING_ECONOMICS_KEY, "f": "json"}
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
            "feed": "TradingEconomics",
        })
    return pd.DataFrame(rows)


def sector_label(profile):
    if not profile or not isinstance(profile, dict):
        return "Unknown"
    sector = (profile.get("gsector") or "").strip()
    industry = (profile.get("finnhubIndustry") or "").strip()
    if sector and industry:
        return f"{sector} / {industry}"
    if sector:
        return sector
    if industry:
        return industry
    return "Unknown"


def fmt_time(v):
    if not v or pd.isna(v):
        return ""
    try:
        if isinstance(v, str) and len(v) > 10:
            return pd.to_datetime(v, utc=True).tz_convert(PST).strftime("%-I:%M %p")
        return pd.to_datetime(v, utc=True).tz_convert(PST).strftime("%-I:%M %p")
    except Exception:
        return str(v)


if not FINNHUB_API_KEY:
    st.error("Missing FINNHUB_API_KEY in Streamlit secrets.")
    st.stop()

watchlist_text = st.text_input("Track tickers", "AAPL,MSFT,NVDA,TSLA,AMZN").upper()
watchlist = [s.strip() for s in watchlist_text.split(",") if s.strip()]

finnhub_news = pd.DataFrame()
marketaux_news = pd.DataFrame()
alpha_news = pd.DataFrame()
econ = pd.DataFrame()

try:
    finnhub_news = get_finnhub_news()
except Exception as e:
    st.error(f"Finnhub news failed: {e}")

try:
    marketaux_news = get_marketaux_news()
except Exception as e:
    st.error(f"MarketAux failed: {e}")

try:
    alpha_news = get_alpha_news()
except Exception as e:
    st.error(f"Alpha Vantage failed: {e}")

try:
    econ = get_economic_calendar()
except Exception as e:
    st.error(f"Trading Economics failed: {e}")

rows = []
profile_cache = {}

for sym in watchlist:
    try:
        q = get_quote(sym)
        p = get_profile(sym)
        profile_cache[sym] = p
        cur = q.get("c")
        prev = q.get("pc")
        chg = (cur - prev) if cur is not None and prev is not None else None
        chg_pct = (chg / prev * 100) if chg is not None and prev else None
        rows.append({
            "symbol": sym,
            "price": cur,
            "change": chg,
            "change_pct": chg_pct,
            "sector": sector_label(p),
            "name": p.get("name") if isinstance(p, dict) else "",
            "exchange": p.get("exchange") if isinstance(p, dict) else "",
        })
    except Exception as e:
        rows.append({
            "symbol": sym,
            "price": None,
            "change": None,
            "change_pct": None,
            "sector": f"Error: {e}",
            "name": "",
            "exchange": "",
        })

quote_df = pd.DataFrame(rows)

c1, c2, c3, c4 = st.columns(4)
c1.metric("Tracked symbols", len(watchlist))
c2.metric("Finnhub quotes", int(quote_df["price"].notna().sum()) if not quote_df.empty else 0)
c3.metric("News feeds", sum([not finnhub_news.empty, not marketaux_news.empty, not alpha_news.empty]))
c4.metric("Calendar rows", len(econ))

st.markdown("---")
st.markdown('<div class="section-card"><div class="topic">Watchlist quotes</div>', unsafe_allow_html=True)
st.markdown('<div class="list-head"><div class="sym">SYM</div><div class="sector">SECTOR</div><div class="thesis">MOVE</div><div class="importance">PRICE</div><div class="headline">DETAILS</div></div>', unsafe_allow_html=True)

for _, r in quote_df.iterrows():
    chg = r.get("change")
    chg_pct = r.get("change_pct")
    move = "UP" if pd.notna(chg) and chg >= 0 else "DOWN" if pd.notna(chg) else "N/A"
    move_cls = "bullish" if move == "UP" else "bearish" if move == "DOWN" else "neutral"
    price = f"${r['price']:.2f}" if pd.notna(r.get("price")) else "N/A"
    details = f"{r.get('name', '')} · {r.get('exchange', '')}".strip(" ·")
    if pd.notna(chg) and pd.notna(chg_pct):
        details += f" · {chg:+.2f} ({chg_pct:+.2f}%)"
    st.markdown(
        f'<div class="list-row"><div class="sym">{sym_html(r["symbol"])}</div><div class="sector">{safe_cell(r.get("sector", "Unknown"))}</div><div class="thesis">{badge(move, move_cls)}</div><div class="importance">{badge(price, "moderate")}</div><div class="headline">{safe_cell(details)}</div></div>',
        unsafe_allow_html=True,
    )

st.markdown("---")
st.markdown('<div class="section-card"><div class="topic">Top movers</div>', unsafe_allow_html=True)
movers = quote_df.dropna(subset=["change_pct"]).copy() if not quote_df.empty else pd.DataFrame()
if not movers.empty:
    movers = movers.sort_values("change_pct", ascending=False)
    st.markdown('<div class="list-head"><div class="sym">SYM</div><div class="sector">SECTOR</div><div class="thesis">MOVE</div><div class="importance">PRICE</div><div class="headline">DETAILS</div></div>', unsafe_allow_html=True)
    for _, r in movers.head(10).iterrows():
        move = "UP" if r["change_pct"] >= 0 else "DOWN"
        move_cls = "bullish" if move == "UP" else "bearish"
        price = f"${r['price']:.2f}" if pd.notna(r.get("price")) else "N/A"
        details = f"{r.get('name', '')} · {r.get('exchange', '')} · {r['change']:+.2f} ({r['change_pct']:+.2f}%)"
        st.markdown(
            f'<div class="list-row"><div class="sym">{sym_html(r["symbol"])}</div><div class="sector">{safe_cell(r.get("sector", "Unknown"))}</div><div class="thesis">{badge(move, move_cls)}</div><div class="importance">{badge(price, "moderate")}</div><div class="headline">{safe_cell(details)}</div></div>',
            unsafe_allow_html=True,
        )
else:
    st.info("No movers available from the current watchlist.")

def render_news_section(title, df, source_label):
    st.markdown(f'<div class="section-card"><div class="topic">{title}</div>', unsafe_allow_html=True)
    if df.empty:
        st.info(f"No rows returned from {source_label}.")
        return
    df = df.copy()
    if "title" in df.columns:
        df["thesis"] = df["title"].apply(thesis_from_text)
        df["importance"] = df["title"].apply(importance_from_text)
    st.markdown('<div class="list-head"><div class="sym">SYM</div><div class="sector">SECTOR</div><div class="thesis">THESIS</div><div class="importance">IMPORTANCE</div><div class="headline">HEADLINE</div></div>', unsafe_allow_html=True)
    for _, r in df.head(12).iterrows():
        related = str(r.get("tickers", "")).split(",")[0].strip()
        prof = profile_cache.get(related, {}) if related else {}
        sector = sector_label(prof) if related else source_label
        thesis = r.get("thesis", "Neutral")
        imp = r.get("importance", "Moderate")
        tcls = "bullish" if thesis == "Bullish" else "bearish" if thesis == "Bearish" else "neutral"
        icls = "notable" if imp == "Notable" else "moderate"
        st.markdown(
            f'<div class="list-row"><div class="sym">{sym_html(related)}</div><div class="sector">{safe_cell(sector)}</div><div class="thesis">{badge(thesis.upper(), tcls)}</div><div class="importance">{badge(imp.upper(), icls)}</div><div class="headline">{safe_cell(r.get("title", r.get("event", "")))}</div></div>',
            unsafe_allow_html=True,
        )

st.markdown("---")
render_news_section("Finnhub news", finnhub_news, "Finnhub")
st.markdown("---")
render_news_section("MarketAux news", marketaux_news, "MarketAux")
st.markdown("---")
render_news_section("Alpha Vantage news", alpha_news, "Alpha Vantage")

st.markdown("---")
st.markdown('<div class="section-card"><div class="topic">Economic calendar</div>', unsafe_allow_html=True)
if not econ.empty:
    st.markdown('<div class="list-head"><div class="sym">TIME</div><div class="sector">COUNTRY</div><div class="thesis">PRIORITY</div><div class="importance">TYPE</div><div class="headline">EVENT</div></div>', unsafe_allow_html=True)
    for _, r in econ.head(8).iterrows():
        imp = str(r.get("importance", "")).upper()
        imp_cls = "high" if "HIGH" in imp else "medium" if "MEDIUM" in imp else "low"
        st.markdown(
            f'<div class="list-row"><div class="sym">{fmt_time(r.get("time"))}</div><div class="sector">{safe_cell(r.get("country", ""))}</div><div class="thesis">{badge(imp if imp else "EVENT", imp_cls)}</div><div class="importance">{badge("CAL", "neutral")}</div><div class="headline">{safe_cell(r.get("event", ""))}</div></div>',
            unsafe_allow_html=True,
        )
else:
    st.info("No economic calendar rows returned.")

st.markdown('<div class="small-muted">Finnhub supplies live quotes and company profiles. MarketAux, Alpha Vantage, and Trading Economics remain as original supporting sources.</div>', unsafe_allow_html=True)
