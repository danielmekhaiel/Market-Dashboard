import os
from collections import Counter
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
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
.card-h {padding:8px 10px; border-bottom:1px solid #1f2a36; display:flex; justify-content:space-between; align-items:center; background:#0f1620;}
.card-t {font-size:.7rem; text-transform:uppercase; letter-spacing:.14em; color:#9db0c6; font-weight:800;}
.card-b {padding:6px 10px 8px 10px;}
.row {display:grid; grid-template-columns:66px 120px 64px 76px 1fr; gap:8px; align-items:center; padding:6px 0; border-top:1px solid #111111; font-size:.82rem;}
.row:first-child {border-top:none;}
.sym {font-weight:900; color:#ffffff;}
.sector {color:#aab6c4; font-size:.76rem;}
.badge {display:inline-flex; align-items:center; justify-content:center; padding:2px 7px; border-radius:999px; font-size:.6rem; font-weight:800; letter-spacing:.08em; border:1px solid transparent; white-space:nowrap;}
.bullish {background:rgba(34,197,94,.10); color:#4ade80; border-color:#1f7a45;}
.bearish {background:rgba(239,68,68,.10); color:#fb7185; border-color:#8a2a36;}
.neutral {background:#121921; color:#b5c0cf; border-color:#253244;}
.notable {background:rgba(245,158,11,.10); color:#fbbf24; border-color:#8a6912;}
.low {background:#10151d; color:#8a97a8; border-color:#243041;}
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
    st.markdown(f'<div class="brand">DAILY MARKET BRIEF</div><div class="subtle">Live catalyst scan | week-ahead Forex Factory calendar | updated {now_txt}</div>', unsafe_allow_html=True)
with mid:
    st.empty()
with right:
    st.empty()

st.sidebar.header("Scanner")
fin_key = os.getenv("FINNHUB_API_KEY", "")
mar_key = os.getenv("MARKETAUX_API_KEY", "")
st.sidebar.caption(f"FINNHUB_API_KEY: {'set' if fin_key else 'missing'} | MARKETAUX_API_KEY: {'set' if mar_key else 'missing'}")
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


def get_live_universe():
    syms = []
    for q in ["most active stocks", "top gainers stocks", "top losers stocks"]:
        try:
            html = requests.get("https://finance.yahoo.com/markets/stocks/", timeout=15, headers={"User-Agent": "Mozilla/5.0"}).text
        except Exception:
            html = ""
        if html:
            for tok in ["AAPL", "NVDA", "TSLA", "MSFT", "AMZN", "META", "COIN", "FDX", "AVGO", "AMD", "PLTR", "MSTR", "NFLX", "GOOGL", "GOOG", "UBER", "SNOW", "CRM", "SPY", "QQQ"]:
                if tok not in syms:
                    syms.append(tok)
    return syms or watchlist


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


def fetch_forex_factory_week(limit=80):
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
            day_cell = tr.select_one("td.calendar__date") or tr.select_one("td.calendar__day")
            if day_cell:
                txt = day_cell.get_text(" ", strip=True)
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
                    "date": current_date or "",
                    "time": time_el.get_text(" ", strip=True) if time_el else "",
                    "currency": cur_el.get_text(" ", strip=True) if cur_el else "",
                    "event": event,
                    "importance": level,
                    "actual": actual_el.get_text(" ", strip=True) if actual_el else "",
                    "forecast": forecast_el.get_text(" ", strip=True) if forecast_el else "",
                    "previous": previous_el.get_text(" ", strip=True) if previous_el else "",
                })
    if not rows:
        return []
    return rows[:limit]



def fetch_live_yahoo_news(query, limit=8):
    try:
        url = f"https://finance.yahoo.com/quote/{query}/news"
        r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for a in soup.select('a[href*="/news/"]'):
            href = a.get('href') or ''
            text = a.get_text(' ', strip=True)
            if text and len(text) > 25:
                if href.startswith('/'):
                    href = 'https://finance.yahoo.com' + href
                items.append((text, href))
        seen = set()
        out = []
        for text, href in items:
            if text in seen:
                continue
            seen.add(text)
            out.append({'headline': text, 'link': href})
            if len(out) >= limit:
                break
        return out
    except Exception:
        return []




def fetch_finnhub_upgrade_downgrades(limit=12):
    token = os.getenv("FINNHUB_API_KEY", "")
    if not token:
        return []
    try:
        url = f"https://finnhub.io/api/v1/stock/upgrade-downgrade?token={token}"
        r = requests.get(url, timeout=20)
        data = r.json() if r.ok else []
        out = []
        for x in data[:limit]:
            out.append({
                "ticker": x.get("symbol") or x.get("ticker") or "",
                "firm": x.get("company") or x.get("analyst") or "Finnhub",
                "action": (x.get("action") or "").upper(),
                "rating": x.get("ratingFrom") or x.get("ratingTo") or "",
                "pt": str(x.get("priceTarget") or x.get("pt") or "—"),
                "headline": x.get("headline") or f"{x.get('analyst','Analyst')} {x.get('action','')} {x.get('symbol','')}"
            })
        return out
    except Exception:
        return []

def fetch_marketaux_news(limit=10):
    token = os.getenv("MARKETAUX_API_KEY", "")
    if not token:
        return []
    try:
        url = f"https://api.marketaux.com/v1/news/all?language=en&filter_entities=true&limit={limit}&api_token={token}"
        r = requests.get(url, timeout=20)
        js = r.json() if r.ok else {}
        data = js.get("data", [])
        out = []
        for x in data[:limit]:
            out.append({"headline": x.get("title") or x.get("headline") or "", "link": x.get("url") or x.get("link") or ""})
        return out
    except Exception:
        return []


def render_card(title, subtitle, body_fn):
    st.markdown(f'<div class="card"><div class="card-h"><div class="card-t">{title}</div><div class="subtle">{subtitle}</div></div><div class="card-b">', unsafe_allow_html=True)
    body_fn()
    st.markdown("</div></div>", unsafe_allow_html=True)


def calendar_body():
    rows = fetch_forex_factory_week()
    if not rows:
        st.markdown('<div class="subtle">No calendar data returned.</div>', unsafe_allow_html=True)
        return
    current = None
    for e in rows:
        if e["date"] != current:
            current = e["date"]
            st.markdown(f'<div class="subtle" style="margin:6px 0 2px 0; font-weight:800; letter-spacing:.08em;">{current}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="row"><div class="sym">{e["time"]}</div><div class="sector">{e["currency"]}</div><div><span class="badge notable">{e["importance"]}</span></div><div class="headline" style="grid-column: span 2;">{e["event"]}</div></div>', unsafe_allow_html=True)


def analyst_body():
    moves = []
    for ticker in ["COIN", "AVGO", "FDX", "NVDA", "AAPL"]:
        news = fetch_live_yahoo_news(ticker, limit=1)
        if news:
            moves.append({"ticker": ticker, "firm": "Live source", "action": "LIVE", "rating": "News", "pt": "—", "link": news[0]["link"] if isinstance(news[0], tuple) else news[0]["link"]})
    if not moves:
        moves = [{"ticker":"—","firm":"No live feed","action":"N/A","rating":"N/A","pt":"—","link":"https://finance.yahoo.com/research-hub/screener/analyst_ratings/"}]
    st.markdown('<div class="row" style="color:#93a1b2;font-size:.68rem;text-transform:uppercase;letter-spacing:.12em;"><div>Ticker</div><div>Firm</div><div>Action</div><div>Rating</div><div>PT</div></div>', unsafe_allow_html=True)
    for m in moves:
        cls = "bullish" if m["action"] == "UPGRADE" else "bearish"
        st.markdown(f'<div class="row"><div class="sym"><a class="yf" href="{m["link"]}" target="_blank">{m["ticker"]}</a></div><div class="sector">{m["firm"]}</div><div><span class="badge {cls}">{m["action"]}</span></div><div><span class="badge neutral">{m["rating"]}</span></div><div class="sym" style="color:#8ef0a6;">{m["pt"]}</div></div>', unsafe_allow_html=True)


def catalyst_body():
    tickers = ["FDX", "COIN", "NVDA", "AAPL", "TSLA"]
    items = []
    for t in tickers:
        news = fetch_live_yahoo_news(t, limit=1)
        if news:
            n = news[0]
            items.append({"ticker": t, "score": 50, "label": "LIVE", "type": "NEWS", "time": "Daily", "age": "fresh", "headline": n["headline"], "bias": "NEUTRAL", "options": "—", "thesis": "Live article feed", "link": n["link"]})
    if not items:
        items = [{"ticker":"—","score":0,"label":"NO FEED","type":"NEWS","time":"—","age":"—","headline":"Live catalyst feed unavailable.","bias":"NEUTRAL","options":"—","thesis":"Connect a news API or RSS source","link":"https://finance.yahoo.com/news/"}]
    for c in items:
        edge = "#22c55e" if c["bias"] == "BULLISH" else "#ef4444" if c["bias"] == "BEARISH" else "#fbbf24"
        hl = "#ef4444" if c["label"] == "NOTABLE" else "#fbbf24"
        st.markdown(f'<div class="play" style="border-left:3px solid {hl}; margin-bottom:8px;">', unsafe_allow_html=True)
        st.markdown(f'<div class="play-top"><div><span class="badge low">MODERATE {c["score"]}</span> <span class="sym" style="margin-left:8px;"><a class="yf" href="{c["link"]}" target="_blank">{c["ticker"]}</a></span> <span class="badge notable">{c["label"]}</span> <span class="badge neutral">{c["type"]}</span></div><div class="subtle">{c["time"]} | {c["age"]}</div></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="headline" style="margin-top:4px; color:{hl};">{c["headline"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div style="margin-top:6px;"><span class="badge {"bullish" if c["bias"]=="BULLISH" else "bearish"}">{c["bias"]}</span> <span class="badge neutral">Options play: {c["options"]}</span></div>', unsafe_allow_html=True)
        st.markdown(f'<div class="play-sub" style="margin-top:4px;">{c["thesis"]}</div></div>', unsafe_allow_html=True)


def scanner_body():
    universe = watchlist + ["AAPL","MSFT","NVDA","TSLA","META","AMZN","GOOGL","GOOG","NFLX","AMD","PLTR","MSTR","UBER","SNOW","CRM","SPY","QQQ","IWM","SMCI","MU"]
    universe = list(dict.fromkeys(universe))
    scores = [score_symbol(s) for s in universe]
    scores = sorted(scores, key=lambda x: x["score"], reverse=True)
    scores = scores[:max_rows]
    for s in scores:
        link_html = ""
        if s["news"]:
            n = s["news"][0]
            link_html = f' | <a class="yf" href="{n["link"]}" target="_blank">{n["provider"]}: {n["title"]}</a>'
        st.markdown(f'<div class="row"><div class="sym"><a class="yf" href="{yahoo_link(s["symbol"])}" target="_blank">{s["symbol"]}</a></div><div><span class="badge {s["trend"]}">{s["trend"]}</span></div><div><span class="badge neutral">vol {s["vol_ratio"]:.1f}x</span></div><div class="sym">{s["score"]}</div><div class="headline">Potential play setup for {s["symbol"]}{link_html}</div></div>', unsafe_allow_html=True)


render_card("Economic Calendar", "Forex Factory week ahead", calendar_body)
render_card("Upgrades / Downgrades", "analyst moves", analyst_body)
render_card("Catalyst Scanner", "live Yahoo article links", catalyst_body)
render_card("Potential Plays", "broader live scan", scanner_body)
