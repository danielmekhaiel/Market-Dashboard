import os
import re
import html
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(page_title="Multi-Ticker Scanner", layout="wide", initial_sidebar_state="collapsed")

FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", os.getenv("FINNHUB_API_KEY", ""))
MARKETAUX_API_KEY = st.secrets.get("MARKETAUX_API_KEY", os.getenv("MARKETAUX_API_KEY", ""))
RSS_URL = st.secrets.get("RSS_URL", os.getenv("RSS_URL", ""))

st.markdown("""
<style>
.stApp { background: #040704; color: #d7f5d4; }
.scanner-wrap { max-width: 1400px; margin: 0 auto; }
.title { font-family: monospace; color: #7CFF7C; font-size: 34px; letter-spacing: 2px; margin-bottom: 0; }
.subtitle { color: #7fd47f; font-size: 12px; margin-top: -6px; margin-bottom: 18px; }
.chip { display:inline-block; border:1px solid rgba(124,255,124,.25); color:#9df79d; padding:4px 10px; border-radius:999px; margin-right:6px; font-size:11px; background: rgba(10,25,10,.7); }
.card { background: #0a0a0a; border:1px solid rgba(255,255,255,.08); border-radius:8px; padding:4px 8px; margin: 3px 0; box-shadow: none; }
.ticker { color:#f0f0f0; font-size: 15px; font-weight:700; letter-spacing:.3px; }
.company { color:#a8d9a8; font-size: 12px; margin-top: 2px; }
.score { text-align:right; font-size:18px; font-weight:800; }
.score-label { text-align:right; color:#92c992; font-size:11px; }
.tag { display:inline-block; padding:3px 8px; margin: 2px 5px 2px 0; border-radius: 999px; font-size: 11px; border:1px solid rgba(124,255,124,.18); background: rgba(6,20,8,.85); color:#c2efc2; }
.tag.green { color:#8cff8c; border-color: rgba(124,255,124,.25); }
.tag.red { color:#ff8d8d; border-color: rgba(255,120,120,.25); }
.tag.amber { color:#ffd27a; border-color: rgba(255,210,122,.25); }
.headline { color:#e6ffe6; font-size: 12px; line-height: 1.2; margin-top: 2px; }
.source { color:#76b876; font-size: 11px; margin-top: 6px; }
a { color:#8cff8c !important; }
.small { color:#89b989; font-size: 11px; }
.section { margin-top: 8px; color:#cfcfcf; font-family: Arial, Helvetica, sans-serif; font-size:11px; letter-spacing: .6px; font-weight:600; }
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
                    meta.append(f"{t}:finnhub")
                    continue
            hist = yf.Ticker(t).history(period="1d", interval="1m")
            if not hist.empty:
                last = hist.iloc[-1]
                price = float(last["Close"])
                prev = float(hist.iloc[0]["Open"]) if "Open" in hist.columns else float(last["Close"])
                chg = price - prev
                pct = (chg / prev) * 100 if prev else 0
                rows.append({"ticker": t, "price": price, "change": chg, "pct": pct, "source": "yfinance"})
                meta.append(f"{t}:yfinance")
            else:
                rows.append({"ticker": t, "price": None, "change": None, "pct": None, "source": "no data"})
                meta.append(f"{t}:no-data")
        except Exception:
            rows.append({"ticker": t, "price": None, "change": None, "pct": None, "source": "error"})
            meta.append(f"{t}:error")
    return rows, meta


@st.cache_data(ttl=120)
def fetch_broad_universe():
    urls = [
        "https://www.slickcharts.com/sp500/gainers",
        "https://www.slickcharts.com/sp500/losers",
        "https://www.slickcharts.com/market-movers",
        "https://uk.finance.yahoo.com/markets/stocks/gainers/",
    ]
    syms = []
    meta = []
    for url in urls:
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            text = r.text
            found = re.findall(r'"symbol":"([A-Z\.\-]{1,8})"', text)
            if not found:
                found = re.findall(r'\b[A-Z]{1,5}\b', text)
            for s in found:
                if s not in syms and len(s) <= 5 and s.isupper():
                    syms.append(s)
            meta.append(f"{url.split('//')[-1][:24]}:{len(found)}")
        except Exception:
            meta.append(f"{url.split('//')[-1][:24]}:error")
    syms = [s for s in syms if s not in {"USD","CEO","ETF","EPS","PCT","NYSE","NASDAQ"}]
    return syms[:50], meta


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


def render_row(time, symb, trade, cp, side, strk, score, note, direction, source):
    color = "#7cff7c" if direction == "BULL" else "#ff8a8a"
    side_color = "green" if direction == "BULL" else "red"
    trade_color = "green" if direction == "BULL" else "red"
    st.markdown(f"""
<div class="card" style="padding:6px 10px; margin:4px 0;">
  <div style="display:grid; grid-template-columns: 1.1fr .9fr .8fr .8fr .9fr .8fr .5fr 1.8fr; gap:8px; align-items:center; font-size:12px; line-height:1.05;">
    <div style="color:#a9a9a9;">{clean_text(time)}</div>
    <div style="color:#f3f3f3; font-weight:700;">{clean_text(symb)}</div>
    <div><span class="tag {trade_color}">{clean_text(trade) if trade else '—'}</span></div>
    <div><span class="tag {side_color}">{clean_text(cp)}</span></div>
    <div><span class="tag {side_color}">{clean_text(side)}</span></div>
    <div style="color:#e6e6e6;">{clean_text(strk)}</div>
    <div style="color:{color}; font-weight:700;">{clean_text(direction)}</div>
    <div style="color:#cfcfcf;">{clean_text(note)} <span style="color:#888;">{clean_text(source)}</span></div>
  </div>
</div>
""", unsafe_allow_html=True)


st.markdown('<div class="scanner-wrap">', unsafe_allow_html=True)
st.markdown('<div class="title">MULTI-TICKER SCANNER</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Broad market scan with gappers, catalyst watch, and news</div>', unsafe_allow_html=True)
st.markdown("".join([f'<span class="chip">{c}</span>' for c in ["PIVOT", "2–5 day", "S&P 500", "High conviction"]]), unsafe_allow_html=True)

universe, uni_meta = fetch_broad_universe()
quotes, quote_meta = fetch_live_quotes(universe if universe else ["SPY","QQQ","AAPL","MSFT","NVDA","TSLA","AMD","META","AMZN","GOOGL"])
news, news_meta = fetch_marketaux_news()
rss_items, rss_meta = fetch_rss(RSS_URL)

st.caption(f"Universe: {' | '.join(uni_meta)}")
st.caption(f"Quotes: {' | '.join(quote_meta[:25])}")
st.caption(f"Catalyst: {news_meta} | RSS: {rss_meta}")

up = [q for q in quotes if q["pct"] is not None and q["pct"] >= 0]
dn = [q for q in quotes if q["pct"] is not None and q["pct"] < 0]
up = sorted(up, key=lambda x: x["pct"], reverse=True)[:15]
dn = sorted(dn, key=lambda x: x["pct"])[:15]
act = sorted([q for q in quotes if q["price"] is not None], key=lambda x: abs(x["pct"] or 0), reverse=True)[:15]

st.markdown('<div class="section">DAILY GAPPERS UP</div>', unsafe_allow_html=True)
if up:
    for i, q in enumerate(up):
        render_row("—", q["ticker"], "", "Calls", "At Ask", "—", f"{q['pct']:+.2f}%", "Bull", "GAP UP", q["source"])
else:
    render_row("—", "—", "", "Calls", "At Ask", "—", "0.00%", "Bull", "NO DATA", "Gappers up")

st.markdown('<div class="section">DAILY GAPPERS DOWN</div>', unsafe_allow_html=True)
if dn:
    for i, q in enumerate(dn):
        render_row("—", q["ticker"], "", "Puts", "At Ask", "—", f"{q['pct']:+.2f}%", "Bear", "GAP DN", q["source"])
else:
    render_row("—", "—", "", "Puts", "At Ask", "—", "0.00%", "Bear", "Gappers down")

st.markdown('<div class="section">MOST ACTIVE / BIG MOVERS</div>', unsafe_allow_html=True)
if act:
    for i, q in enumerate(act):
        side = "Calls" if (q["pct"] or 0) >= 0 else "Puts"
        direction = "Bull" if side == "Calls" else "Bear"
        render_row("—", q["ticker"], "Sweep" if i % 3 == 0 else "", side, "At Ask", "—", f"{q['pct']:+.2f}%", direction, "ACTIVE", q["source"])
else:
    render_row("—", "—", "", "Calls", "At Ask", "—", "0.00%", "Bear", "Most active")

st.markdown('<div class="section">CATALYST WATCH</div>', unsafe_allow_html=True)
if news:
    for i, x in enumerate(news):
        render_row("—", x.get("source", "Marketaux"), "Sweep", "Calls", "At Ask", "—", "+0.00%", "Bull", x["headline"], x["source"])
elif rss_items:
    for i, x in enumerate(rss_items):
        render_row("—", x.get("source", "RSS"), "Split", "Calls", "At Ask", "—", "+0.00%", "Bull", x["headline"], x["source"])
else:
    render_row("—", "—", "", "Puts", "At Ask", "—", "0.00%", "Bear", "NO FEED", "Catalyst feed")

st.markdown('</div>', unsafe_allow_html=True)
