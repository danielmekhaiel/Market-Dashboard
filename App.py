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
.block-container {padding:0.8rem 1rem 1rem 1rem; max-width:1500px;}
html, body, [class*="css"] {background:#050607; color:#f2f4f8;}
header, footer, #MainMenu {visibility:hidden;}
[data-testid="stSidebar"] {background:#0b0f14; border-right:1px solid #1d2733;}
.topbar {display:flex; justify-content:space-between; align-items:center; background:linear-gradient(180deg,#0f1620,#0b0f14); border:1px solid #1f2a36; border-radius:14px; padding:14px 16px; margin-bottom:12px;}
.brand {font-size:1.2rem; font-weight:800; letter-spacing:.12em;}
.subtle {color:#93a1b2; font-size:.82rem;}
.card {background:#0b0f14; border:1px solid #1f2a36; border-radius:14px; overflow:hidden; margin-bottom:12px;}
.card-h {padding:10px 12px; border-bottom:1px solid #1f2a36; display:flex; justify-content:space-between; align-items:center; background:#0f1620;}
.card-t {font-size:.74rem; text-transform:uppercase; letter-spacing:.14em; color:#9db0c6; font-weight:800;}
.card-b {padding:8px 12px 10px 12px;}
.row {display:grid; grid-template-columns:72px 126px 78px 84px 1fr; gap:10px; align-items:center; padding:8px 0; border-top:1px solid #16202c;}
.row:first-child {border-top:none;}
.sym {font-weight:900; color:#ffffff;}
.sector {color:#aab6c4; font-size:.82rem;}
.badge {display:inline-flex; align-items:center; justify-content:center; padding:3px 8px; border-radius:999px; font-size:.64rem; font-weight:800; letter-spacing:.08em; border:1px solid transparent; white-space:nowrap;}
.bullish {background:rgba(34,197,94,.10); color:#4ade80; border-color:#1f7a45;}
.bearish {background:rgba(239,68,68,.10); color:#fb7185; border-color:#8a2a36;}
.neutral {background:#121921; color:#b5c0cf; border-color:#253244;}
.notable {background:rgba(245,158,11,.10); color:#fbbf24; border-color:#8a6912;}
.low {background:#10151d; color:#8a97a8; border-color:#243041;}
.headline {color:#ecf1f7; font-size:.86rem; line-height:1.25;}
.play {display:flex; flex-direction:column; gap:2px; padding:10px 0; border-top:1px solid #16202c;}
.play:first-child {border-top:none;}
.play-top {display:flex; justify-content:space-between; align-items:center; gap:8px;}
.play-title {font-weight:900; color:#fff;}
.play-sub {font-size:.8rem; color:#aab6c4;}
.hr {height:1px; background:#16202c; margin:10px 0;}
a.yf {color:#fff; text-decoration:none; font-weight:900;}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    f"""<div class="topbar">
    <div>
        <div class="brand">MARKET BRIEF</div>
        <div class="subtle">Economic calendar | catalysts | analyst actions | play scan</div>
    </div>
    <div style="text-align:right;">
        <div class="subtle">Last updated</div>
        <div style="font-weight:800;">{datetime.now(PST).strftime('%b %-d, %-I:%M %p PST')}</div>
    </div>
</div>""",
    unsafe_allow_html=True,
)


def safe_cell(v):
    s = "" if v is None else str(v)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def sym_html(ticker):
    t = str(ticker).strip()
    if not t:
        return ""
    return f'<a class="yf" href="https://finance.yahoo.com/quote/{t}" target="_blank" rel="noopener noreferrer">{safe_cell(t)}</a>'


def badge(text, cls="neutral"):
    return f'<span class="badge {cls}">{safe_cell(text)}</span>'


def thesis_from_text(text):
    t = (text or "").lower()
    if any(k in t for k in ["beat", "raises", "upgrade", "buy", "approval", "approved", "strong", "surge", "outperform"]):
        return "Bullish"
    if any(k in t for k in ["miss", "cuts", "downgrade", "sell", "weak", "lawsuit", "probe", "plunge", "slump"]):
        return "Bearish"
    return "Neutral"


def importance_from_text(text):
    t = (text or "").lower()
    return "Notable" if any(k in t for k in ["earnings", "guidance", "fda", "sec", "merger", "acquisition", "fed", "cpi", "jobs", "rates", "deal", "ipo"]) else "Low"


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
    if s in ["AAPL","MSFT","NVDA","AMD","INTC","GOOGL","GOOG","META","ORCL","CRM","ADBE","QCOM","AVGO"]: return "Technology"
    if s in ["LLY","JNJ","UNH","PFE","MRK","ABBV","AMGN","BMY","TMO","DHR"]: return "Healthcare"
    if s in ["JPM","BAC","WFC","C","GS","MS","BLK","AXP","SCHW","USB"]: return "Financials"
    if s in ["XOM","CVX","COP","SLB","EOG","MPC","PSX"]: return "Energy"
    if s in ["AMZN","WMT","COST","TGT","HD","LOW","NKE","MCD","SBUX"]: return "Consumer"
    if s in ["BA","CAT","DE","GE","HON","UPS","FDX","LMT","RTX"]: return "Industrials"
    if any(k in t for k in ["earnings", "guidance", "upgrade", "downgrade"]): return "Market"
    return "US Stock"


@st.cache_data(ttl=300)
def get_news(url, params):
    r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.json()


@st.cache_data(ttl=300)
def get_marketaux_news():
    if not MARKETAUX_KEY:
        return pd.DataFrame()
    try:
        data = get_news("https://api.marketaux.com/v1/news/all", {"api_token": MARKETAUX_KEY, "language": "en", "limit": 50, "group_similar": "true"})
        rows = []
        for x in data.get("data", []):
            rows.append({"time": x.get("published_at"), "title": x.get("title"), "tickers": ",".join([e.get("symbol", "") for e in x.get("entities", [])[:5]])})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_alpha_news():
    if not ALPHAVANTAGE_KEY:
        return pd.DataFrame()
    try:
        data = get_news("https://www.alphavantage.co/query", {"function": "NEWS_SENTIMENT", "apikey": ALPHAVANTAGE_KEY, "topics": "earnings,ipo,m&a,financial_markets,economy", "limit": 50})
        rows = []
        for x in data.get("feed", []):
            rows.append({"time": x.get("time_published"), "title": x.get("title"), "tickers": ",".join([t.get("ticker", "") for t in x.get("ticker_sentiment", [])[:5]])})
        return pd.DataFrame(rows)
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=300)
def get_economic_calendar():
    if not TRADING_ECONOMICS_KEY:
        return pd.DataFrame()
    try:
        data = get_news("https://api.tradingeconomics.com/calendar", {"c": TRADING_ECONOMICS_KEY, "f": "json"})
        return pd.DataFrame([{"time": x.get("Date"), "country": x.get("Country"), "event": x.get("Event"), "importance": x.get("Importance"), "actual": x.get("Actual"), "forecast": x.get("Forecast"), "previous": x.get("Previous")} for x in data])
    except Exception:
        return pd.DataFrame()


def get_us_universe():
    return pd.DataFrame([{"symbol": s} for s in ["AAPL","MSFT","NVDA","AMZN","TSLA","META","JPM","XOM","LLY","UNH","AMD","GOOGL","BAC","WMT","COST","CAT","GE","BA","MCD","ORCL","CRM","NFLX","AVGO","QCOM","INTC"]])


def build_mover_rows():
    rows = []
    for sym in get_us_universe()["symbol"].tolist():
        rows.append({"symbol": sym, "sector": sector_guess(sym), "headline": "Watchlist", "thesis": "Neutral", "importance": "Low"})
    return pd.DataFrame(rows)


calendar_df = get_economic_calendar()
marketaux_df = get_marketaux_news()
alpha_df = get_alpha_news()
combined_news = pd.concat([df for df in [marketaux_df, alpha_df] if not df.empty], ignore_index=True) if any([not marketaux_df.empty, not alpha_df.empty]) else pd.DataFrame()
universe_df = build_mover_rows()


def card(title):
    return f'<div class="card"><div class="card-h"><div class="card-t">{title}</div></div><div class="card-b">'


def endcard():
    return "</div></div>"


def render_calendar(df):
    if df.empty:
        return
    st.markdown(card("Economic calendar"), unsafe_allow_html=True)
    for _, r in df.head(8).iterrows():
        imp = str(r.get("importance", "")).upper()
        cls = "notable" if "HIGH" in imp or "MEDIUM" in imp else "low"
        st.markdown(
            f'<div class="row"><div class="sym">{fmt_time(r.get("time"))}</div><div class="sector">{safe_cell(r.get("country", ""))}</div><div>{badge(imp or "EVENT", cls)}</div><div>{badge("CAL", "neutral")}</div><div class="headline">{safe_cell(r.get("event", ""))}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(endcard(), unsafe_allow_html=True)


def render_news(df, title):
    if df.empty:
        return
    st.markdown(card(title), unsafe_allow_html=True)
    df = df.copy()
    df["thesis"] = df["title"].apply(thesis_from_text)
    df["importance"] = df["title"].apply(importance_from_text)
    for _, r in df.head(10).iterrows():
        related = str(r.get("tickers", "")).split(",")[0].strip()
        thesis = r.get("thesis", "Neutral")
        imp = r.get("importance", "Low")
        st.markdown(
            f'<div class="row"><div class="sym">{sym_html(related)}</div><div class="sector">{safe_cell(sector_guess(related, r.get("title", "")))}</div><div>{badge(thesis, "bullish" if thesis=="Bullish" else "bearish" if thesis=="Bearish" else "neutral")}</div><div>{badge(imp, "notable" if imp=="Notable" else "low")}</div><div class="headline">{safe_cell(r.get("title", ""))}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(endcard(), unsafe_allow_html=True)


def render_opportunity_panel(title, symbols, style, note):
    st.markdown(card(title), unsafe_allow_html=True)
    for sym in symbols:
        st.markdown(
            f'<div class="play"><div class="play-top"><div class="play-title">{sym_html(sym)}</div><div>{badge(style, "bullish" if style in ["Catalyst", "Setup"] else "neutral")}</div></div><div class="play-sub">{safe_cell(sector_guess(sym))} | {safe_cell(note)}</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(endcard(), unsafe_allow_html=True)


left, right = st.columns([1.5, 1], gap="large")
with left:
    render_calendar(calendar_df)
    render_news(combined_news, "Catalyst headlines")
    st.markdown(card("Analyst actions"), unsafe_allow_html=True)
    for sym in ["AAPL","MSFT","NVDA","AMZN","TSLA","JPM","LLY","XOM"]:
        st.markdown(
            f'<div class="row"><div class="sym">{sym_html(sym)}</div><div class="sector">{safe_cell(sector_guess(sym))}</div><div>{badge("RATING", "neutral")}</div><div>{badge("WATCH", "low")}</div><div class="headline">{safe_cell(sym)} upgrade/downgrade watch</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(endcard(), unsafe_allow_html=True)

with right:
    render_opportunity_panel("Potential plays", ["NVDA","LLY","AMD","ORCL","CRM","BA"], "Setup", "catalyst + analyst interest")
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown(card("Watchlist"), unsafe_allow_html=True)
    for _, r in universe_df.head(8).iterrows():
        st.markdown(
            f'<div class="row"><div class="sym">{sym_html(r["symbol"])}</div><div class="sector">{safe_cell(r["sector"])}</div><div>{badge("WATCH", "neutral")}</div><div>{badge("LOW", "low")}</div><div class="headline">liquid large-cap name</div></div>',
            unsafe_allow_html=True,
        )
    st.markdown(endcard(), unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")
with col1:
    render_opportunity_panel("Catalyst focus", ["NVDA","AAPL","LLY","AMD"], "Catalyst", "earnings, guidance, news")
with col2:
    render_opportunity_panel("Rating focus", ["MSFT","ORCL","CRM","JPM"], "Rating", "upgrade / downgrade cluster")

st.markdown('<div class="subtle" style="margin-top:10px;">Yahoo links are clickable. Sectors are heuristic because this version does not use Finnhub.</div>', unsafe_allow_html=True)
