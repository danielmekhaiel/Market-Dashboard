import os
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
import streamlit as st
import yfinance as yf
from bs4 import BeautifulSoup

PST = ZoneInfo("America/Los_Angeles")
st.set_page_config(page_title="Daily Market Brief", layout="wide")

CSS = """
<style>
.block-container {padding:0.5rem 0.8rem 0.8rem 0.8rem; max-width:1500px;}
html, body, [class*="css"] {background:#000000; color:#f2f4f8;}
header, footer, #MainMenu {visibility:hidden;}
[data-testid="stSidebar"] {background:#000000; border-right:1px solid #111111;}
.topbar {display:flex; justify-content:space-between; align-items:center; background:#000000; border:1px solid #111111; border-radius:12px; padding:10px 12px; margin-bottom:10px;}
.brand {font-size:1.05rem; font-weight:800; letter-spacing:.12em;}
.subtle {color:#93a1b2; font-size:.76rem;}
.card {background:#000000; border:1px solid #111111; border-radius:12px; overflow:hidden; margin-bottom:10px;}
.card-h {padding:8px 10px; border-bottom:1px solid #111111; display:flex; justify-content:space-between; align-items:center; background:#000000;}
.card-t {font-size:.7rem; text-transform:uppercase; letter-spacing:.14em; color:#9db0c6; font-weight:800;}
.card-b {padding:6px 10px 8px 10px;}
.row {display:grid; grid-template-columns:66px 120px 64px 76px 1fr; gap:8px; align-items:center; padding:6px 0; border-top:1px solid #111111; font-size:.82rem;}
.row:first-child {border-top:none;}
.sym {font-weight:900; color:#ffffff;}
.sector {color:#aab6c4; font-size:.76rem;}
.badge {display:inline-flex; align-items:center; justify-content:center; padding:2px 7px; border-radius:999px; font-size:.6rem; font-weight:800; letter-spacing:.08em; border:1px solid transparent; white-space:nowrap;}
.bullish {background:rgba(34,197,94,.10); color:#4ade80; border-color:#1f7a45;}
.bearish {background:rgba(239,68,68,.10); color:#fb7185; border-color:#8a2a36;}
.neutral {background:#121212; color:#b5c0cf; border-color:#253244;}
.notable {background:rgba(245,158,11,.10); color:#fbbf24; border-color:#8a6912;}
.low {background:#101010; color:#8a97a8; border-color:#243041;}
.headline {color:#ecf1f7; font-size:.8rem; line-height:1.2;}
.play {display:flex; flex-direction:column; gap:2px; padding:8px 0; border-top:1px solid #111111; border-left:3px solid transparent; padding-left:9px;}
.play:first-child {border-top:none;}
.play-top {display:flex; justify-content:space-between; align-items:center; gap:8px;}
.play-sub {font-size:.74rem; color:#aab6c4;}
a.yf {color:#fff; text-decoration:none; font-weight:900;}
</style>
"""

st.markdown(CSS, unsafe_allow_html=True)
now_txt = datetime.now(PST).strftime("%b %-d, %-I:%M %p PST")
left, mid, right = st.columns([3,1,1])
with left:
    st.markdown(f'<div class="brand">DAILY MARKET BRIEF</div>', unsafe_allow_html=True)
with mid:
    st.empty()
with right:
    st.empty()

st.sidebar.header("Scanner")
watchlist_text = st.sidebar.text_input("Watchlist", "AAPL,MSFT,NVDA,TSLA,COIN,FDX,AVGO,AMZN")
watchlist = [s.strip().upper() for s in watchlist_text.split(",") if s.strip()]
max_rows = st.sidebar.slider("Top results", 10, 100, 30, 5)


def thesis_from_text(text):
    t = (text or "").lower()
    if any(k in t for k in ["beat", "raised", "upgrade", "bull", "growth", "strong", "record", "win", "surge", "momentum"]):
        return "bullish"
    if any(k in t for k in ["miss", "cut", "downgrade", "bear", "weak", "lawsuit", "probe", "slump", "fall", "drop"]):
        return "bearish"
    return "neutral"


def yahoo_link(symbol):
    return f"https://finance.yahoo.com/quote/{symbol}/news"


def fetch_live_stock(symbol):
    try:
        t = yf.Ticker(symbol)
        hist = t.history(period="1d", interval="5m", auto_adjust=False)
        info = getattr(t, "fast_info", {}) or {}
        last = hist.iloc[-1] if not hist.empty else None
        prev = hist.iloc[-2] if len(hist) > 1 else None
        price = float(last["Close"]) if last is not None else float(info.get("lastPrice") or 0)
        vol = float(last["Volume"]) if last is not None else 0
        avg_vol = float(hist["Volume"].tail(20).mean()) if not hist.empty and "Volume" in hist else 0
        chg = ((price - float(prev["Close"])) / float(prev["Close"])) * 100 if prev is not None and float(prev["Close"]) else 0
        return {"symbol": symbol, "chg": chg, "vol": vol, "avg_vol": avg_vol, "price": price}
    except Exception:
        return {"symbol": symbol, "chg": 0, "vol": 0, "avg_vol": 0, "price": 0}


def fetch_yahoo_news(symbol, limit=3):
    try:
        items = getattr(yf.Ticker(symbol), "news", []) or []
    except Exception:
        items = []
    out = []
    for a in items[:limit]:
        title = a.get("content", {}).get("title") or a.get("title") or "Yahoo news"
        link = a.get("content", {}).get("canonicalUrl", {}).get("url") or a.get("link") or yahoo_link(symbol)
        provider = a.get("content", {}).get("provider", {}).get("displayName") or a.get("publisher") or "Yahoo"
        out.append({"title": title, "link": link, "provider": provider, "thesis": thesis_from_text(title)})
    return out


def score_symbol(symbol):
    d = fetch_live_stock(symbol)
    news = fetch_yahoo_news(symbol, 3)
    vol_ratio = d["vol"] / d["avg_vol"] if d["avg_vol"] else 0
    text = " ".join(n["title"] for n in news)
    tone = thesis_from_text(text)
    score = 0
    score += min(max(d["chg"] * 4, -20), 20)
    score += min(vol_ratio * 10, 25)
    score += 8 if tone == "bullish" else -8 if tone == "bearish" else 0
    score += min(len(news) * 2, 6)
    return {**d, "news": news, "vol_ratio": vol_ratio, "tone": tone, "score": round(score, 1), "trend": "bullish" if score > 12 else "bearish" if score < -5 else "neutral"}


def fetch_forex_factory_week(limit=40):
    urls = ["https://www.forexfactory.com/calendar?week=this", "https://www.forexfactory.com/calendar"]
    html = ""
    for url in urls:
        try:
            html = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"}).text
            if html:
                break
        except Exception:
            pass
    rows = []
    if html:
        soup = BeautifulSoup(html, "html.parser")
        current_date = None
        for tr in soup.select("tr.calendar__row"):
            classes = tr.get("class", [])
            if any(c.startswith("calendar__row--day") for c in classes):
                day_text = tr.get_text(" ", strip=True)
                if day_text:
                    current_date = day_text
                continue
            date_cell = tr.select_one("td.calendar__date") or tr.select_one("td.calendar__day")
            if date_cell:
                txt = date_cell.get_text(" ", strip=True)
                if txt:
                    current_date = txt
            time_el = tr.select_one("td.calendar__time")
            cur_el = tr.select_one("td.calendar__currency")
            impact_el = tr.select_one("span.calendar__impact")
            event_el = tr.select_one("td.calendar__event")
            actual_el = tr.select_one("td.calendar__actual")
            forecast_el = tr.select_one("td.calendar__forecast")
            previous_el = tr.select_one("td.calendar__previous")
            title = impact_el.get("title", "") if impact_el else ""
            level = "HIGH" if "High" in title else "MED" if "Medium" in title else "LOW"
            event = event_el.get_text(" ", strip=True) if event_el else ""
            if event:
                rows.append({
                    "date": current_date or "Today",
                    "time": time_el.get_text(" ", strip=True) if time_el else "",
                    "currency": cur_el.get_text(" ", strip=True) if cur_el else "",
                    "event": event,
                    "importance": level,
                    "actual": actual_el.get_text(" ", strip=True) if actual_el else "",
                    "forecast": forecast_el.get_text(" ", strip=True) if forecast_el else "",
                    "previous": previous_el.get_text(" ", strip=True) if previous_el else "",
                })
    if not rows:
        rows = [
            {"date":"Mon Apr 13","time":"2:00 PM","currency":"USD","event":"FOMC Meeting Minutes","importance":"HIGH","actual":"","forecast":"","previous":""},
            {"date":"Tue Apr 14","time":"8:30 AM","currency":"USD","event":"Initial Jobless Claims","importance":"HIGH","actual":"","forecast":"","previous":""},
            {"date":"Wed Apr 15","time":"10:00 AM","currency":"USD","event":"Consumer Sentiment","importance":"MED","actual":"","forecast":"","previous":""},
            {"date":"Thu Apr 16","time":"8:30 AM","currency":"USD","event":"Retail Sales","importance":"HIGH","actual":"","forecast":"","previous":""},
            {"date":"Fri Apr 17","time":"9:45 AM","currency":"USD","event":"PMI Flash","importance":"HIGH","actual":"","forecast":"","previous":""},
        ]
    return rows[:limit]


def render_card(title, subtitle, body_fn):
    st.markdown(f'<div class="card"><div class="card-h"><div class="card-t">{title}</div><div class="subtle">{subtitle}</div></div><div class="card-b">', unsafe_allow_html=True)
    body_fn()
    st.markdown("</div></div>", unsafe_allow_html=True)


def calendar_body():
    rows = fetch_forex_factory_week()
    for e in rows:
        st.markdown(f'<div class="row"><div class="sym">{e["date"]}</div><div class="sector">{e["time"]}</div><div><span class="badge notable">{e["importance"]}</span></div><div class="headline" style="grid-column: span 2;">{e["currency"]} · {e["event"]}</div></div>', unsafe_allow_html=True)


def analyst_body():
    moves = [{"ticker":"COIN","firm":"Barclays","action":"DOWNGRADE","rating":"Underweight","pt":"$140"},{"ticker":"AVGO","firm":"Seaport Global","action":"DOWNGRADE","rating":"Neutral","pt":"—"},{"ticker":"FDX","firm":"Wolfe","action":"UPGRADE","rating":"Outperform","pt":"$305"}]
    st.markdown('<div class="row" style="color:#93a1b2;font-size:.68rem;text-transform:uppercase;letter-spacing:.12em;"><div>Ticker</div><div>Firm</div><div>Action</div><div>Rating</div><div>PT</div></div>', unsafe_allow_html=True)
    for m in moves:
        cls = "bullish" if m["action"] == "UPGRADE" else "bearish"
        st.markdown(f'<div class="row"><div class="sym">{m["ticker"]}</div><div class="sector">{m["firm"]}</div><div><span class="badge {cls}">{m["action"]}</span></div><div><span class="badge neutral">{m["rating"]}</span></div><div class="sym" style="color:#8ef0a6;">{m["pt"]}</div></div>', unsafe_allow_html=True)


def catalyst_body():
    items = [
        {"ticker":"FDX","score":58,"label":"NOTABLE","type":"CONFERENCE","time":"8:23 AM","age":"28min ago","headline":"FedEx Freight holds investor day ahead of spin-off; sees medium-term revenue growth of 4% to 6% CAGR.","bias":"BULLISH","options":"CALLS","thesis":"Conference catalyst = potential guidance or announcement"},
        {"ticker":"COIN","score":55,"label":"NOTABLE","type":"PT CUT","time":"8:35 AM","age":"15min ago","headline":"Barclays downgrades Coinbase to Underweight, lowers price target to $140.","bias":"BEARISH","options":"PUTS","thesis":"PT cut or downgrade = bearish signal"},
        {"ticker":"NVDA","score":72,"label":"HIGH","type":"EARNINGS","time":"9:10 AM","age":"5min ago","headline":"Chip demand remains elevated into next quarter with margin support holding.","bias":"BULLISH","options":"CALLS","thesis":"Momentum and earnings narrative"},
    ]
    for c in items:
        hl = "#ef4444" if c["label"] == "NOTABLE" else "#fbbf24"
        st.markdown(f'<div class="play" style="border-left:3px solid {hl}; margin-bottom:8px;">', unsafe_allow_html=True)
        st.markdown(f'<div class="play-top"><div><span class="badge low">MODERATE {c["score"]}</span> <span class="sym" style="margin-left:8px;">{c["ticker"]}</span> <span class="badge notable">{c["label"]}</span> <span class="badge neutral">{c["type"]}</span></div><div class="subtle">{c["time"]} | {c["age"]}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="headline" style="margin-top:4px; color:{hl};">{c["headline"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="margin-top:6px;"><span class="badge {"bullish" if c["bias"]=="BULLISH" else "bearish"}">{c["bias"]}</span> <span class="badge neutral">Options play: {c["options"]}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="play-sub" style="margin-top:4px;">{c["thesis"]}</div></div>', unsafe_allow_html=True)


def scanner_body():
    universe = watchlist + ["AAPL","MSFT","NVDA","TSLA","META","AMZN","GOOGL","GOOG","NFLX","AMD","PLTR","MSTR","UBER","SNOW","CRM","SPY","QQQ","IWM","SMCI","MU"]
    universe = list(dict.fromkeys(universe))
    scores = [score_symbol(s) for s in universe]
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)[:max_rows]
    for s in scores:
        link_html = ""
        if s["news"]:
            n = s["news"][0]
            link_html = f' | <a class="yf" href="{n["link"]}" target="_blank">{n["provider"]}: {n["title"]}</a>'
        st.markdown(f'<div class="row"><div class="sym"><a class="yf" href="{yahoo_link(s["symbol"])}" target="_blank">{s["symbol"]}</a></div><div><span class="badge {s["trend"]}">{s["trend"]}</span></div><div><span class="badge neutral">vol {s["vol_ratio"]:.1f}x</span></div><div class="sym">{s["score"]}</div><div class="headline">Potential play setup for {s["symbol"]}{link_html}</div></div>', unsafe_allow_html=True)


render_card("Economic Calendar", "", calendar_body)
render_card("Upgrades / Downgrades", "", analyst_body)
render_card("Catalyst Scanner", "", catalyst_body)
render_card("Potential Plays", "", scanner_body)
