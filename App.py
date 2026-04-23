import os
import re
import html
import requests
import streamlit as st
import yfinance as yf
from datetime import datetime, timedelta

st.set_page_config(page_title="Market Scanner", layout="wide", initial_sidebar_state="collapsed")

FINNHUB_API_KEY = st.secrets.get("FINNHUB_API_KEY", os.getenv("FINNHUB_API_KEY", ""))
MARKETAUX_API_KEY = st.secrets.get("MARKETAUX_API_KEY", os.getenv("MARKETAUX_API_KEY", ""))
RSS_URL = st.secrets.get("RSS_URL", os.getenv("RSS_URL", ""))

ROWS_PER_PAGE = 20
TOP_N = 80

st.markdown("""
<style>
.stApp { background:#000; color:#e2e4e9; }
* { box-sizing:border-box; }
body { font-family: 'DM Sans', sans-serif; }
.wrap { max-width:1440px; margin:0 auto; padding:0 16px 60px; }
.head { display:flex; align-items:center; gap:12px; padding:16px 4px 14px; border-bottom:1px solid rgba(255,255,255,.07); }
.logo { width:32px; height:32px; border-radius:7px; background:linear-gradient(135deg,#4f46e5,#818cf8); display:flex; align-items:center; justify-content:center; color:#fff; font-family:monospace; font-weight:700; }
.title { font-family:monospace; font-size:14px; font-weight:700; letter-spacing:2px; text-transform:uppercase; }
.sub { font-family:monospace; font-size:9px; color:#6b7280; letter-spacing:1.5px; text-transform:uppercase; }
.ts { margin-left:auto; font-family:monospace; font-size:11px; color:#9ca3af; background:rgba(255,255,255,.05); padding:5px 12px; border-radius:6px; border:1px solid rgba(255,255,255,.08); }
.panel { background:#0a0a0a; border:1px solid rgba(255,255,255,.1); border-radius:10px; overflow:hidden; margin-bottom:18px; }
.ph { display:flex; align-items:center; gap:10px; padding:13px 16px 11px; border-bottom:1px solid rgba(255,255,255,.06); background:rgba(0,0,0,.2); }
.pt { font-family:monospace; font-size:12px; font-weight:700; letter-spacing:.8px; text-transform:uppercase; }
.pc { margin-left:auto; font-family:monospace; font-size:11px; padding:3px 10px; border-radius:999px; border:1px solid rgba(255,255,255,.12); color:#c8cad6; }
.row { display:grid; grid-template-columns: 90px 1fr 80px 90px 90px 1fr; gap:0; padding:9px 14px; border-bottom:1px solid rgba(255,255,255,.03); align-items:center; }
.row:hover { background:rgba(255,255,255,.025); }
.headrow { display:grid; grid-template-columns: 90px 1fr 80px 90px 90px 1fr; gap:0; padding:7px 14px; border-bottom:1px solid rgba(255,255,255,.04); background:rgba(0,0,0,.2); }
.headrow span { font-family:monospace; font-size:8px; font-weight:700; letter-spacing:1.5px; color:#2e3148; text-transform:uppercase; }
.sym { font-family:monospace; font-size:12px; font-weight:700; color:#f0f1f5; }
.txt { font-size:12px; color:#c8cad6; }
.num { font-family:monospace; font-size:12px; color:#c8cad6; text-align:right; }
.pos { font-family:monospace; font-size:12px; color:#4ade80; font-weight:700; text-align:right; }
.neg { font-family:monospace; font-size:12px; color:#f87171; font-weight:700; text-align:right; }
.empty { padding:28px 16px; text-align:center; font-size:13px; color:#6b7280; }
.badge { display:inline-block; font-family:monospace; font-size:9px; font-weight:700; padding:2px 7px; border-radius:4px; margin-right:5px; border:1px solid rgba(99,102,241,.3); background:rgba(99,102,241,.16); color:#a5b4fc; }
.small { font-size:11px; color:#6b7280; }
.cal { display:grid; grid-template-columns: 95px 95px 1fr 100px 100px 110px; gap:0; padding:9px 14px; border-bottom:1px solid rgba(255,255,255,.03); align-items:center; }
.calhead { display:grid; grid-template-columns: 95px 95px 1fr 100px 100px 110px; gap:0; padding:7px 14px; border-bottom:1px solid rgba(255,255,255,.04); background:rgba(0,0,0,.2); }
.calhead span { font-family:monospace; font-size:8px; font-weight:700; letter-spacing:1.5px; color:#2e3148; text-transform:uppercase; }
.high { display:inline-block; font-family:monospace; font-size:8px; font-weight:700; padding:2px 7px; border-radius:4px; background:rgba(239,68,68,.12); color:#f87171; border:1px solid rgba(239,68,68,.25); }
.med { display:inline-block; font-family:monospace; font-size:8px; font-weight:700; padding:2px 7px; border-radius:4px; background:rgba(245,158,11,.1); color:#fcd34d; border:1px solid rgba(245,158,11,.2); }
.low { display:inline-block; font-family:monospace; font-size:8px; font-weight:700; padding:2px 7px; border-radius:4px; background:rgba(255,255,255,.06); color:#6b7280; border:1px solid rgba(255,255,255,.1); }
</style>
""", unsafe_allow_html=True)

def clean(x):
    return re.sub(r"\s+", " ", html.unescape(str(x or ""))).strip()

def fmt_price(v):
    return "—" if v is None else f"{v:,.2f}"

def fmt_pct(v):
    return "—" if v is None else f"{v:+.2f}%"

def fmt_vol(v):
    if v is None:
        return "—"
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"{v/1_000:.0f}K"
    return str(int(v))

@st.cache_data(ttl=86400)
def fetch_universe():
    syms = []
    block = {"USD","CEO","ETF","EPS","PCT","NYSE","NASDAQ","THE","FOR","AND","BUT","WITH","ALL","NEW","INC","LLC","LTD","PLC","EST","EDT","AM","PM","IPO"}
    finviz_urls = [
        "https://finviz.com/screener.ashx?v=111&s=ta_topvolume&o=-volume",
        "https://finviz.com/screener.ashx?v=111&s=ta_topgainers&o=-change",
    ]
    headers = {"User-Agent":"Mozilla/5.0","Referer":"https://finviz.com/"}
    for url in finviz_urls:
        try:
            r = requests.get(url, headers=headers, timeout=12)
            if r.status_code == 200:
                found = re.findall(r'class="screener-link-primary">([A-Z]{1,5})<', r.text)
                for s in found:
                    if s not in syms and s not in block:
                        syms.append(s)
        except Exception:
            pass
    if len(syms) < 40:
        try:
            r = requests.get("https://finance.yahoo.com/markets/stocks/most-active/", headers={"User-Agent":"Mozilla/5.0"}, timeout=12)
            for s in re.findall(r'"symbol":"([A-Z]{1,5})"', r.text):
                if s not in syms and s not in block:
                    syms.append(s)
        except Exception:
            pass
    core = ["SPY","QQQ","AAPL","MSFT","NVDA","TSLA","AMD","META","AMZN","GOOGL","JPM","V","XOM","MA","BAC","WMT","UNH","GS","NFLX","COIN","PLTR","SOFI","MARA","GME","SMCI","ARM","MU","AVGO","UBER","SNAP"]
    for s in core:
        if s not in syms:
            syms.append(s)
    syms = [s for s in dict.fromkeys(syms) if 1 < len(s) <= 5 and s not in block]
    return syms[:TOP_N]

@st.cache_data(ttl=300)
def fetch_quotes(tickers):
    out = []
    if not tickers:
        return out
    try:
        data = yf.download(list(tickers), period="2d", interval="1d", group_by="ticker", auto_adjust=True, progress=False, threads=False)
    except Exception:
        data = None
    for t in tickers:
        try:
            df = data[t] if data is not None and hasattr(data, "columns") and t in getattr(data.columns, "get_level_values", lambda x: [])(0) else None
            if df is None or getattr(df, 'empty', True):
                tk = yf.Ticker(t)
                hist = tk.history(period="2d", interval="1d")
                df = hist
            if df is None or df.empty:
                out.append({"ticker":t,"price":None,"change":None,"pct":None,"open":None,"prev_close":None,"volume":None})
                continue
            price = float(df["Close"].iloc[-1])
            open_p = float(df["Open"].iloc[-1]) if "Open" in df.columns else None
            prev_close = float(df["Close"].iloc[-2]) if len(df) >= 2 else price
            change = price - prev_close
            pct = (change/prev_close*100) if prev_close else None
            vol = int(df["Volume"].iloc[-1]) if "Volume" in df.columns else None
            out.append({"ticker":t,"price":price,"change":change,"pct":pct,"open":open_p,"prev_close":prev_close,"volume":vol})
        except Exception:
            out.append({"ticker":t,"price":None,"change":None,"pct":None,"open":None,"prev_close":None,"volume":None})
    return out

@st.cache_data(ttl=3600)
def fetch_news():
    items = []
    try:
        for sym in ["SPY","AAPL","MSFT","NVDA","TSLA"]:
            tk = yf.Ticker(sym)
            for item in (tk.news or [])[:3]:
                ct = item.get("content", {})
                title = ct.get("title", item.get("title", ""))
                if not title:
                    continue
                link = ct.get("canonicalUrl", {}).get("url", "") or item.get("link", "")
                source = ct.get("provider", {}).get("displayName", "Yahoo Finance") or item.get("publisher", "Yahoo Finance")
                pub = ""
                ts = ct.get("pubDate") or item.get("providerPublishTime")
                if isinstance(ts, (int, float)):
                    pub = datetime.fromtimestamp(ts).strftime("%b %d")
                items.append({"headline":clean(title),"link":link,"source":clean(source),"published":pub,"tickers":[sym]})
        return items[:15]
    except Exception:
        return []

@st.cache_data(ttl=1800)
def fetch_earnings(tickers):
    out = []
    for sym in tickers[:80]:
        eps = None
        timing = ""
        date_str = ""
        exp_move = None
        try:
            tk = yf.Ticker(sym)
            ed = tk.earnings_dates
            if ed is not None and not ed.empty:
                row = ed.reset_index().iloc[0]
                d = row.iloc[0]
                if hasattr(d, "date"):
                    d = d.date()
                elif isinstance(d, str):
                    try:
                        d = datetime.strptime(d[:10], "%Y-%m-%d").date()
                    except Exception:
                        d = None
                if d:
                    date_str = str(d)
                    eps_val = row.get("EPS Estimate", None)
                    if eps_val is None and "EPS Estimate" in ed.columns:
                        eps_val = ed["EPS Estimate"].iloc[0]
                    try:
                        eps = float(eps_val) if eps_val not in (None, "") else None
                    except Exception:
                        eps = None
                    timing = "BMO" if sym in {"UNH","JPM","WMT","HD","COST","BAC","GS"} else "AMC"
            try:
                price = float(getattr(tk.fast_info, 'lastPrice', None) or tk.info.get('regularMarketPrice') or 0)
                exps = tk.options or []
                if exps and price:
                    exp = exps[0]
                    chain = tk.option_chain(exp)
                    if chain.calls is not None and chain.puts is not None and not chain.calls.empty and not chain.puts.empty:
                        calls = chain.calls.copy()
                        puts = chain.puts.copy()
                        calls['dist'] = (calls['strike'] - price).abs()
                        atm = float(calls.sort_values('dist').iloc[0]['strike'])
                        c = float(calls.loc[calls['strike'] == atm, 'lastPrice'].fillna(0).iloc[0])
                        p = float(puts.loc[puts['strike'] == atm, 'lastPrice'].fillna(0).iloc[0])
                        mv = c + p
                        exp_move = round(mv, 2) if mv > 0 else None
            except Exception:
                exp_move = None
        except Exception:
            pass
        if date_str:
            out.append({"symbol":sym,"date":date_str,"timing":timing,"epsest":eps,"expected_move":exp_move})
    return out

def render_quotes(quotes):
    st.markdown('<div class="panel"><div class="ph"><span class="pt">Top 80 Scanner</span><span class="pc">Daily Finviz + Yahoo</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="headrow"><span>Symbol</span><span>Price</span><span>Chg</span><span>Vol</span><span>Open</span><span>Prev Close</span></div>', unsafe_allow_html=True)
    if not quotes:
        st.markdown('<div class="empty">No scanner data found.</div></div>', unsafe_allow_html=True)
        return
    for q in quotes[:ROWS_PER_PAGE]:
        pct = q.get("pct") or 0
        cls = "pos" if pct >= 0 else "neg"
        st.markdown(f'<div class="row"><div class="sym">{q["ticker"]}</div><div class="txt">{fmt_price(q.get("price"))}</div><div class="{cls}">{fmt_pct(q.get("pct"))}</div><div class="num">{fmt_vol(q.get("volume"))}</div><div class="num">{fmt_price(q.get("open"))}</div><div class="num">{fmt_price(q.get("prev_close"))}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_earnings(rows):
    st.markdown('<div class="panel"><div class="ph"><span class="pt">Earnings</span><span class="pc">EPS + Expected Move ready</span></div>', unsafe_allow_html=True)
    st.markdown('<div class="calhead"><span>Symbol</span><span>Date</span><span>Timing</span><span>EPS Est</span><span>Exp Move</span><span>Status</span></div>', unsafe_allow_html=True)
    if not rows:
        st.markdown('<div class="empty">No earnings data available right now.</div></div>', unsafe_allow_html=True)
        return
    for r in rows[:ROWS_PER_PAGE]:
        sym = r.get("symbol", "")
        date = r.get("date", "")
        timing = r.get("timing", "") or "N/A"
        eps = r.get("epsest")
        eps_txt = "N/A" if eps is None else f"{eps:.2f}"
        move_txt = "N/A"
        em = r.get("expected_move")
        if em is not None:
            try:
                price = None
                tk = yf.Ticker(sym)
                price = float(getattr(tk.fast_info, 'lastPrice', None) or tk.info.get('regularMarketPrice') or 0)
                move_txt = f"{em:.2f} ({em/price*100:.1f}%)" if price else f"{em:.2f}"
            except Exception:
                move_txt = f"{em:.2f}"
        status = 'Ready' if (eps_txt != 'N/A' or move_txt != 'N/A') else 'Partial'
        st.markdown(f'<div class="cal"><div class="sym">{sym}</div><div class="txt">{date}</div><div class="txt">{timing}</div><div class="num">{eps_txt}</div><div class="num">{move_txt}</div><div class="txt">{status}</div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def render_news(items):
    st.markdown('<div class="panel"><div class="ph"><span class="pt">Catalyst News</span><span class="pc">Yahoo + fallback</span></div>', unsafe_allow_html=True)
    if not items:
        st.markdown('<div class="empty">No recent news found.</div></div>', unsafe_allow_html=True)
        return
    for it in items[:10]:
        tickers = ' '.join([f'<span class="badge">{t}</span>' for t in it.get('tickers', [])[:4]])
        headline = clean(it.get('headline', ''))
        link = it.get('link', '')
        src = clean(it.get('source', ''))
        pub = clean(it.get('published', ''))
        hl = f'<a class="news-link" href="{link}" target="_blank">{headline}</a>' if link else headline
        st.markdown(f'<div class="row" style="grid-template-columns: 1fr;"><div><div>{tickers}</div><div class="txt">{hl}</div><div class="small">{src} {pub}</div></div></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


def main():
    st.markdown('<div class="wrap">', unsafe_allow_html=True)
    st.markdown(f'<div class="head"><div class="logo">MS</div><div><div class="title">Market Scanner</div><div class="sub">Top 80 daily universe</div></div><div class="ts">{datetime.now().strftime("%b %d, %Y %I:%M %p")}</div></div>', unsafe_allow_html=True)
    universe = fetch_universe()
    quotes = fetch_quotes(tuple(universe))
    earnings = fetch_earnings(tuple(universe))
    news = fetch_news()
    render_quotes(quotes)
    render_earnings(earnings)
    render_detail_cards(earnings)
    render_news(news)
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == '__main__':
    main()


# v3 alias kept for deployment
main()


def render_detail_cards(earnings_rows):
    st.markdown('<div class="panel"><div class="ph"><span class="pt">Earnings Detail</span><span class="pc">Expected move + EPS</span></div>', unsafe_allow_html=True)
    if not earnings_rows:
        st.markdown('<div class="empty">No earnings detail available.</div></div>', unsafe_allow_html=True)
        return
    cols = st.columns(2)
    for i, r in enumerate(earnings_rows[:10]):
        col = cols[i % 2]
        sym = r.get('symbol', '')
        date = r.get('date', '')
        timing = r.get('timing', '') or 'N/A'
        eps = r.get('epsest')
        em = r.get('expected_move')
        eps_txt = 'N/A' if eps is None else f'{eps:.2f}'
        em_txt = 'N/A' if em is None else f'{em:.2f}'
        with col:
            st.markdown(f"""<div class='panel' style='margin-bottom:12px;'><div class='ph'><span class='pt'>{sym}</span><span class='pc'>{date}</span></div><div style='padding:14px 16px; line-height:1.7;'><div><span class='small'>Timing:</span> <span class='txt'>{timing}</span></div><div><span class='small'>EPS Est:</span> <span class='txt'>{eps_txt}</span></div><div><span class='small'>Expected Move:</span> <span class='txt'>{em_txt}</span></div></div></div>""", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
