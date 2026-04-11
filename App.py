from pathlib import Path
code = r'''import os
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

st.markdown("""
<style>
.block-container {padding:0.75rem 1rem; max-width:1500px;}
html, body, [class*="css"] {background:#050607; color:#eef3f8;}
header, footer, #MainMenu {visibility:hidden;}
.topbar {display:flex; justify-content:space-between; align-items:center; background:linear-gradient(180deg,#0f1620,#0b0f14); border:1px solid #1f2a36; border-radius:14px; padding:14px 16px; margin-bottom:12px;}
.brand {font-size:1.15rem; font-weight:900; letter-spacing:.12em;}
.subtle {color:#93a1b2; font-size:.82rem;}
.card {background:#0b0f14; border:1px solid #1f2a36; border-radius:14px; overflow:hidden; margin-bottom:12px;}
.card-h {padding:10px 12px; border-bottom:1px solid #1f2a36; background:#0f1620;}
.card-t {font-size:.74rem; text-transform:uppercase; letter-spacing:.14em; color:#9db0c6; font-weight:800;}
.card-b {padding:8px 12px;}
.row {display:grid; grid-template-columns:72px 120px 78px 84px 1fr; gap:10px; align-items:center; padding:8px 0; border-top:1px solid #16202c;}
.row:first-child {border-top:none;}
.sym {font-weight:900; color:#fff;}
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
a.yf {color:#fff; text-decoration:none; font-weight:900;}
</style>
""", unsafe_allow_html=True)

st.markdown(f'''<div class="topbar"><div><div class="brand">MARKET BRIEF</div><div class="subtle">Dynamic watchlist | premarket movers | gappers | unusual volume</div></div><div style="text-align:right;"><div class="subtle">Last updated</div><div style="font-weight:800;">{datetime.now(PST).strftime('%b %-d, %-I:%M %p PST')}</div></div></div>''', unsafe_allow_html=True)


def esc(v):
    s = "" if v is None else str(v)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def link(t):
    t = str(t).strip()
    return f'<a class="yf" href="https://finance.yahoo.com/quote/{t}" target="_blank" rel="noopener noreferrer">{esc(t)}</a>' if t else ""

def tag(txt, cls="neutral"):
    return f'<span class="badge {cls}">{esc(txt)}</span>'

def thesis(txt):
    t = (txt or "").lower()
    if any(k in t for k in ["beat", "raises", "upgrade", "buy", "approval", "approved", "strong", "surge", "outperform"]): return "Bullish"
    if any(k in t for k in ["miss", "cuts", "downgrade", "sell", "weak", "lawsuit", "probe", "plunge", "slump"]): return "Bearish"
    return "Neutral"

def important(txt):
    t = (txt or "").lower()
    return "Notable" if any(k in t for k in ["earnings", "guidance", "fda", "sec", "merger", "acquisition", "fed", "cpi", "jobs", "rates", "deal", "ipo"]) else "Low"

def tztime(v):
    if not v or pd.isna(v): return ""
    try: return pd.to_datetime(v, utc=True).tz_convert(PST).strftime("%-I:%M %p")
    except Exception: return str(v)

def sector(sym):
    s = (sym or "").upper()
    if s in ["AAPL","MSFT","NVDA","AMD","INTC","GOOGL","GOOG","META","ORCL","CRM","ADBE","QCOM","AVGO"]: return "Technology"
    if s in ["LLY","JNJ","UNH","PFE","MRK","ABBV","AMGN","BMY","TMO","DHR"]: return "Healthcare"
    if s in ["JPM","BAC","WFC","C","GS","MS","BLK","AXP","SCHW","USB"]: return "Financials"
    if s in ["XOM","CVX","COP","SLB","EOG","MPC","PSX"]: return "Energy"
    if s in ["AMZN","WMT","COST","TGT","HD","LOW","NKE","MCD","SBUX"]: return "Consumer"
    if s in ["BA","CAT","DE","GE","HON","UPS","FDX","LMT","RTX"]: return "Industrials"
    return "US Stock"

@st.cache_data(ttl=300)
def fetch(url, params):
    r = requests.get(url, params=params, timeout=30, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    return r.json()

@st.cache_data(ttl=300)
def news_marketaux():
    if not MARKETAUX_KEY: return pd.DataFrame()
    try:
        data = fetch("https://api.marketaux.com/v1/news/all", {"api_token": MARKETAUX_KEY, "language": "en", "limit": 50, "group_similar": "true"})
        return pd.DataFrame([{ "time": x.get("published_at"), "title": x.get("title"), "tickers": ",".join([e.get("symbol", "") for e in x.get("entities", [])[:5]]) } for x in data.get("data", [])])
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def news_alpha():
    if not ALPHAVANTAGE_KEY: return pd.DataFrame()
    try:
        data = fetch("https://www.alphavantage.co/query", {"function": "NEWS_SENTIMENT", "apikey": ALPHAVANTAGE_KEY, "topics": "earnings,ipo,m&a,financial_markets,economy", "limit": 50})
        return pd.DataFrame([{ "time": x.get("time_published"), "title": x.get("title"), "tickers": ",".join([t.get("ticker", "") for t in x.get("ticker_sentiment", [])[:5]]) } for x in data.get("feed", [])])
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def calendar():
    if not TRADING_ECONOMICS_KEY: return pd.DataFrame()
    try:
        data = fetch("https://api.tradingeconomics.com/calendar", {"c": TRADING_ECONOMICS_KEY, "f": "json"})
        return pd.DataFrame([{ "time": x.get("Date"), "country": x.get("Country"), "event": x.get("Event"), "importance": x.get("Importance") } for x in data])
    except Exception:
        return pd.DataFrame()

@st.cache_data(ttl=300)
def q(symbol):
    if not ALPHAVANTAGE_KEY: return None
    try:
        data = fetch("https://www.alphavantage.co/query", {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": ALPHAVANTAGE_KEY})
        g = data.get("Global Quote", {})
        price = float(g.get("05. price", 0) or 0)
        prev = float(g.get("08. previous close", 0) or 0)
        op = float(g.get("02. open", 0) or 0)
        vol = float(g.get("06. volume", 0) or 0)
        chg = float((g.get("10. change percent", "0%").replace("%", "") or 0))
        return {"price": price, "prev": prev, "open": op, "vol": vol, "chg": chg}
    except Exception:
        return None

def universe():
    return ["AAPL","MSFT","NVDA","AMZN","TSLA","META","JPM","XOM","LLY","UNH","AMD","GOOGL","BAC","WMT","COST","CAT","GE","BA","MCD","ORCL","CRM","NFLX","AVGO","QCOM","INTC"]

def candidates(df):
    if df.empty: return pd.DataFrame()
    x = df.copy()
    x["ticker"] = x["tickers"].fillna("").astype(str).str.split(",").str[0].str.strip()
    x = x[x["ticker"] != ""]
    x["score"] = 1 + (x["title"].apply(important).eq("Notable")).astype(int)*2 + (x["title"].str.contains("upgrade|downgrade", case=False, na=False)).astype(int)*2 + (x["title"].str.contains("earnings|guidance|merger|acquisition|fda|ipo", case=False, na=False)).astype(int)*2
    g = x.groupby("ticker", as_index=False).agg(score=("score", "sum"), title=("title", "first"))
    g["sector"] = g["ticker"].apply(sector)
    return g.sort_values("score", ascending=False)

def movers():
    rows=[]
    for s in universe():
        r=q(s)
        if r and abs(r["chg"])>=2:
            rows.append({"symbol": s, "sector": sector(s), "chg": r["chg"]})
    return pd.DataFrame(rows).sort_values("chg", ascending=False) if rows else pd.DataFrame()

def gappers():
    rows=[]
    for s in universe():
        r=q(s)
        if r and r["prev"] and r["open"]:
            gap=((r["open"]-r["prev"])/r["prev"])*100
            if abs(gap)>=2: rows.append({"symbol": s, "sector": sector(s), "gap": gap})
    return pd.DataFrame(rows).sort_values("gap", ascending=False) if rows else pd.DataFrame()

def volscan():
    rows=[]
    for s in universe():
        r=q(s)
        if r and r["vol"]:
            rows.append({"symbol": s, "sector": sector(s), "vol": r["vol"]})
    return pd.DataFrame(rows).sort_values("vol", ascending=False).head(8) if rows else pd.DataFrame()

def box(title): return f'<div class="card"><div class="card-h"><div class="card-t">{title}</div></div><div class="card-b">'
def endbox(): return '</div></div>'

def render_calendar(df):
    st.markdown(box("Economic calendar"), unsafe_allow_html=True)
    if df.empty:
        st.markdown('<div class="subtle">No calendar data.</div>', unsafe_allow_html=True)
    else:
        for _, r in df.head(8).iterrows():
            imp = str(r.get("importance", "")).upper()
            cls = "notable" if "HIGH" in imp or "MEDIUM" in imp else "low"
            st.markdown(f'<div class="row"><div class="sym">{tztime(r.get("time"))}</div><div class="sector">{esc(r.get("country", ""))}</div><div>{tag(imp or "EVENT", cls)}</div><div>{tag("CAL", "neutral")}</div><div class="headline">{esc(r.get("event", ""))}</div></div>', unsafe_allow_html=True)
    st.markdown(endbox(), unsafe_allow_html=True)

def render_news(df, title):
    st.markdown(box(title), unsafe_allow_html=True)
    if df.empty:
        st.markdown('<div class="subtle">No news data.</div>', unsafe_allow_html=True)
    else:
        d=df.copy(); d["thesis"]=d["title"].apply(thesis); d["importance"]=d["title"].apply(important)
        for _, r in d.head(10).iterrows():
            t = str(r.get("tickers", "")).split(",")[0].strip()
            th = r["thesis"]
            im = r["importance"]
            st.markdown(f'<div class="row"><div class="sym">{link(t)}</div><div class="sector">{esc(sector(t))}</div><div>{tag(th, "bullish" if th=="Bullish" else "bearish" if th=="Bearish" else "neutral")}</div><div>{tag(im, "notable" if im=="Notable" else "low")}</div><div class="headline">{esc(r.get("title", ""))}</div></div>', unsafe_allow_html=True)
    st.markdown(endbox(), unsafe_allow_html=True)

def render_list(title, df, kind):
    st.markdown(box(title), unsafe_allow_html=True)
    if df.empty:
        st.markdown('<div class="subtle">No names matched right now.</div>', unsafe_allow_html=True)
    else:
        if kind=="watchlist":
            for _, r in df.head(8).iterrows():
                st.markdown(f'<div class="play"><div class="play-top"><div class="play-title">{link(r["ticker"])}</div><div>{tag("ENTRY SETUP", "bullish")}</div></div><div class="play-sub">{esc(r["sector"])} | score {int(r["score"])} | {esc(r["title"][:110])}</div></div>', unsafe_allow_html=True)
        elif kind=="movers":
            for _, r in df.head(8).iterrows():
                cls = "bullish" if r["chg"]>=0 else "bearish"
                st.markdown(f'<div class="row"><div class="sym">{link(r["symbol"])}</div><div class="sector">{esc(r["sector"])}</div><div>{tag(f"{r["chg"]:+.2f}%", cls)}</div><div>{tag("PRE", "neutral")}</div><div class="headline">premarket move >= 2%</div></div>', unsafe_allow_html=True)
        elif kind=="gappers":
            for _, r in df.head(8).iterrows():
                cls = "bullish" if r["gap"]>=0 else "bearish"
                st.markdown(f'<div class="row"><div class="sym">{link(r["symbol"])}</div><div class="sector">{esc(r["sector"])}</div><div>{tag(f"{r["gap"]:+.2f}%", cls)}</div><div>{tag("GAP", "notable")}</div><div class="headline">open vs prior close</div></div>', unsafe_allow_html=True)
        elif kind=="volume":
            for _, r in df.iterrows():
                st.markdown(f'<div class="row"><div class="sym">{link(r["symbol"])}</div><div class="sector">{esc(r["sector"])}</div><div>{tag("VOL", "notable")}</div><div>{tag("SCAN", "neutral")}</div><div class="headline">{format(int(r["vol"]), ",")} shares</div></div>', unsafe_allow_html=True)
    st.markdown(endbox(), unsafe_allow_html=True)

cal_df = calendar()
news_df = pd.concat([d for d in [news_marketaux(), news_alpha()] if not d.empty], ignore_index=True) if True else pd.DataFrame()
cand = candidates(news_df)
mov = movers()
gap = gappers()
vol = volscan()

st.markdown(box("Market overview"), unsafe_allow_html=True)
st.markdown('<div class="subtle">Dynamic scans refresh from the connected APIs.</div>', unsafe_allow_html=True)
st.markdown(endbox(), unsafe_allow_html=True)

left, right = st.columns([1.45, 1], gap="large")
with left:
    render_calendar(cal_df)
    render_news(news_df, "Catalyst headlines")
    render_list("Watchlist", cand, "watchlist")
    render_list("Analyst actions", cand[cand["title"].str.contains("upgrade|downgrade", case=False, na=False)] if not cand.empty else cand, "watchlist")
with right:
    render_list("Premarket movers +/- 2%", mov, "movers")
    render_list("Daily gappers", gap, "gappers")
    render_list("Unusual volume", vol, "volume")

c1, c2 = st.columns(2, gap="large")
with c1:
    render_list("Catalyst focus", cand, "watchlist")
with c2:
    render_list("Entry setup", cand, "watchlist")
'''
Path('output/App.py').write_text(code)
print('slim version written')
