import os
import re
import html
import requests
import streamlit as st
import yfinance as yf
from datetime import datetime, timezone

st.set_page_config(page_title="Multi-Ticker Scanner", layout="wide", initial_sidebar_state="collapsed")

FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", os.getenv("FINNHUB_API_KEY", ""))
MARKETAUX_API_KEY = st.secrets.get("MARKETAUX_API_KEY", os.getenv("MARKETAUX_API_KEY", ""))
RSS_URL = st.secrets.get("RSS_URL", os.getenv("RSS_URL", ""))
TICKERS = st.secrets.get("TICKERS", os.getenv("TICKERS", "AAPL,MSFT,NVDA,AMD,META,AMZN,GOOGL,TSLA")).split(",")
TICKERS = [t.strip().upper() for t in TICKERS if t.strip()]

st.markdown("""
<style>
.stApp { background: #040704; color: #d7f5d4; }
.scanner-wrap { max-width: 1400px; margin: 0 auto; }
.title { font-family: monospace; color: #7CFF7C; font-size: 34px; letter-spacing: 2px; margin-bottom: 0; }
.subtitle { color: #7fd47f; font-size: 12px; margin-top: -6px; margin-bottom: 18px; }
.chip { display:inline-block; border:1px solid rgba(124,255,124,.25); color:#9df79d; padding:4px 10px; border-radius:999px; margin-right:6px; font-size:11px; background: rgba(10,25,10,.7); }
.card { background: linear-gradient(180deg, rgba(6,30,10,.98), rgba(3,12,6,.98)); border:1px solid rgba(124,255,124,.14); border-radius:14px; padding:14px 16px; margin: 12px 0; box-shadow: 0 0 0 1px rgba(0,0,0,.2), 0 14px 40px rgba(0,0,0,.35); }
.ticker { color:#8bff8b; font-size: 22px; font-weight:700; letter-spacing:.5px; }
.company { color:#a8d9a8; font-size: 12px; margin-top: 2px; }
.score { text-align:right; font-size:28px; font-weight:800; }
.score-label { text-align:right; color:#92c992; font-size:11px; }
.tag { display:inline-block; padding:3px 8px; margin: 2px 5px 2px 0; border-radius: 999px; font-size: 11px; border:1px solid rgba(124,255,124,.18); background: rgba(6,20,8,.85); color:#c2efc2; }
.tag.green { color:#8cff8c; border-color: rgba(124,255,124,.25); }
.tag.red { color:#ff8d8d; border-color: rgba(255,120,120,.25); }
.tag.amber { color:#ffd27a; border-color: rgba(255,210,122,.25); }
.headline { color:#e6ffe6; font-size: 13px; line-height: 1.35; margin-top: 6px; }
.source { color:#76b876; font-size: 11px; margin-top: 6px; }
a { color:#8cff8c !important; }
.small { color:#89b989; font-size: 11px; }
</style>
""", unsafe_allow_html=True)


def clean_text(x):
    return re.sub(r"\s+", " ", html.unescape(str(x or ""))).strip()


def badge(text, tone):
    return f'<span class="tag {tone}">{clean_text(text)}</span>'


@st.cache_data(ttl=30)
def fetch_live_quotes(tickers):
    rows = []
    meta = []
    for t in tickers:
        try:
            if FINNHUB_API_KEY:
                r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={t}&token={FINNHUB_API_KEY}", timeout=15)
                js = r.json() if r.content else {}
                price = js.get("c")
                prev = js.get("pc")
                chg = None if price is None or prev is None else price - prev
                pct = None if price is None or prev in (None, 0) else (chg / prev) * 100
                if price not in (None, 0):
                    rows.append({"ticker": t, "price": price, "change": chg, "pct": pct, "source": f"Finnhub {r.status_code}"})
                    meta.append(f"{t}: finnhub {r.status_code}")
                    continue
            hist = yf.Ticker(t).history(period="1d", interval="1m")
            if not hist.empty:
                last = hist.iloc[-1]
                price = float(last["Close"])
                prev = float(hist.iloc[0]["Open"]) if "Open" in hist.columns else float(last["Close"])
                chg = price - prev
                pct = (chg / prev) * 100 if prev else 0
                rows.append({"ticker": t, "price": price, "change": chg, "pct": pct, "source": "yfinance"})
                meta.append(f"{t}: yfinance")
            else:
                rows.append({"ticker": t, "price": None, "change": None, "pct": None, "source": "no data"})
                meta.append(f"{t}: no data")
        except Exception as e:
            rows.append({"ticker": t, "price": None, "change": None, "pct": None, "source": f"error {type(e).__name__}"})
            meta.append(f"{t}: error")
    return rows, meta


@st.cache_data(ttl=180)
def fetch_marketaux_news(limit=8):
    token = MARKETAUX_API_KEY
    if not token:
        return [], "missing MARKETAUX_API_KEY"
    url = f"https://api.marketaux.com/v1/news/all?language=en&filter_entities=true&limit={limit}&api_token={token}"
    r = requests.get(url, timeout=20)
    js = r.json() if r.content else {}
    data = js.get("data", []) if isinstance(js, dict) else []
    items = []
    for x in data[:limit]:
        items.append({"headline": x.get("title") or x.get("headline") or "", "link": x.get("url") or x.get("link") or "", "source": (x.get("source") or {}).get("name") if isinstance(x.get("source"), dict) else x.get("source") or "Marketaux"})
    return items, f"status={r.status_code} items={len(items)}"


@st.cache_data(ttl=300)
def fetch_rss(url):
    if not url:
        return [], "missing RSS_URL"
    try:
        import feedparser
        feed = feedparser.parse(url)
        items = []
        for e in feed.entries[:8]:
            items.append({"headline": getattr(e, "title", ""), "link": getattr(e, "link", ""), "source": getattr(getattr(e, "source", None), "title", "RSS")})
        return items, f"status=ok items={len(items)}"
    except Exception as e:
        return [], f"error={type(e).__name__}: {e}"


def render_card(ticker, company, score, action, rating, pt, tags, headline, link, source, price=None, change=None, pct=None):
    color = "#7cff7c" if score >= 60 else "#ffd27a" if score >= 35 else "#ff8a8a"
    tag_html = "".join([badge(t, c) for t, c in tags])
    link_html = f'<a href="{html.escape(link)}" target="_blank">{html.escape(link)}</a>' if link else ""
    price_line = "—" if price is None else f"${price:,.2f}"
    chg_line = "—" if change is None else f"{change:+.2f} ({pct:+.2f}%)"
    st.markdown(f"""
<div class="card">
  <div style="display:flex; gap:16px; align-items:flex-start; justify-content:space-between;">
    <div style="flex:1 1 auto; min-width:0;">
      <div class="ticker">{clean_text(ticker)} <span class="small">{price_line} | {chg_line}</span></div>
      <div class="company">{clean_text(company)}</div>
      <div style="margin-top:8px;">{tag_html}</div>
      <div class="headline">{clean_text(headline)}</div>
      <div class="source">{clean_text(source)} {link_html}</div>
    </div>
    <div style="min-width:120px;">
      <div class="score" style="color:{color};">+{score}</div>
      <div class="score-label">{clean_text(action)} | {clean_text(rating)}</div>
      <div class="score-label">PT {clean_text(pt)}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)


st.markdown('<div class="scanner-wrap">', unsafe_allow_html=True)
st.markdown('<div class="title">MULTI-TICKER SCANNER</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Live stock prices first, news and RSS second</div>', unsafe_allow_html=True)
st.markdown("".join([f'<span class="chip">{c}</span>' for c in ["PIVOT", "2–5 day", "S&P 500", "High conviction"]]), unsafe_allow_html=True)

quotes, quote_meta = fetch_live_quotes(TICKERS)
news, news_meta = fetch_marketaux_news()
rss_items, rss_meta = fetch_rss(RSS_URL)

st.caption(f"Quotes: {' | '.join(quote_meta)}")
st.caption(f"Catalyst: {news_meta} | RSS: {rss_meta}")

st.markdown(f'<div style="margin-top:14px; color:#78d878; font-family: monospace; font-size:14px;">LIVE QUOTES ({len(quotes)})</div>', unsafe_allow_html=True)
for i, q in enumerate(quotes):
    score = 100 - i * 3 if q["price"] is not None else 0
    tags = [("LIVE", "green"), (q["source"], "amber")]
    render_card(q["ticker"], "Live stock quote", score, "MARKET", "QUOTE", "—", tags, "Real-time price stream", "", f"Quote source: {q['source']}", q["price"], q["change"], q["pct"])

st.markdown('<div style="margin-top:18px; color:#78d878; font-family: monospace; font-size:14px;">ANALYST / CATALYST</div>', unsafe_allow_html=True)
if news:
    for i, x in enumerate(news):
        render_card("NEWS", x.get("source", "Marketaux"), 80 - i * 6, "LIVE", "N/A", "—", [("LIVE", "green"), (x["source"] or "NEWS", "amber")], x["headline"], x["link"], x["source"])
elif rss_items:
    for i, x in enumerate(rss_items):
        render_card("RSS", x.get("source", "RSS"), 70 - i * 5, "LIVE", "N/A", "—", [("RSS", "amber"), ("FALLBACK", "green")], x["headline"], x["link"], x["source"])
else:
    render_card("—", "Live catalyst feed unavailable", 0, "NEUTRAL", "Options play: —", "—", [("NO FEED", "red")], "Connect a news API or RSS source.", "https://www.marketaux.com/", "Catalyst feed")

st.markdown('</div>', unsafe_allow_html=True)
