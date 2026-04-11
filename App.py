import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st

PST = ZoneInfo("America/Los_Angeles")
st.set_page_config(page_title="Daily Market Brief", layout="wide")

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
.sym {width:68px; font-weight:800; color:#ffffff; font-size:.92rem;}
.sector {width:200px; color:#c9c9c9; font-size:.85rem;}
.thesis {width:78px; font-weight:700; font-size:.72rem;}
.importance {width:92px; font-size:.72rem; font-weight:700;}
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
st.caption("Economic calendar first - merged news feed - dark compact layout")


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


def fmt_time(v):
    if not v or pd.isna(v):
        return ""
    try:
        return pd.to_datetime(v, utc=True).tz_convert(PST).strftime("%-I:%M %p")
    except Exception:
        return str(v)


def sector_guess(symbol, title=""):
    s = (symbol or "").upper()
    t = (title or "").lower()
    tech = ["AAPL","MSFT","NVDA","AMD","INTC","GOOGL","GOOG","META","ORCL","CRM","ADBE","QCOM","AVGO"]
    health = ["LLY","JNJ","UNH","PFE","MRK","ABBV","AMGN","BMY","TMO","DHR"]
    fin = ["JPM","BAC","WFC","C","GS","MS","BLK","AXP","SCHW","USB"]
    energy = ["XOM","CVX","COP","SLB","EOG","MPC","PSX"]
    retail = ["AMZN","WMT","COST","TGT","HD","LOW","NKE","MCD","SBUX"]
    industrial = ["BA","CAT","DE","GE","HON","UPS","FDX","LMT","RTX"]
    if s in tech: return "Technology"
    if s in health: return "Healthcare"
    if s in fin: return "Financials"
    if s in energy: return "Energy"
    if s in retail: return "Consumer"
    if s in industrial: return "Industrials"
    if any(k in t for k in ["earnings", "guidance", "upgrade", "downgrade"]): return "Market"
    return "US Stock"


@st.cache_data(ttl=300)
def get_marketaux_news():
    if not MARKETAUX_KEY:
        return pd.DataFrame()
    try:
        r = requests.get(
            "https://api.marketaux.com/v1/news/all",
            params={"api_token": MARKETAUX_KEY, "language": "en", "limit": 50, "group_similar": "true"},
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.raise_for_status()
        rows = []
        for x in r.json().get("data", []):
            rows.append({
                "time": x.get("published_at"),
                "title": x.get("title"),
                "source": x.get("source"),
                "tickers": ",".join([e.get("symbol", "") for e in x.get("entities", [])[:5]]),
                "feed": "MarketAux",
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_alpha_news():
    if not ALPHAVANTAGE_KEY:
        return pd.DataFrame()
    try:
        r = requests.get(
            "https://www.alphavantage.co/query",
            params={"function": "NEWS_SENTIMENT", "apikey": ALPHAVANTAGE_KEY, "topics": "earnings,ipo,m&a,financial_markets,economy", "limit": 50},
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        r.raise_for_status()
        rows = []
        for x in r.json().get("feed", []):
            rows.append({
                "time": x.get("time_published"),
                "title": x.get("title"),
                "source": x.get("source"),
                "tickers": ",".join([t.get("ticker", "") for t in x.get("ticker_sentiment", [])[:5]]),
                "feed": "AlphaVantage",
            })
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_economic_calendar():
    if not TRADING_ECONOMICS_KEY:
        return pd.DataFrame()
    try:
        r = requests.get(
            "https://api.tradingeconomics.com/calendar",
            params={"c": TRADING_ECONOMICS_KEY, "f": "json"},
            timeout=30,
            headers={"User-Agent": "Mozilla/5.0"},
        )
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


def get_us_universe():
    return pd.DataFrame([
        {"symbol": "AAPL"}, {"symbol": "MSFT"}, {"symbol": "NVDA"}, {"symbol": "AMZN"}, {"symbol": "TSLA"},
        {"symbol": "META"}, {"symbol": "JPM"}, {"symbol": "XOM"}, {"symbol": "LLY"}, {"symbol": "UNH"},
        {"symbol": "AMD"}, {"symbol": "GOOGL"}, {"symbol": "BAC"}, {"symbol": "WMT"}, {"symbol": "COST"},
        {"symbol": "CAT"}, {"symbol": "GE"}, {"symbol": "BA"}, {"symbol": "MCD"}, {"symbol": "ORCL"},
        {"symbol": "CRM"}, {"symbol": "NFLX"}, {"symbol": "AVGO"}, {"symbol": "QCOM"}, {"symbol": "INTC"}
    ])


def build_mover_rows():
    uni = get_us_universe()
    rows = []
    for _, r in uni.iterrows():
        sym = r["symbol"]
        rows.append({
            "symbol": sym,
            "price": None,
            "change": None,
            "change_pct": None,
            "sector": sector_guess(sym, sym),
            "name": sym,
            "exchange": "US",
        })
    return pd.DataFrame(rows)


calendar_df = get_economic_calendar()
marketaux_df = get_marketaux_news()
alpha_df = get_alpha_news()
combined_news = pd.concat([df for df in [marketaux_df, alpha_df] if not df.empty], ignore_index=True) if any([not marketaux_df.empty, not alpha_df.empty]) else pd.DataFrame()
universe_df = build_mover_rows()

st.markdown(f'<div class="small-muted">Last updated: {datetime.now(PST).strftime("%-I:%M %p")} PST</div>', unsafe_allow_html=True)


def render_calendar(df):
    if df.empty:
        return
    st.markdown('<div class="section-card"><div class="topic">Economic calendar</div>', unsafe_allow_html=True)
    st.markdown('<div class="list-head"><div class="sym">TIME</div><div class="sector">COUNTRY</div><div class="thesis">PRIORITY</div><div class="importance">TYPE</div><div class="headline">EVENT</div></div>', unsafe_allow_html=True)
    for _, r in df.head(10).iterrows():
        imp = str(r.get("importance", "")).upper()
        imp_cls = "high" if "HIGH" in imp else "medium" if "MEDIUM" in imp else "low"
        st.markdown(
            f'<div class="list-row"><div class="sym">{fmt_time(r.get("time"))}</div><div class="sector">{safe_cell(r.get("country", ""))}</div><div class="thesis">{badge(imp if imp else "EVENT", imp_cls)}</div><div class="importance">{badge("CAL", "neutral")}</div><div class="headline">{safe_cell(r.get("event", ""))}</div></div>',
            unsafe_allow_html=True,
        )


def render_news(df, title):
    if df.empty:
        return
    st.markdown(f'<div class="section-card"><div class="topic">{title}</div>', unsafe_allow_html=True)
    df = df.copy()
    df["thesis"] = df["title"].apply(thesis_from_text)
    df["importance"] = df["title"].apply(importance_from_text)
    st.markdown('<div class="list-head"><div class="sym">SYM</div><div class="sector">SECTOR</div><div class="thesis">THESIS</div><div class="importance">IMPORTANCE</div><div class="headline">HEADLINE</div></div>', unsafe_allow_html=True)
    for _, r in df.head(15).iterrows():
        related = str(r.get("tickers", "")).split(",")[0].strip()
        sector = sector_guess(related, r.get("title", ""))
        thesis = r.get("thesis", "Neutral")
        imp = r.get("importance", "Moderate")
        tcls = "bullish" if thesis == "Bullish" else "bearish" if thesis == "Bearish" else "neutral"
        icls = "notable" if imp == "Notable" else "moderate"
        st.markdown(
            f'<div class="list-row"><div class="sym">{sym_html(related)}</div><div class="sector">{safe_cell(sector)}</div><div class="thesis">{badge(thesis.upper(), tcls)}</div><div class="importance">{badge(imp.upper(), icls)}</div><div class="headline">{safe_cell(r.get("title", ""))}</div></div>',
            unsafe_allow_html=True,
        )


def render_static_market(title, symbols, badge_text):
    st.markdown(f'<div class="section-card"><div class="topic">{title}</div>', unsafe_allow_html=True)
    st.markdown('<div class="list-head"><div class="sym">SYM</div><div class="sector">SECTOR</div><div class="thesis">THESIS</div><div class="importance">IMPORTANCE</div><div class="headline">DETAILS</div></div>', unsafe_allow_html=True)
    for sym in symbols:
        sector = sector_guess(sym, "")
        st.markdown(
            f'<div class="list-row"><div class="sym">{sym_html(sym)}</div><div class="sector">{safe_cell(sector)}</div><div class="thesis">{badge(badge_text, "neutral")}</div><div class="importance">{badge("WATCH", "moderate")}</div><div class="headline">{safe_cell(sym)} • market watch</div></div>',
            unsafe_allow_html=True,
        )


render_calendar(calendar_df)
render_news(combined_news, "Market news")
render_static_market("Upgrades / downgrades", ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA", "JPM", "XOM", "LLY"], "UP/DOWN")
render_static_market("Pre-market movers", ["AAPL", "MSFT", "NVDA", "AMZN", "TSLA", "META"], "MOVE")
render_static_market("Unusual volume", ["AMD", "BA", "COST", "CAT", "GE", "NFLX"], "VOL")
render_static_market("Catalysts", ["JPM", "XOM", "LLY", "UNH", "ORCL", "CRM"], "CAT")

st.markdown('<div class="small-muted">Yahoo links are clickable. Sectors are heuristic because this version does not use Finnhub.</div>', unsafe_allow_html=True)
