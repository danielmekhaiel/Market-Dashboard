import os
import re
import html
import requests
import streamlit as st
import yfinance as yf
from datetime import datetime

st.set_page_config(
    page_title="Market Scanner",
    layout="wide",
    initial_sidebar_state="collapsed",
)

FINNHUB_API_KEY  = st.secrets.get("FINNHUB_API_KEY",  os.getenv("FINNHUB_API_KEY",  ""))
MARKETAUX_API_KEY = st.secrets.get("MARKETAUX_API_KEY", os.getenv("MARKETAUX_API_KEY", ""))
RSS_URL          = st.secrets.get("RSS_URL",           os.getenv("RSS_URL",           ""))

ROWS_PER_PAGE = 20
GAP_THRESHOLD = 1.5   # % open vs prev-close considered a gap

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=DM+Sans:wght@400;500;600&display=swap');

.stApp { background: #0d0f10; color: #e2e4e9; }
*, *::before, *::after { box-sizing: border-box; }

.sc-wrap { max-width: 1400px; margin: 0 auto; padding: 24px 12px 60px; font-family: 'DM Sans', sans-serif; }

/* header */
.sc-header { display: flex; align-items: baseline; gap: 14px; margin-bottom: 6px; }
.sc-title { font-family: 'IBM Plex Mono', monospace; font-size: 18px; font-weight: 600; color: #e8eaf0; letter-spacing: 1px; }
.sc-sub { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #4a4e62; letter-spacing: 1.5px; text-transform: uppercase; }
.sc-timestamp { margin-left: auto; font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #4a4e62; }

/* section label */
.sc-section {
    font-family: 'IBM Plex Mono', monospace; font-size: 10px; font-weight: 600;
    letter-spacing: 2px; color: #4a4e62; text-transform: uppercase;
    margin: 28px 0 10px; padding-left: 2px;
    display: flex; align-items: center; gap: 10px;
}
.sc-section::after { content: ''; flex: 1; height: 1px; background: rgba(255,255,255,.06); }

/* panel */
.sc-panel { background: #13151a; border: 1px solid rgba(255,255,255,.07); border-radius: 10px; overflow: hidden; }
.sc-panel-bull   { border-top: 2px solid #16a34a; }
.sc-panel-bear   { border-top: 2px solid #dc2626; }
.sc-panel-gap-up { border-top: 2px solid #22c55e; }
.sc-panel-gap-dn { border-top: 2px solid #ef4444; }
.sc-panel-news   { border-top: 2px solid #6366f1; }

/* panel header */
.sc-panel-head {
    display: flex; align-items: center; gap: 10px;
    padding: 12px 16px 10px; border-bottom: 1px solid rgba(255,255,255,.05);
}
.sc-panel-title { font-size: 13px; font-weight: 600; color: #e8eaf0; }
.sc-count {
    margin-left: auto; font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; padding: 1px 7px; border-radius: 999px;
    font-weight: 600; letter-spacing: .5px;
}
.sc-count-bull   { background: rgba(22,163,74,.15);  color: #4ade80; border: 1px solid rgba(22,163,74,.3); }
.sc-count-bear   { background: rgba(220,38,38,.15);  color: #f87171; border: 1px solid rgba(220,38,38,.3); }
.sc-count-gap-up { background: rgba(34,197,94,.12);  color: #86efac; border: 1px solid rgba(34,197,94,.25); }
.sc-count-gap-dn { background: rgba(239,68,68,.12);  color: #fca5a5; border: 1px solid rgba(239,68,68,.25); }
.sc-count-news   { background: rgba(99,102,241,.15); color: #a5b4fc; border: 1px solid rgba(99,102,241,.3); }

/* table */
.sc-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.sc-table thead th {
    padding: 6px 12px; text-align: left;
    font-family: 'IBM Plex Mono', monospace; font-size: 9px; font-weight: 600;
    letter-spacing: 1px; color: #3d4158; border-bottom: 1px solid rgba(255,255,255,.05);
    white-space: nowrap;
}
.sc-table thead th.r { text-align: right; }
.sc-table tbody tr { border-bottom: 1px solid rgba(255,255,255,.035); transition: background .1s; }
.sc-table tbody tr:last-child { border-bottom: none; }
.sc-table tbody tr:hover { background: rgba(255,255,255,.03); }
.sc-table td { padding: 7px 12px; vertical-align: middle; white-space: nowrap; }

/* cells */
.c-sym {
    display: flex; align-items: center; gap: 7px;
    font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 600; color: #e8eaf0;
}
.sym-av {
    width: 22px; height: 22px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 7px; font-weight: 700; flex-shrink: 0; border: 1px solid rgba(255,255,255,.1);
}
.av-bull { background: rgba(22,163,74,.2);  color: #4ade80; }
.av-bear { background: rgba(220,38,38,.2);  color: #f87171; }
.av-up   { background: rgba(34,197,94,.15); color: #86efac; }
.av-dn   { background: rgba(239,68,68,.15); color: #fca5a5; }
.av-neu  { background: rgba(255,255,255,.06); color: #8b8fa8; }

.c-price  { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #c8cad6; text-align: right; }
.c-pos    { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #22c55e; font-weight: 600; text-align: right; }
.c-neg    { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #ef4444; font-weight: 600; text-align: right; }
.c-vol    { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #555870; text-align: right; }
.c-gap-up { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #22c55e; font-weight: 700; text-align: right; }
.c-gap-dn { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #ef4444; font-weight: 700; text-align: right; }

/* pagination */
.sc-pg {
    display: flex; align-items: center; gap: 5px;
    padding: 8px 12px; border-top: 1px solid rgba(255,255,255,.05);
    font-size: 10px; color: #3d4158; font-family: 'IBM Plex Mono', monospace;
}
.sc-pg .pg-info { margin-right: auto; }

/* news */
.news-row { padding: 10px 16px; border-bottom: 1px solid rgba(255,255,255,.04); }
.news-row:last-child { border-bottom: none; }
.news-row:hover { background: rgba(255,255,255,.02); }
.news-ticker {
    display: inline-block; font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; font-weight: 700; padding: 1px 6px; border-radius: 4px;
    margin-right: 5px; background: rgba(99,102,241,.15); color: #a5b4fc;
    border: 1px solid rgba(99,102,241,.25); vertical-align: middle;
}
.news-headline { font-size: 12px; color: #c8cad6; line-height: 1.45; }
.news-meta { font-size: 10px; color: #3d4158; margin-top: 3px; font-family: 'IBM Plex Mono', monospace; }
a.news-link { color: #818cf8 !important; text-decoration: none; }
a.news-link:hover { color: #a5b4fc !important; text-decoration: underline; }

/* empty */
.sc-empty {
    padding: 28px 16px; text-align: center;
    font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #3d4158; letter-spacing: 1px;
}
</style>
""", unsafe_allow_html=True)


# ── helpers ───────────────────────────────────────────────────────────────────
def clean(x):
    return re.sub(r"\s+", " ", html.unescape(str(x or ""))).strip()

def fmt_price(p):
    return f"{p:,.2f}" if p is not None else "—"

def fmt_pct(p):
    return f"{p:+.2f}%" if p is not None else "—"

def fmt_vol(v):
    if v is None: return "—"
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M"
    if v >= 1_000: return f"{v/1_000:.0f}K"
    return str(int(v))

def _pg_controls(page_key, total):
    total_pages = max(1, (total + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)
    page = st.session_state.get(page_key, 1)
    col_p, col_m, col_n = st.columns([1, 1, 1])
    with col_p:
        if st.button("← Prev", key=f"{page_key}_prev", use_container_width=True, disabled=(page <= 1)):
            st.session_state[page_key] = page - 1; st.rerun()
    with col_m:
        st.markdown(f"<div style='text-align:center;font-size:10px;padding-top:8px;color:#3d4158;font-family:monospace'>{page}/{total_pages}</div>", unsafe_allow_html=True)
    with col_n:
        if st.button("Next →", key=f"{page_key}_next", use_container_width=True, disabled=(page >= total_pages)):
            st.session_state[page_key] = page + 1; st.rerun()


# ── data ──────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch_quotes(tickers):
    rows = []
    for t in tickers:
        rec = {"ticker": t, "price": None, "change": None, "pct": None,
               "open": None, "prev_close": None, "gap_pct": None, "volume": None}
        try:
            if FINNHUB_API_KEY:
                r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={t}&token={FINNHUB_API_KEY}", timeout=15)
                js = r.json() if r.content else {}
                price, prev_close, open_p = js.get("c"), js.get("pc"), js.get("o")
                if price not in (None, 0):
                    chg = price - prev_close if prev_close else None
                    pct = (chg / prev_close * 100) if prev_close else None
                    gap = ((open_p - prev_close) / prev_close * 100) if (open_p and prev_close) else None
                    rows.append({**rec, "price": price, "change": chg, "pct": pct,
                                 "open": open_p, "prev_close": prev_close, "gap_pct": gap})
                    continue
            # yfinance fallback
            tk = yf.Ticker(t)
            hist  = tk.history(period="2d",  interval="1d")
            intra = tk.history(period="1d",  interval="1m")
            if not intra.empty:
                price     = float(intra.iloc[-1]["Close"])
                open_p    = float(intra.iloc[0]["Open"]) if "Open" in intra.columns else price
                vol       = int(intra["Volume"].sum())   if "Volume" in intra.columns else None
                prev_close = float(hist.iloc[-2]["Close"]) if len(hist) >= 2 else open_p
                chg  = price - prev_close
                pct  = (chg / prev_close * 100) if prev_close else 0
                gap  = ((open_p - prev_close) / prev_close * 100) if prev_close else 0
                rows.append({**rec, "price": price, "change": chg, "pct": pct,
                             "open": open_p, "prev_close": prev_close, "gap_pct": gap, "volume": vol})
            else:
                rows.append(rec)
        except Exception:
            rows.append(rec)
    return rows


@st.cache_data(ttl=120)
def fetch_universe():
    urls = [
        "https://www.slickcharts.com/sp500/gainers",
        "https://www.slickcharts.com/sp500/losers",
        "https://uk.finance.yahoo.com/markets/stocks/gainers/",
        "https://uk.finance.yahoo.com/markets/stocks/losers/",
    ]
    syms = []
    for url in urls:
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            found = re.findall(r'"symbol":"([A-Z\.\-]{1,8})"', r.text) or re.findall(r'\b[A-Z]{2,5}\b', r.text)
            for s in found:
                if s not in syms and len(s) <= 5 and s.isupper():
                    syms.append(s)
        except Exception:
            pass
    block = {"USD","CEO","ETF","EPS","PCT","NYSE","NASDAQ","THE","FOR","AND","BUT","WITH","ALL","NEW"}
    syms = [s for s in syms if s not in block]
    fallback = ["SPY","QQQ","AAPL","MSFT","NVDA","TSLA","AMD","META","AMZN","GOOGL",
                "GOOG","JPM","V","XOM","MA","JNJ","PG","BAC","WMT","DIS","NFLX","INTC","PYPL"]
    return list(dict.fromkeys(syms[:60] + fallback))[:80]


@st.cache_data(ttl=180)
def fetch_news():
    items = []
    if MARKETAUX_API_KEY:
        try:
            url = (f"https://api.marketaux.com/v1/news/all"
                   f"?language=en&filter_entities=true&limit=15&api_token={MARKETAUX_API_KEY}")
            js = requests.get(url, timeout=20).json()
            for x in js.get("data", [])[:15]:
                tickers = list(dict.fromkeys(
                    e.get("symbol", e.get("ticker", "")).upper()
                    for e in (x.get("entities") or [])
                    if e.get("symbol") or e.get("ticker")
                ))[:4]
                src = x.get("source", {})
                items.append({
                    "headline": clean(x.get("title", "")),
                    "link": x.get("url", ""),
                    "source": src.get("name", "Marketaux") if isinstance(src, dict) else str(src),
                    "tickers": tickers,
                    "published": (x.get("published_at") or "")[:10],
                })
            if items: return items
        except Exception:
            pass
    if RSS_URL:
        try:
            import feedparser
            for e in feedparser.parse(RSS_URL).entries[:12]:
                h = getattr(e, "title", "")
                items.append({
                    "headline": clean(h),
                    "link": getattr(e, "link", ""),
                    "source": getattr(getattr(e, "source", None), "title", "RSS"),
                    "tickers": list(dict.fromkeys(re.findall(r'\b([A-Z]{2,5})\b', h)))[:4],
                    "published": getattr(e, "published", "")[:10],
                })
            return items
        except Exception:
            pass
    return []


# ── panel renderers ───────────────────────────────────────────────────────────
def render_scan_panel(title, rows, direction, page_key):
    is_bull = direction == "BULL"
    if page_key not in st.session_state: st.session_state[page_key] = 1
    page  = min(st.session_state[page_key], max(1, (len(rows) + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE))
    start = (page - 1) * ROWS_PER_PAGE
    page_rows = rows[start: start + ROWS_PER_PAGE]

    av_cls   = "av-bull" if is_bull else "av-bear"
    panel_cls = "sc-panel-bull" if is_bull else "sc-panel-bear"
    cnt_cls   = "sc-count-bull" if is_bull else "sc-count-bear"

    trs = ""
    for q in page_rows:
        sym = clean(q["ticker"])
        pct = q["pct"]
        cc  = "c-pos" if (pct or 0) >= 0 else "c-neg"
        trs += f"""<tr>
  <td><div class="c-sym"><span class="sym-av {av_cls}">{sym[:2]}</span>{sym}</div></td>
  <td class="c-price">{fmt_price(q['price'])}</td>
  <td class="{cc}">{fmt_pct(pct)}</td>
  <td class="c-vol">{fmt_vol(q.get('volume'))}</td>
</tr>"""

    body = (f"""<table class="sc-table">
  <thead><tr><th>SYMBOL</th><th class="r">PRICE</th><th class="r">CHG %</th><th class="r">VOLUME</th></tr></thead>
  <tbody>{trs}</tbody>
</table>
<div class="sc-pg"><span class="pg-info">Showing {start+1}–{min(start+ROWS_PER_PAGE,len(rows))} of {len(rows)}</span></div>"""
            if page_rows else '<div class="sc-empty">NO DATA</div>')

    st.markdown(f"""<div class="sc-panel {panel_cls}">
  <div class="sc-panel-head">
    <span class="sc-panel-title">{title}</span>
    <span class="sc-count {cnt_cls}">{len(rows)}</span>
  </div>{body}</div>""", unsafe_allow_html=True)
    _pg_controls(page_key, len(rows))


def render_gap_panel(title, rows, direction, page_key):
    is_up = direction == "UP"
    if page_key not in st.session_state: st.session_state[page_key] = 1
    page  = min(st.session_state[page_key], max(1, (len(rows) + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE))
    start = (page - 1) * ROWS_PER_PAGE
    page_rows = rows[start: start + ROWS_PER_PAGE]

    av_cls    = "av-up"  if is_up else "av-dn"
    gap_cls   = "c-gap-up" if is_up else "c-gap-dn"
    panel_cls = "sc-panel-gap-up" if is_up else "sc-panel-gap-dn"
    cnt_cls   = "sc-count-gap-up" if is_up else "sc-count-gap-dn"
    badge     = f"GAP {'UP ▲' if is_up else 'DOWN ▼'} · {len(rows)}"

    trs = ""
    for q in page_rows:
        sym = clean(q["ticker"])
        pct_cc = "c-pos" if (q["pct"] or 0) >= 0 else "c-neg"
        trs += f"""<tr>
  <td><div class="c-sym"><span class="sym-av {av_cls}">{sym[:2]}</span>{sym}</div></td>
  <td class="c-price">{fmt_price(q['prev_close'])}</td>
  <td class="c-price">{fmt_price(q['open'])}</td>
  <td class="{gap_cls}">{fmt_pct(q['gap_pct'])}</td>
  <td class="{pct_cc}">{fmt_pct(q['pct'])}</td>
  <td class="c-vol">{fmt_vol(q.get('volume'))}</td>
</tr>"""

    body = (f"""<table class="sc-table">
  <thead><tr><th>SYMBOL</th><th class="r">PREV CLOSE</th><th class="r">OPEN</th>
    <th class="r">GAP %</th><th class="r">DAY CHG %</th><th class="r">VOLUME</th></tr></thead>
  <tbody>{trs}</tbody>
</table>
<div class="sc-pg"><span class="pg-info">Showing {start+1}–{min(start+ROWS_PER_PAGE,len(rows))} of {len(rows)}</span></div>"""
            if page_rows else '<div class="sc-empty">NO GAP DATA — FINNHUB KEY REQUIRED FOR ACCURATE OPEN vs PREV CLOSE</div>')

    st.markdown(f"""<div class="sc-panel {panel_cls}">
  <div class="sc-panel-head">
    <span class="sc-panel-title">{title}</span>
    <span class="sc-count {cnt_cls}">{badge}</span>
  </div>{body}</div>""", unsafe_allow_html=True)
    _pg_controls(page_key, len(rows))


def render_news_panel(news_items):
    if not news_items:
        body = '<div class="sc-empty">NO NEWS — ADD MARKETAUX_API_KEY OR RSS_URL TO SECRETS</div>'
    else:
        rows_html = ""
        for item in news_items:
            tickers_html = "".join(f'<span class="news-ticker">{t}</span>' for t in item["tickers"])
            h = clean(item["headline"])
            link = item.get("link", "")
            h_html = f'<a class="news-link" href="{link}" target="_blank">{h}</a>' if link else h
            pub = item.get("published", "")
            rows_html += f"""<div class="news-row">
  <div>{tickers_html}<span class="news-headline">{h_html}</span></div>
  <div class="news-meta">{clean(item['source'])}{' · ' + pub if pub else ''}</div>
</div>"""
        body = rows_html

    st.markdown(f"""<div class="sc-panel sc-panel-news">
  <div class="sc-panel-head">
    <span class="sc-panel-title">Catalyst News</span>
    <span class="sc-count sc-count-news">{len(news_items)} stories</span>
  </div>{body}</div>""", unsafe_allow_html=True)


# ── main ──────────────────────────────────────────────────────────────────────
now_str = datetime.now().strftime("%b %d, %Y  %H:%M:%S")

with st.spinner("Fetching universe…"):
    tickers = fetch_universe()

with st.spinner("Fetching live quotes…"):
    quotes = fetch_quotes(tickers)

with st.spinner("Fetching catalyst news…"):
    news = fetch_news()

valid    = [q for q in quotes if q["price"] is not None and q["pct"] is not None]
bull     = sorted([q for q in valid if (q["pct"] or 0) >= 0], key=lambda x: x["pct"], reverse=True)
bear     = sorted([q for q in valid if (q["pct"] or 0) <  0], key=lambda x: x["pct"])
gap_valid = [q for q in valid if q.get("gap_pct") is not None]
gap_up   = sorted([q for q in gap_valid if q["gap_pct"] >= GAP_THRESHOLD],  key=lambda x: x["gap_pct"], reverse=True)
gap_dn   = sorted([q for q in gap_valid if q["gap_pct"] <= -GAP_THRESHOLD], key=lambda x: x["gap_pct"])

# ── render ────────────────────────────────────────────────────────────────────
st.markdown('<div class="sc-wrap">', unsafe_allow_html=True)
st.markdown(f"""<div class="sc-header">
  <span class="sc-title">MARKET SCANNER</span>
  <span class="sc-sub">Live · S&amp;P 500 + Broad Market</span>
  <span class="sc-timestamp">{now_str}</span>
</div>""", unsafe_allow_html=True)

st.markdown('<div class="sc-section">Bullish &amp; Bearish Scans</div>', unsafe_allow_html=True)
c1, c2 = st.columns(2)
with c1: render_scan_panel("Bullish Scans", bull, "BULL", "bull_page")
with c2: render_scan_panel("Bearish Scans", bear, "BEAR", "bear_page")

st.markdown('<div class="sc-section">Daily Gappers</div>', unsafe_allow_html=True)
c3, c4 = st.columns(2)
with c3: render_gap_panel("Gappers Up",   gap_up, "UP", "gap_up_page")
with c4: render_gap_panel("Gappers Down", gap_dn, "DN", "gap_dn_page")

st.markdown('<div class="sc-section">Catalyst News</div>', unsafe_allow_html=True)
render_news_panel(news)

st.markdown('</div>', unsafe_allow_html=True)
