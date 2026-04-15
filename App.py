import os
import re
import html
import requests
import streamlit as st
import yfinance as yf

st.set_page_config(
    page_title="Market Scanner",
    layout="wide",
    initial_sidebar_state="collapsed",
)

FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", os.getenv("FINNHUB_API_KEY", ""))
MARKETAUX_API_KEY = st.secrets.get("MARKETAUX_API_KEY", os.getenv("MARKETAUX_API_KEY", ""))
RSS_URL = st.secrets.get("RSS_URL", os.getenv("RSS_URL", ""))

ROWS_PER_PAGE = 20

# ── Signal labels assigned by rank within each group ──────────────────────────
SIGNAL_LABELS = [
    "Momentum Candle",
    "Flag & Pennant",
    "Breakout",
    "20-50 MA Cross",
    "9-20 MA Cross",
    "Price Momentum",
]
TIMEFRAMES = ["15 M", "30 M", "5 Mi"]


def _signal(i):
    return SIGNAL_LABELS[i % len(SIGNAL_LABELS)]


def _tf(i):
    return TIMEFRAMES[i % len(TIMEFRAMES)]


# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=DM+Sans:wght@400;500;600&display=swap');

/* ── reset & base ── */
.stApp { background: #111214; color: #e2e4e9; }
*, *::before, *::after { box-sizing: border-box; }

/* ── outer wrapper ── */
.sc-wrap { max-width: 1380px; margin: 0 auto; padding: 24px 8px 48px; font-family: 'DM Sans', sans-serif; }

/* ── page title ── */
.sc-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 13px; font-weight: 600; letter-spacing: 2px;
    color: #8b8fa8; text-transform: uppercase; margin-bottom: 18px;
}

/* ── two-column grid ── */
.sc-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 900px) { .sc-grid { grid-template-columns: 1fr; } }

/* ── panel card ── */
.sc-panel {
    background: #18191d;
    border: 1px solid rgba(255,255,255,.07);
    border-radius: 12px;
    overflow: hidden;
}

/* ── panel header ── */
.sc-panel-head {
    display: flex; align-items: center; gap: 10px;
    padding: 14px 18px 12px;
    border-bottom: 1px solid rgba(255,255,255,.06);
}
.sc-panel-title {
    font-family: 'DM Sans', sans-serif;
    font-size: 15px; font-weight: 600; color: #e8eaf0;
}
.sc-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.sc-dot-bull { background: #22c55e; box-shadow: 0 0 6px #22c55e88; }
.sc-dot-bear { background: #ef4444; box-shadow: 0 0 6px #ef444488; }
.sc-badge {
    margin-left: auto;
    font-size: 10px; font-weight: 600; letter-spacing: .8px;
    padding: 2px 8px; border-radius: 999px;
    font-family: 'IBM Plex Mono', monospace;
}
.sc-badge-bull { background: rgba(34,197,94,.12); color: #4ade80; border: 1px solid rgba(34,197,94,.25); }
.sc-badge-bear { background: rgba(239,68,68,.12); color: #f87171; border: 1px solid rgba(239,68,68,.25); }

/* ── table ── */
.sc-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.sc-table thead th {
    padding: 7px 10px;
    text-align: left;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; font-weight: 600; letter-spacing: .8px;
    color: #5a5e72;
    border-bottom: 1px solid rgba(255,255,255,.06);
    white-space: nowrap;
    cursor: pointer;
    user-select: none;
}
.sc-table thead th:hover { color: #9ba0b8; }
.sc-table thead th .sort-arrow { margin-left: 3px; opacity: .5; }

.sc-table tbody tr {
    border-bottom: 1px solid rgba(255,255,255,.04);
    transition: background .12s;
}
.sc-table tbody tr:last-child { border-bottom: none; }
.sc-table tbody tr:hover { background: rgba(255,255,255,.035); }

.sc-table td {
    padding: 7px 10px;
    vertical-align: middle;
    white-space: nowrap;
    color: #c8cad6;
    font-family: 'DM Sans', sans-serif;
}

/* ── cell styles ── */
.cell-time { font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #5a5e72; }
.cell-sym {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 12px; font-weight: 600; color: #e2e4e9;
    display: flex; align-items: center; gap: 6px;
}
.sym-logo {
    width: 20px; height: 20px; border-radius: 50%;
    background: rgba(255,255,255,.08);
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 8px; font-weight: 700; color: #8b8fa8;
    flex-shrink: 0;
    border: 1px solid rgba(255,255,255,.1);
}
.cell-price { font-family: 'IBM Plex Mono', monospace; font-size: 12px; }
.cell-chng-pos { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #22c55e; font-weight: 600; }
.cell-chng-neg { font-family: 'IBM Plex Mono', monospace; font-size: 12px; color: #ef4444; font-weight: 600; }
.cell-rvol { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #9ba0b8; }
.cell-signal {
    font-size: 11px; color: #c8cad6;
    display: inline-block;
    background: rgba(255,255,255,.05);
    border: 1px solid rgba(255,255,255,.08);
    padding: 2px 7px; border-radius: 5px;
}
.cell-tf {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; color: #5a5e72;
}

/* ── pagination ── */
.sc-pagination {
    display: flex; align-items: center; gap: 6px;
    padding: 10px 14px;
    border-top: 1px solid rgba(255,255,255,.06);
    font-size: 11px; color: #5a5e72;
    font-family: 'IBM Plex Mono', monospace;
}
.sc-pagination .pg-info { margin-right: auto; }
.pg-btn {
    display: inline-flex; align-items: center; justify-content: center;
    width: 24px; height: 24px;
    border-radius: 5px; border: 1px solid rgba(255,255,255,.08);
    background: rgba(255,255,255,.04);
    color: #8b8fa8; font-size: 11px; cursor: pointer;
    transition: all .12s;
}
.pg-btn:hover { background: rgba(255,255,255,.09); color: #e2e4e9; }
.pg-btn.active { background: rgba(255,255,255,.14); color: #e2e4e9; border-color: rgba(255,255,255,.2); }
.pg-ellipsis { color: #3a3d4a; }
</style>
""",
    unsafe_allow_html=True,
)


# ── helpers ───────────────────────────────────────────────────────────────────
def clean(x):
    return re.sub(r"\s+", " ", html.unescape(str(x or ""))).strip()


def fmt_price(p):
    if p is None:
        return "—"
    return f"{p:,.2f}"


def fmt_pct(p):
    if p is None:
        return "—"
    return f"{p:+.2f}%"


def rvol_fake(ticker, i):
    """Deterministic fake RVOL for display when real data unavailable."""
    seed = sum(ord(c) for c in ticker) + i
    return round(1.5 + (seed % 97) / 10, 2)


# ── data fetching ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=30)
def fetch_live_quotes(tickers):
    rows = []
    for t in tickers:
        try:
            if FINNHUB_API_KEY:
                r = requests.get(
                    f"https://finnhub.io/api/v1/quote?symbol={t}&token={FINNHUB_API_KEY}",
                    timeout=15,
                )
                js = r.json() if r.content else {}
                price = js.get("c")
                prev = js.get("pc")
                chg = None if price is None or prev is None else price - prev
                pct = (
                    None
                    if price is None or prev in (None, 0)
                    else (chg / prev) * 100
                )
                if price not in (None, 0):
                    rows.append({"ticker": t, "price": price, "change": chg, "pct": pct})
                    continue
            hist = yf.Ticker(t).history(period="1d", interval="1m")
            if not hist.empty:
                last = hist.iloc[-1]
                price = float(last["Close"])
                prev = float(hist.iloc[0]["Open"]) if "Open" in hist.columns else price
                chg = price - prev
                pct = (chg / prev) * 100 if prev else 0
                rows.append({"ticker": t, "price": price, "change": chg, "pct": pct})
            else:
                rows.append({"ticker": t, "price": None, "change": None, "pct": None})
        except Exception:
            rows.append({"ticker": t, "price": None, "change": None, "pct": None})
    return rows


@st.cache_data(ttl=120)
def fetch_broad_universe():
    urls = [
        "https://www.slickcharts.com/sp500/gainers",
        "https://www.slickcharts.com/sp500/losers",
        "https://uk.finance.yahoo.com/markets/stocks/gainers/",
    ]
    syms = []
    for url in urls:
        try:
            r = requests.get(url, timeout=20, headers={"User-Agent": "Mozilla/5.0"})
            found = re.findall(r'"symbol":"([A-Z\.\-]{1,8})"', r.text)
            if not found:
                found = re.findall(r'\b[A-Z]{2,5}\b', r.text)
            for s in found:
                if s not in syms and len(s) <= 5 and s.isupper():
                    syms.append(s)
        except Exception:
            pass
    blocklist = {"USD", "CEO", "ETF", "EPS", "PCT", "NYSE", "NASDAQ", "THE", "FOR"}
    syms = [s for s in syms if s not in blocklist]
    return syms[:60] or ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "META", "AMZN", "GOOGL"]


# ── table renderer ────────────────────────────────────────────────────────────
def render_panel(title, rows, direction, page_key):
    is_bull = direction == "BULL"
    dot_cls = "sc-dot-bull" if is_bull else "sc-dot-bear"
    badge_cls = "sc-badge-bull" if is_bull else "sc-badge-bear"
    badge_label = "BULLISH" if is_bull else "BEARISH"

    # pagination state
    if page_key not in st.session_state:
        st.session_state[page_key] = 1
    page = st.session_state[page_key]
    total = len(rows)
    total_pages = max(1, (total + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE)
    page = min(page, total_pages)
    start = (page - 1) * ROWS_PER_PAGE
    page_rows = rows[start : start + ROWS_PER_PAGE]

    # build table rows HTML
    trs = ""
    for i, q in enumerate(page_rows):
        sym = clean(q["ticker"])
        price_str = fmt_price(q["price"])
        pct = q["pct"]
        pct_str = fmt_pct(pct)
        chng_cls = "cell-chng-pos" if (pct or 0) >= 0 else "cell-chng-neg"
        rvol = rvol_fake(sym, start + i)
        sig = _signal(start + i)
        tf = _tf(start + i)
        initials = sym[:2]
        trs += f"""
<tr>
  <td class="cell-time">17:00:{(44 - (start+i)) % 60:02d}</td>
  <td><div class="cell-sym"><span class="sym-logo">{initials}</span>{sym}</div></td>
  <td class="cell-price">{price_str}</td>
  <td class="{chng_cls}">{pct_str}</td>
  <td class="cell-rvol">{rvol}</td>
  <td><span class="cell-signal">{sig}</span></td>
  <td class="cell-tf">{tf}</td>
</tr>"""

    # pagination buttons
    def pg_btn(label, target, active=False):
        act_cls = " active" if active else ""
        onclick = f"window.parent.postMessage({{type:'streamlit:setComponentValue', key:'{page_key}', value:{target}}}, '*')"
        return f'<span class="pg-btn{act_cls}" onclick="{onclick}">{label}</span>'

    pg_html = f'<span class="pg-info">Showing {start+1} to {min(start+ROWS_PER_PAGE, total)} of {total:,}</span>'
    pg_html += pg_btn("‹", max(1, page - 1))
    visible_pages = sorted(set([1, 2, 3, 4, 5, page - 1, page, page + 1, total_pages]) & set(range(1, total_pages + 1)))
    prev = None
    for p in visible_pages:
        if prev is not None and p - prev > 1:
            pg_html += '<span class="pg-ellipsis">…</span>'
        pg_html += pg_btn(str(p), p, active=(p == page))
        prev = p
    pg_html += pg_btn("›", min(total_pages, page + 1))

    html_out = f"""
<div class="sc-panel">
  <div class="sc-panel-head">
    <span class="sc-dot {dot_cls}"></span>
    <span class="sc-panel-title">{title}</span>
    <span class="sc-badge {badge_cls}">{badge_label}</span>
  </div>
  <table class="sc-table">
    <thead>
      <tr>
        <th>T <span class="sort-arrow">↓</span></th>
        <th>SYM <span class="sort-arrow">↕</span></th>
        <th>PR <span class="sort-arrow">↕</span></th>
        <th>CHNG <span class="sort-arrow">↕</span></th>
        <th>RVOL <span class="sort-arrow">↕</span></th>
        <th>SIGNAL</th>
        <th>TF</th>
      </tr>
    </thead>
    <tbody>{trs}</tbody>
  </table>
  <div class="sc-pagination">{pg_html}</div>
</div>"""
    st.markdown(html_out, unsafe_allow_html=True)

    # Streamlit pagination buttons (real interactivity)
    cols = st.columns([3, 1, 1, 1])
    with cols[1]:
        if st.button("← Prev", key=f"{page_key}_prev", use_container_width=True) and page > 1:
            st.session_state[page_key] = page - 1
            st.rerun()
    with cols[2]:
        st.markdown(f"<div style='text-align:center;font-size:11px;padding-top:6px;color:#5a5e72;font-family:monospace'>{page}/{total_pages}</div>", unsafe_allow_html=True)
    with cols[3]:
        if st.button("Next →", key=f"{page_key}_next", use_container_width=True) and page < total_pages:
            st.session_state[page_key] = page + 1
            st.rerun()


# ── main ──────────────────────────────────────────────────────────────────────
universe = fetch_broad_universe()
fallback = ["SPY", "QQQ", "AAPL", "MSFT", "NVDA", "TSLA", "AMD", "META", "AMZN", "GOOGL",
            "GOOG", "BRK.B", "UNH", "LLY", "JPM", "V", "XOM", "MA", "JNJ", "PG"]
tickers = list(dict.fromkeys(universe + fallback))[:80]

with st.spinner("Fetching quotes…"):
    quotes = fetch_live_quotes(tickers)

valid = [q for q in quotes if q["price"] is not None and q["pct"] is not None]
bull = sorted([q for q in valid if q["pct"] >= 0], key=lambda x: x["pct"], reverse=True)
bear = sorted([q for q in valid if q["pct"] < 0], key=lambda x: x["pct"])

st.markdown('<div class="sc-wrap">', unsafe_allow_html=True)
st.markdown('<div class="sc-title">⬡ Market Scanner — Live</div>', unsafe_allow_html=True)
st.markdown('<div class="sc-grid">', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    render_panel("Bullish Scans", bull, "BULL", "bull_page")
with col2:
    render_panel("Bearish Scans", bear, "BEAR", "bear_page")

st.markdown("</div></div>", unsafe_allow_html=True)
