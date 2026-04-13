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

CSS = """
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
"""

st.markdown(CSS, unsafe_allow_html=True)
now_txt = datetime.now(PST).strftime("%b %-d, %-I:%M %p PST")
st.markdown(f"""<div class="topbar"><div><div class="brand">MARKET BRIEF</div><div class="subtle">Economic calendar | catalysts | analyst actions | play scan</div></div><div style="text-align:right;"><div class="subtle">Last updated</div><div style="font-weight:800;">{now_txt}</div></div></div>""", unsafe_allow_html=True)


def fetch_marketaux(symbols):
    if not MARKETAUX_KEY:
        return []
    url = "https://api.marketaux.com/v1/news/all"
    params = {
        "api_token": MARKETAUX_KEY,
        "symbols": ",".join(symbols),
        "filter_entities": "true",
        "language": "en",
        "limit": 10,
    }
    r = requests.get(url, params=params, timeout=15)
    data = r.json().get("data", []) if r.ok else []
    items = []
        for a in data:
        items.append({
            "symbol": (a.get("entities") or [{}])[0].get("symbol", symbols[0]),
            "source": (a.get("source") or {}).get("name", "Marketaux"),
            "thesis": thesis_from_text((a.get("title") or "") + " " + (a.get("description") or "")),
            "type": "News",
            "headline": a.get("title") or a.get("description") or "Market news",
        })
    return items

def fetch_forex_factory_calendar():
    url = "https://www.forexfactory.com/calendar?week=apr5.2026"
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        txt = r.text
    except Exception:
        txt = ""
    items = []
    if txt:
        lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
        for ln in lines:
            if "USD" in ln and ("CPI" in ln or "PPI" in ln or "Fed" in ln or "NFP" in ln or "Job" in ln or "Claims" in ln):
                items.append({
                    "symbol": "USD",
                    "source": "Forex Factory",
                    "thesis": "Neutral",
                    "type": "Calendar",
                    "headline": ln[:120],
                })
    if items:
        return items[:8]
    return [
        {"symbol":"USD","source":"Forex Factory","thesis":"Neutral","type":"Calendar","headline":"US economic calendar for the selected week"},
        {"symbol":"USD","source":"Forex Factory","thesis":"Neutral","type":"Calendar","headline":"High-impact US releases filtered from the calendar"},
    ]

def fetch_alpha_earnings(symbols):
    if not ALPHAVANTAGE_KEY:
        return []
    items = []
    for sym in symbols[:6]:
        url = "https://www.alphavantage.co/query"
        params = {"function": "EARNINGS_CALENDAR", "horizon": "3month", "symbol": sym, "apikey": ALPHAVANTAGE_KEY}
        r = requests.get(url, params=params, timeout=20)
        if r.ok and r.text.strip():
            items.append({
                "symbol": sym,
                "source": "Alpha Vantage",
                "thesis": "Neutral",
                "type": "Earnings",
                "headline": f"Earnings calendar data available for {sym}",
            })
    return items
def safe_cell(v):
    s = "" if v is None else str(v)
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

def sym_html(ticker):
    t = str(ticker).strip()
    return f'<a class="yf" href="https://finance.yahoo.com/quote/{t}" target="_blank" rel="noopener noreferrer">{safe_cell(t)}</a>' if t else ""

def badge(text, cls="neutral"):
    return f'<span class="badge {cls}">{safe_cell(text)}</span>'

def sector_guess(sym):
    mapping = {"AAPL":"Technology","MSFT":"Technology","NVDA":"Semiconductors","AMD":"Semiconductors","TSLA":"Consumer Discretionary","AMZN":"Consumer Discretionary","JPM":"Financials","LLY":"Healthcare","XOM":"Energy","ORCL":"Technology","CRM":"Technology","BA":"Industrials"}
    return mapping.get(sym, "Large Cap")

def thesis_from_text(text):
    t = (text or "").lower()
    if any(k in t for k in ["beat", "raises", "upgrade", "buy", "approval", "approved", "strong", "surge", "outperform"]): return "Bullish"
    if any(k in t for k in ["miss", "cuts", "downgrade", "sell", "probe", "lawsuit", "weak", "slump", "recall"]): return "Bearish"
    return "Neutral"

def card(title): return f'<div class="card"><div class="card-h"><div class="card-t">{safe_cell(title)}</div><div class="subtle">Live scan</div></div><div class="card-b">'
def endcard(): return '</div></div>'

def render_news(items, title):
    st.markdown(card(title), unsafe_allow_html=True)
    for item in items:
        st.markdown(f'<div class="row"><div class="sym">{sym_html(item["symbol"])}</div><div class="sector">{safe_cell(item["source"])}</div><div>{badge(item["thesis"], "bullish" if item["thesis"]=="Bullish" else ("bearish" if item["thesis"]=="Bearish" else "neutral"))}</div><div>{badge(item["type"], "notable")}</div><div class="headline">{safe_cell(item["headline"])}</div></div>', unsafe_allow_html=True)
    st.markdown(endcard(), unsafe_allow_html=True)

universe_df = pd.DataFrame({"symbol":["NVDA","AAPL","MSFT","TSLA","AMZN","JPM","LLY","XOM","ORCL","CRM","AMD","BA"],"sector":[sector_guess(s) for s in ["NVDA","AAPL","MSFT","TSLA","AMZN","JPM","LLY","XOM","ORCL","CRM","AMD","BA"]]})
calendar_df = pd.DataFrame(fetch_forex_factory_calendar())
combined_news = fetch_marketaux(["NVDA","AAPL","MSFT","TSLA","AMZN","LLY"]) or [
    {"symbol":"NVDA","source":"Earnings","thesis":thesis_from_text("strong guidance"),"type":"Catalyst","headline":"AI demand and guidance remain the key driver."},
    {"symbol":"LLY","source":"Health","thesis":thesis_from_text("approval"),"type":"Catalyst","headline":"Pipeline and approval headlines keep it on watch."},
    {"symbol":"AAPL","source":"Product","thesis":thesis_from_text("upgrade"),"type":"Analyst","headline":"Rating and product cycle comments can move the stock."},
    {"symbol":"TSLA","source":"Autos","thesis":thesis_from_text("weak"),"type":"Volatility","headline":"Delivery and margin chatter can create swings."},
]

def render_calendar(df):
    st.markdown(card("Economic calendar"), unsafe_allow_html=True)
    for _, r in df.iterrows():
        st.markdown(f'<div class="row"><div class="sym">{safe_cell(r["symbol"])}</div><div class="sector">{safe_cell(r["source"])}</div><div>{badge(r["thesis"], "neutral")}</div><div>{badge(r["type"], "low")}</div><div class="headline">{safe_cell(r["headline"])}</div></div>', unsafe_allow_html=True)
    st.markdown(endcard(), unsafe_allow_html=True)

def render_opportunity_panel(title, symbols, style, note):
    st.markdown(card(title), unsafe_allow_html=True)
    for sym in symbols:
        st.markdown(f'<div class="play"><div class="play-top"><div class="play-title">{sym_html(sym)}</div><div>{badge(style, "bullish" if style == "Catalyst" else "notable" if style == "Setup" else "neutral")}</div></div><div class="play-sub">{safe_cell(sector_guess(sym))} | {safe_cell(note)}</div></div>', unsafe_allow_html=True)
    st.markdown(endcard(), unsafe_allow_html=True)

left, right = st.columns([1.5, 1], gap="large")
with left:
    render_calendar(calendar_df)
    render_news(combined_news + fetch_alpha_earnings(["AAPL","MSFT","NVDA","TSLA","AMZN","LLY"]), "Catalyst headlines")
    st.markdown(card("Analyst actions"), unsafe_allow_html=True)
    for sym in ["AAPL","MSFT","NVDA","AMZN","TSLA","JPM","LLY","XOM"]:
        st.markdown(f'<div class="row"><div class="sym">{sym_html(sym)}</div><div class="sector">{safe_cell(sector_guess(sym))}</div><div>{badge("RATING", "neutral")}</div><div>{badge("WATCH", "low")}</div><div class="headline">{safe_cell(sym)} upgrade/downgrade watch</div></div>', unsafe_allow_html=True)
    st.markdown(endcard(), unsafe_allow_html=True)
with right:
    render_opportunity_panel("Potential plays", ["NVDA","LLY","AMD","ORCL","CRM","BA"], "Setup", "catalyst + analyst interest")
    st.markdown('<div class="hr"></div>', unsafe_allow_html=True)
    st.markdown(card("Watchlist"), unsafe_allow_html=True)
    for _, r in universe_df.head(8).iterrows():
        st.markdown(f'<div class="row"><div class="sym">{sym_html(r["symbol"])}</div><div class="sector">{safe_cell(r["sector"])}</div><div>{badge("WATCH", "neutral")}</div><div>{badge("LOW", "low")}</div><div class="headline">liquid large-cap name</div></div>', unsafe_allow_html=True)
    st.markdown(endcard(), unsafe_allow_html=True)

col1, col2 = st.columns(2, gap="large")
with col1:
    render_opportunity_panel("Catalyst focus", ["NVDA","AAPL","LLY","AMD"], "Catalyst", "earnings, guidance, news")
with col2:
    render_opportunity_panel("Rating focus", ["MSFT","ORCL","CRM","JPM"], "Rating", "upgrade / downgrade cluster")

st.markdown('<div class="subtle" style="margin-top:10px;">Yahoo links are clickable. Sectors are heuristic because this version does not use a sector API.</div>', unsafe_allow_html=True)
