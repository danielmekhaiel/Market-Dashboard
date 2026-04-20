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

# Auto-refresh every 30 seconds
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30_000, key="autorefresh")
except ImportError:
    st.warning("Install streamlit-autorefresh for live updates: `pip install streamlit-autorefresh`")

FINNHUB_API_KEY   = st.secrets.get("FINNHUB_API_KEY",   os.getenv("FINNHUB_API_KEY",   ""))
MARKETAUX_API_KEY = st.secrets.get("MARKETAUX_API_KEY", os.getenv("MARKETAUX_API_KEY", ""))
RSS_URL           = st.secrets.get("RSS_URL",            os.getenv("RSS_URL",            ""))

ROWS_PER_PAGE = 20
GAP_THRESHOLD = 1.5

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=DM+Sans:wght@400;500;600&display=swap');

.stApp { background: #0d0f10; color: #e2e4e9; }
*, *::before, *::after { box-sizing: border-box; }

.sc-wrap { max-width: 1440px; margin: 0 auto; padding: 0 16px 60px; font-family: 'DM Sans', sans-serif; }

/* header */
.sc-header {
    display: flex; align-items: center; gap: 14px;
    padding: 16px 4px 14px;
    border-bottom: 1px solid rgba(255,255,255,.05);
    margin-bottom: 4px;
}
.sc-logo {
    width: 30px; height: 30px; border-radius: 7px;
    background: linear-gradient(135deg, #4f46e5, #818cf8);
    display: inline-flex; align-items: center; justify-content: center;
    font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 700; color: #fff;
    flex-shrink: 0;
}
.sc-title { font-family: 'IBM Plex Mono', monospace; font-size: 14px; font-weight: 700; color: #e8eaf0; letter-spacing: 2.5px; text-transform: uppercase; }
.sc-sub { font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #3d4158; letter-spacing: 1.5px; text-transform: uppercase; }
.sc-divider { width: 1px; height: 18px; background: rgba(255,255,255,.07); margin: 0 2px; }
.sc-timestamp { margin-left: auto; font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #3d4158; background: rgba(255,255,255,.03); padding: 4px 10px; border-radius: 6px; border: 1px solid rgba(255,255,255,.05); }

/* market summary bar */
.sc-mkt-bar {
    display: flex; gap: 0; margin: 10px 0 2px;
    background: #0f1117; border: 1px solid rgba(255,255,255,.06);
    border-radius: 10px; overflow: hidden;
}
.sc-mkt-item {
    flex: 1; padding: 10px 16px; border-right: 1px solid rgba(255,255,255,.05);
    display: flex; flex-direction: column; gap: 3px;
}
.sc-mkt-item:last-child { border-right: none; }
.sc-mkt-label { font-family: 'IBM Plex Mono', monospace; font-size: 8px; letter-spacing: 1.5px; color: #3d4158; text-transform: uppercase; }
.sc-mkt-val { font-family: 'IBM Plex Mono', monospace; font-size: 13px; font-weight: 600; color: #e8eaf0; }
.sc-mkt-chg-pos { font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #22c55e; }
.sc-mkt-chg-neg { font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #ef4444; }

/* section label */
.sc-section {
    font-family: 'IBM Plex Mono', monospace; font-size: 9px; font-weight: 700;
    letter-spacing: 2.5px; color: #3d4158; text-transform: uppercase;
    margin: 22px 0 8px; padding-left: 2px;
    display: flex; align-items: center; gap: 12px;
}
.sc-section::after { content: ''; flex: 1; height: 1px; background: rgba(255,255,255,.04); }

/* panel */
.sc-panel {
    background: #0f1117;
    border: 1px solid rgba(255,255,255,.06);
    border-radius: 10px; overflow: hidden;
    box-shadow: 0 2px 20px rgba(0,0,0,.35);
}
.sc-panel-bull   { border-top: 2px solid #16a34a; }
.sc-panel-bear   { border-top: 2px solid #dc2626; }
.sc-panel-gap-up { border-top: 2px solid #22c55e; }
.sc-panel-gap-dn { border-top: 2px solid #ef4444; }
.sc-panel-news   { border-top: 2px solid #6366f1; }

/* panel header */
.sc-panel-head {
    display: flex; align-items: center; gap: 10px;
    padding: 12px 16px 10px;
    border-bottom: 1px solid rgba(255,255,255,.04);
    background: rgba(0,0,0,.15);
}
.sc-panel-title { font-size: 11px; font-weight: 700; color: #c8cad6; letter-spacing: .8px; text-transform: uppercase; font-family: 'IBM Plex Mono', monospace; }
.sc-count {
    margin-left: auto; font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; padding: 2px 8px; border-radius: 999px;
    font-weight: 700; letter-spacing: .5px;
}
.sc-count-bull   { background: rgba(22,163,74,.1);   color: #4ade80; border: 1px solid rgba(22,163,74,.2); }
.sc-count-bear   { background: rgba(220,38,38,.1);   color: #f87171; border: 1px solid rgba(220,38,38,.2); }
.sc-count-gap-up { background: rgba(34,197,94,.08);  color: #86efac; border: 1px solid rgba(34,197,94,.18); }
.sc-count-gap-dn { background: rgba(239,68,68,.08);  color: #fca5a5; border: 1px solid rgba(239,68,68,.18); }
.sc-count-news   { background: rgba(99,102,241,.1);  color: #a5b4fc; border: 1px solid rgba(99,102,241,.2); }

/* table */
.sc-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.sc-table thead th {
    padding: 7px 14px; text-align: left;
    font-family: 'IBM Plex Mono', monospace; font-size: 8px; font-weight: 700;
    letter-spacing: 1.5px; color: #2e3148; border-bottom: 1px solid rgba(255,255,255,.04);
    white-space: nowrap; text-transform: uppercase; background: rgba(0,0,0,.2);
}
.sc-table thead th.r { text-align: right; }
.sc-table tbody tr { border-bottom: 1px solid rgba(255,255,255,.025); transition: background .15s; }
.sc-table tbody tr:last-child { border-bottom: none; }
.sc-table tbody tr:hover { background: rgba(99,102,241,.04); }
.sc-table td { padding: 8px 14px; vertical-align: middle; white-space: nowrap; }

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

.sc-pg {
    display: flex; align-items: center; gap: 5px;
    padding: 8px 12px; border-top: 1px solid rgba(255,255,255,.05);
    font-size: 10px; color: #3d4158; font-family: 'IBM Plex Mono', monospace;
}
.sc-pg .pg-info { margin-right: auto; }

/* clickable ticker rows */
.ticker-btn-row { cursor: pointer; }
.ticker-btn-row:hover .c-sym { color: #818cf8 !important; }

/* news */
.news-row {
    padding: 12px 18px; border-bottom: 1px solid rgba(255,255,255,.05);
    display: flex; gap: 12px; align-items: flex-start;
}
.news-row:last-child { border-bottom: none; }
.news-row:hover { background: rgba(255,255,255,.025); }
.news-dot {
    width: 6px; height: 6px; border-radius: 50%; background: #6366f1;
    flex-shrink: 0; margin-top: 5px;
}
.news-body { flex: 1; min-width: 0; }
.news-ticker {
    display: inline-block; font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; font-weight: 700; padding: 1px 6px; border-radius: 3px;
    margin-right: 5px; margin-bottom: 4px; background: rgba(99,102,241,.18); color: #a5b4fc;
    border: 1px solid rgba(99,102,241,.3); vertical-align: middle; letter-spacing: .5px;
}
.news-headline { font-size: 13px; color: #f0f1f5; line-height: 1.5; font-weight: 500; }
.news-meta { font-size: 10px; color: #4a4e62; margin-top: 4px; font-family: 'IBM Plex Mono', monospace; letter-spacing: .3px; }
a.news-link { color: #f0f1f5 !important; text-decoration: none; }
a.news-link:hover { color: #a5b4fc !important; }

.sc-empty {
    padding: 28px 16px; text-align: center;
    font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #3d4158; letter-spacing: 1px;
}

/* ticker detail modal */
.ticker-detail-panel {
    background: #13151a;
    border: 1px solid rgba(99,102,241,.3);
    border-top: 2px solid #818cf8;
    border-radius: 10px;
    padding: 0;
    margin-bottom: 20px;
    overflow: hidden;
}
.td-header {
    display: flex; align-items: center; gap: 16px;
    padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,.06);
    background: rgba(99,102,241,.06);
}
.td-sym { font-family: 'IBM Plex Mono', monospace; font-size: 22px; font-weight: 700; color: #e8eaf0; }
.td-name { font-size: 13px; color: #6b7280; margin-top: 2px; }
.td-price { font-family: 'IBM Plex Mono', monospace; font-size: 26px; font-weight: 600; color: #e8eaf0; margin-left: auto; }
.td-chg-pos { font-family: 'IBM Plex Mono', monospace; font-size: 14px; color: #22c55e; font-weight: 600; }
.td-chg-neg { font-family: 'IBM Plex Mono', monospace; font-size: 14px; color: #ef4444; font-weight: 600; }
.td-stats { display: flex; gap: 0; border-bottom: 1px solid rgba(255,255,255,.06); }
.td-stat {
    flex: 1; padding: 14px 20px; border-right: 1px solid rgba(255,255,255,.05);
    display: flex; flex-direction: column; gap: 4px;
}
.td-stat:last-child { border-right: none; }
.td-stat-label { font-family: 'IBM Plex Mono', monospace; font-size: 9px; letter-spacing: 1.5px; color: #4a4e62; text-transform: uppercase; }
.td-stat-value { font-family: 'IBM Plex Mono', monospace; font-size: 13px; color: #c8cad6; font-weight: 600; }
.td-stat-value.pos { color: #22c55e; }
.td-stat-value.neg { color: #ef4444; }
.td-section-label {
    font-family: 'IBM Plex Mono', monospace; font-size: 9px; letter-spacing: 2px;
    color: #4a4e62; text-transform: uppercase; padding: 12px 20px 6px;
    border-bottom: 1px solid rgba(255,255,255,.04);
}
.td-news-row { padding: 9px 20px; border-bottom: 1px solid rgba(255,255,255,.03); font-size: 12px; color: #9ca3af; line-height: 1.4; }
.td-news-row:last-child { border-bottom: none; }
a.td-news-link { color: #818cf8 !important; text-decoration: none; }
a.td-news-link:hover { text-decoration: underline; }
.td-news-src { font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #4a4e62; margin-top: 2px; }
.td-no-news { padding: 16px 20px; font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #3d4158; }

/* ── options flow ── */
.sc-panel-flow  { border-top: 2px solid #f59e0b; }
.sc-count-flow  { background: rgba(245,158,11,.1); color: #fcd34d; border: 1px solid rgba(245,158,11,.2); }
.flow-row {
    display: grid;
    grid-template-columns: 56px 52px 70px 70px 60px 60px 70px 1fr;
    gap: 0; padding: 8px 14px;
    border-bottom: 1px solid rgba(255,255,255,.03);
    align-items: center; font-size: 11px;
    transition: background .15s;
}
.flow-row:last-child { border-bottom: none; }
.flow-row:hover { background: rgba(245,158,11,.04); }
.flow-head {
    display: grid;
    grid-template-columns: 56px 52px 70px 70px 60px 60px 70px 1fr;
    gap: 0; padding: 7px 14px;
    border-bottom: 1px solid rgba(255,255,255,.04);
    background: rgba(0,0,0,.2);
}
.flow-head span {
    font-family: 'IBM Plex Mono', monospace; font-size: 8px;
    font-weight: 700; letter-spacing: 1.5px; color: #2e3148; text-transform: uppercase;
}
.flow-sym { font-family: 'IBM Plex Mono', monospace; font-weight: 700; color: #e8eaf0; font-size: 12px; }
.flow-call { color: #22c55e; font-family: 'IBM Plex Mono', monospace; font-weight: 700; font-size: 11px; }
.flow-put  { color: #ef4444; font-family: 'IBM Plex Mono', monospace; font-weight: 700; font-size: 11px; }
.flow-strike { font-family: 'IBM Plex Mono', monospace; color: #c8cad6; font-size: 11px; }
.flow-exp    { font-family: 'IBM Plex Mono', monospace; color: #6b7280; font-size: 10px; }
.flow-prem   { font-family: 'IBM Plex Mono', monospace; font-weight: 700; font-size: 11px; }
.flow-prem-lg { color: #fcd34d; }
.flow-prem-md { color: #c8cad6; }
.flow-side-ask  { background: rgba(34,197,94,.12);  color: #4ade80; border: 1px solid rgba(34,197,94,.25);  font-family: 'IBM Plex Mono', monospace; font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 4px; display: inline-block; }
.flow-side-bid  { background: rgba(239,68,68,.12);  color: #f87171; border: 1px solid rgba(239,68,68,.25);  font-family: 'IBM Plex Mono', monospace; font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 4px; display: inline-block; }
.flow-side-mid  { background: rgba(255,255,255,.06); color: #8b8fa8; border: 1px solid rgba(255,255,255,.1); font-family: 'IBM Plex Mono', monospace; font-size: 9px; font-weight: 700; padding: 2px 7px; border-radius: 4px; display: inline-block; }
.flow-tag-sweep { background: rgba(245,158,11,.15); color: #fcd34d; border: 1px solid rgba(245,158,11,.3); font-family: 'IBM Plex Mono', monospace; font-size: 8px; font-weight: 700; padding: 1px 5px; border-radius: 3px; margin-left: 4px; letter-spacing: .5px; }
.flow-tag-block { background: rgba(99,102,241,.12); color: #a5b4fc; border: 1px solid rgba(99,102,241,.25); font-family: 'IBM Plex Mono', monospace; font-size: 8px; font-weight: 700; padding: 1px 5px; border-radius: 3px; margin-left: 4px; letter-spacing: .5px; }
.flow-time { font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #3d4158; text-align: right; }
.flow-filters {
    display: flex; gap: 8px; padding: 10px 14px;
    border-bottom: 1px solid rgba(255,255,255,.04);
    background: rgba(0,0,0,.1); flex-wrap: wrap;
}
.flow-filter-label { font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #3d4158; letter-spacing: 1px; text-transform: uppercase; align-self: center; }

/* ── volume spikes ── */
.sc-panel-vol   { border-top: 2px solid #06b6d4; }
.sc-count-vol   { background: rgba(6,182,212,.1); color: #67e8f9; border: 1px solid rgba(6,182,212,.2); }
.vol-row {
    display: grid;
    grid-template-columns: 64px 90px 90px 80px 1fr 80px;
    gap: 0; padding: 8px 14px;
    border-bottom: 1px solid rgba(255,255,255,.03);
    align-items: center; transition: background .15s;
}
.vol-row:hover { background: rgba(6,182,212,.04); }
.vol-row:last-child { border-bottom: none; }
.vol-head {
    display: grid;
    grid-template-columns: 64px 90px 90px 80px 1fr 80px;
    gap: 0; padding: 7px 14px;
    border-bottom: 1px solid rgba(255,255,255,.04);
    background: rgba(0,0,0,.2);
}
.vol-head span {
    font-family: 'IBM Plex Mono', monospace; font-size: 8px;
    font-weight: 700; letter-spacing: 1.5px; color: #2e3148; text-transform: uppercase;
}
.vol-sym  { font-family: 'IBM Plex Mono', monospace; font-weight: 700; color: #e8eaf0; font-size: 12px; }
.vol-num  { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #c8cad6; }
.vol-ratio-high { font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 700; color: #06b6d4; }
.vol-ratio-med  { font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 700; color: #67e8f9; }
.vol-bar-wrap { background: rgba(255,255,255,.05); border-radius: 3px; height: 6px; overflow: hidden; }
.vol-bar-fill { height: 100%; border-radius: 3px; background: linear-gradient(90deg, #06b6d4, #818cf8); }

/* ── calendar ── */
.sc-panel-cal   { border-top: 2px solid #a855f7; }
.sc-count-cal   { background: rgba(168,85,247,.1); color: #d8b4fe; border: 1px solid rgba(168,85,247,.2); }
.cal-tabs { display: flex; border-bottom: 1px solid rgba(255,255,255,.05); }
.cal-tab {
    padding: 9px 18px; font-family: 'IBM Plex Mono', monospace;
    font-size: 10px; font-weight: 700; letter-spacing: 1px; text-transform: uppercase;
    color: #3d4158; cursor: pointer; border-bottom: 2px solid transparent;
    transition: color .15s;
}
.cal-tab.active { color: #d8b4fe; border-bottom-color: #a855f7; }
.cal-row {
    display: grid; grid-template-columns: 80px 80px 1fr 100px 80px;
    gap: 0; padding: 9px 14px;
    border-bottom: 1px solid rgba(255,255,255,.03);
    align-items: center; font-size: 11px; transition: background .15s;
}
.cal-row:hover { background: rgba(168,85,247,.04); }
.cal-row:last-child { border-bottom: none; }
.cal-head {
    display: grid; grid-template-columns: 80px 80px 1fr 100px 80px;
    gap: 0; padding: 7px 14px;
    border-bottom: 1px solid rgba(255,255,255,.04);
    background: rgba(0,0,0,.2);
}
.cal-head span {
    font-family: 'IBM Plex Mono', monospace; font-size: 8px;
    font-weight: 700; letter-spacing: 1.5px; color: #2e3148; text-transform: uppercase;
}
.cal-date  { font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #6b7280; }
.cal-today { font-family: 'IBM Plex Mono', monospace; font-size: 10px; color: #fcd34d; font-weight: 700; }
.cal-sym   { font-family: 'IBM Plex Mono', monospace; font-size: 12px; font-weight: 700; color: #e8eaf0; }
.cal-name  { font-size: 12px; color: #9ca3af; }
.cal-est   { font-family: 'IBM Plex Mono', monospace; font-size: 11px; color: #c8cad6; }
.cal-impact-high { background: rgba(239,68,68,.12); color: #f87171; border: 1px solid rgba(239,68,68,.25); font-family: 'IBM Plex Mono', monospace; font-size: 8px; font-weight: 700; padding: 2px 7px; border-radius: 4px; display: inline-block; letter-spacing: .5px; }
.cal-impact-med  { background: rgba(245,158,11,.1);  color: #fcd34d; border: 1px solid rgba(245,158,11,.2); font-family: 'IBM Plex Mono', monospace; font-size: 8px; font-weight: 700; padding: 2px 7px; border-radius: 4px; display: inline-block; letter-spacing: .5px; }
.cal-impact-low  { background: rgba(255,255,255,.06); color: #6b7280; border: 1px solid rgba(255,255,255,.1); font-family: 'IBM Plex Mono', monospace; font-size: 8px; font-weight: 700; padding: 2px 7px; border-radius: 4px; display: inline-block; letter-spacing: .5px; }
.cal-timing { font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #6b7280; }
.cal-bmo { color: #22c55e; }
.cal-amc { color: #f59e0b; }

/* ── streamlit tab overrides ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: #0f1117;
    border: 1px solid rgba(255,255,255,.06);
    border-radius: 10px;
    padding: 4px;
    margin-bottom: 8px;
}
.stTabs [data-baseweb="tab"] {
    background: transparent;
    border-radius: 7px;
    color: #4a4e62;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: .5px;
    padding: 8px 18px;
    border: none;
    transition: all .15s;
}
.stTabs [data-baseweb="tab"]:hover {
    color: #c8cad6;
    background: rgba(255,255,255,.04);
}
.stTabs [aria-selected="true"] {
    background: rgba(99,102,241,.15) !important;
    color: #a5b4fc !important;
    border: 1px solid rgba(99,102,241,.25) !important;
}
.stTabs [data-baseweb="tab-highlight"] { display: none; }
.stTabs [data-baseweb="tab-border"]    { display: none; }
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
    if v >= 1_000_000_000: return f"{v/1_000_000_000:.2f}B"
    if v >= 1_000_000: return f"{v/1_000_000:.1f}M"
    if v >= 1_000: return f"{v/1_000:.0f}K"
    return str(int(v))

def fmt_mktcap(v):
    if v is None: return "—"
    if v >= 1_000_000_000_000: return f"${v/1_000_000_000_000:.2f}T"
    if v >= 1_000_000_000: return f"${v/1_000_000_000:.1f}B"
    if v >= 1_000_000: return f"${v/1_000_000:.0f}M"
    return f"${v:,.0f}"

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
            tk = yf.Ticker(t)
            hist  = tk.history(period="2d", interval="1d")
            intra = tk.history(period="1d", interval="1m")
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


@st.cache_data(ttl=300)
def fetch_ticker_detail(ticker):
    """Fetch detailed info for a single ticker using yfinance."""
    try:
        tk = yf.Ticker(ticker)
        info = tk.info or {}
        hist = tk.history(period="5d", interval="1d")

        # 52-week high/low
        wk52_high = info.get("fiftyTwoWeekHigh")
        wk52_low  = info.get("fiftyTwoWeekLow")
        mkt_cap   = info.get("marketCap")
        pe_ratio  = info.get("trailingPE")
        avg_vol   = info.get("averageVolume")
        beta      = info.get("beta")
        name      = info.get("shortName") or info.get("longName") or ticker
        sector    = info.get("sector", "")
        industry  = info.get("industry", "")

        return {
            "name": name,
            "sector": sector,
            "industry": industry,
            "wk52_high": wk52_high,
            "wk52_low": wk52_low,
            "mkt_cap": mkt_cap,
            "pe_ratio": pe_ratio,
            "avg_vol": avg_vol,
            "beta": beta,
            "hist": hist,
        }
    except Exception:
        return {}


@st.cache_data(ttl=180)
def fetch_ticker_news(ticker):
    """Fetch news for a specific ticker."""
    items = []
    # Try Finnhub company news if key available
    if FINNHUB_API_KEY:
        try:
            today = datetime.now().strftime("%Y-%m-%d")
            r = requests.get(
                f"https://finnhub.io/api/v1/company-news?symbol={ticker}&from=2024-01-01&to={today}&token={FINNHUB_API_KEY}",
                timeout=15
            )
            js = r.json() if r.content else []
            for item in js[:5]:
                items.append({
                    "headline": clean(item.get("headline", "")),
                    "link": item.get("url", ""),
                    "source": clean(item.get("source", "")),
                    "published": datetime.fromtimestamp(item.get("datetime", 0)).strftime("%b %d") if item.get("datetime") else "",
                })
            if items:
                return items
        except Exception:
            pass

    # Fallback: yfinance news
    try:
        tk = yf.Ticker(ticker)
        news = tk.news or []
        for item in news[:5]:
            ct = item.get("content", {})
            title = ct.get("title", item.get("title", ""))
            link  = ct.get("canonicalUrl", {}).get("url", "") or item.get("link", "")
            provider = ct.get("provider", {}).get("displayName", "") or item.get("publisher", "")
            pub_date = ""
            pub_ts = ct.get("pubDate") or item.get("providerPublishTime")
            if pub_ts:
                try:
                    if isinstance(pub_ts, (int, float)):
                        pub_date = datetime.fromtimestamp(pub_ts).strftime("%b %d")
                    else:
                        pub_date = str(pub_ts)[:10]
                except Exception:
                    pass
            if title:
                items.append({"headline": clean(title), "link": link, "source": clean(provider), "published": pub_date})
        return items
    except Exception:
        return []


@st.cache_data(ttl=300)
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

    # 1. Marketaux (if key provided)
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
            if items:
                return items
        except Exception:
            pass

    # 2. Custom RSS (if provided)
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
            if items:
                return items
        except Exception:
            pass

    # 3. Free fallback — Yahoo Finance RSS feeds (no key needed)
    FREE_FEEDS = [
        ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US", "Yahoo Finance"),
        ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AAPL,MSFT,NVDA,TSLA,META&region=US&lang=en-US", "Yahoo Finance"),
        ("https://feeds.finance.yahoo.com/rss/2.0/headline?s=AMZN,GOOGL,JPM,AMD,NFLX&region=US&lang=en-US", "Yahoo Finance"),
    ]
    try:
        import feedparser
        for feed_url, feed_name in FREE_FEEDS:
            try:
                parsed = feedparser.parse(feed_url)
                for e in parsed.entries[:6]:
                    h = getattr(e, "title", "")
                    if not h:
                        continue
                    tickers = list(dict.fromkeys(re.findall(r'\b([A-Z]{2,5})\b', h)))
                    tickers = [t for t in tickers if t not in {"US","AM","PM","ET","EST","EDT","CEO","IPO","GDP","CPI","Fed","SEC","NYSE","NASDAQ"}][:4]
                    pub = ""
                    if hasattr(e, "published_parsed") and e.published_parsed:
                        try:
                            pub = datetime(*e.published_parsed[:6]).strftime("%b %d")
                        except Exception:
                            pass
                    items.append({
                        "headline": clean(h),
                        "link": getattr(e, "link", ""),
                        "source": feed_name,
                        "tickers": tickers,
                        "published": pub,
                    })
            except Exception:
                continue
        if items:
            return items
    except ImportError:
        pass

    # 4. yfinance market news as last resort
    try:
        for sym in ["SPY", "AAPL", "MSFT", "NVDA", "TSLA"]:
            tk = yf.Ticker(sym)
            news = tk.news or []
            for item in news[:3]:
                ct = item.get("content", {})
                title = ct.get("title", item.get("title", ""))
                link  = ct.get("canonicalUrl", {}).get("url", "") or item.get("link", "")
                provider = ct.get("provider", {}).get("displayName", "") or item.get("publisher", "Yahoo Finance")
                pub_date = ""
                pub_ts = ct.get("pubDate") or item.get("providerPublishTime")
                if pub_ts:
                    try:
                        if isinstance(pub_ts, (int, float)):
                            pub_date = datetime.fromtimestamp(pub_ts).strftime("%b %d")
                        else:
                            pub_date = str(pub_ts)[:10]
                    except Exception:
                        pass
                if title and not any(x["headline"] == clean(title) for x in items):
                    items.append({
                        "headline": clean(title),
                        "link": link,
                        "source": clean(provider),
                        "tickers": [sym],
                        "published": pub_date,
                    })
        return items[:15]
    except Exception:
        pass

    return []


# ── ticker detail view ────────────────────────────────────────────────────────
def render_ticker_detail(ticker, quote):
    detail = fetch_ticker_detail(ticker)
    news   = fetch_ticker_news(ticker)

    pct = quote.get("pct") or 0
    chg_cls = "td-chg-pos" if pct >= 0 else "td-chg-neg"

    name = detail.get("name", ticker)
    sector = detail.get("sector", "")
    sub = f"{sector}" if sector else ""

    # Stats row
    stats = [
        ("Open",        fmt_price(quote.get("open"))),
        ("Prev Close",  fmt_price(quote.get("prev_close"))),
        ("Volume",      fmt_vol(quote.get("volume"))),
        ("Avg Volume",  fmt_vol(detail.get("avg_vol"))),
        ("Mkt Cap",     fmt_mktcap(detail.get("mkt_cap"))),
        ("52W High",    fmt_price(detail.get("wk52_high"))),
        ("52W Low",     fmt_price(detail.get("wk52_low"))),
        ("P/E Ratio",   f"{detail['pe_ratio']:.1f}" if detail.get("pe_ratio") else "—"),
        ("Beta",        f"{detail['beta']:.2f}" if detail.get("beta") else "—"),
    ]

    stats_html = "".join(
        f'<div class="td-stat"><div class="td-stat-label">{label}</div><div class="td-stat-value">{val}</div></div>'
        for label, val in stats
    )

    news_html = ""
    if news:
        for item in news:
            h = clean(item["headline"])
            link = item.get("link", "")
            src  = item.get("source", "")
            pub  = item.get("published", "")
            h_html = f'<a class="td-news-link" href="{link}" target="_blank">{h}</a>' if link else h
            meta = f"{src}{' · ' + pub if pub else ''}"
            news_html += f'<div class="td-news-row">{h_html}<div class="td-news-src">{meta}</div></div>'
    else:
        news_html = '<div class="td-no-news">No recent news found</div>'

    st.markdown(f"""
<div class="ticker-detail-panel">
  <div class="td-header">
    <div>
      <div class="td-sym">{ticker}</div>
      <div class="td-name">{clean(name)}{' · ' + sub if sub else ''}</div>
    </div>
    <div style="margin-left:auto;text-align:right">
      <div class="td-price">${fmt_price(quote.get('price'))}</div>
      <div class="{chg_cls}">{fmt_pct(pct)} today</div>
    </div>
  </div>
  <div class="td-stats">{stats_html}</div>
  <div class="td-section-label">Recent News</div>
  {news_html}
</div>
""", unsafe_allow_html=True)

    if st.button("✕ Close", key=f"close_{ticker}"):
        st.session_state["selected_ticker"] = None
        st.session_state["selected_quote"]  = None
        st.rerun()


# ── panel renderers ───────────────────────────────────────────────────────────
def render_scan_panel(title, rows, direction, page_key):
    is_bull = direction == "BULL"
    if page_key not in st.session_state: st.session_state[page_key] = 1
    page  = min(st.session_state[page_key], max(1, (len(rows) + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE))
    start = (page - 1) * ROWS_PER_PAGE
    page_rows = rows[start: start + ROWS_PER_PAGE]

    av_cls    = "av-bull" if is_bull else "av-bear"
    panel_cls = "sc-panel-bull" if is_bull else "sc-panel-bear"
    cnt_cls   = "sc-count-bull" if is_bull else "sc-count-bear"

    st.markdown(f"""<div class="sc-panel {panel_cls}">
  <div class="sc-panel-head">
    <span class="sc-panel-title">{title}</span>
    <span class="sc-count {cnt_cls}">{len(rows)}</span>
  </div>""", unsafe_allow_html=True)

    if not page_rows:
        st.markdown('<div class="sc-empty">NO DATA</div>', unsafe_allow_html=True)
    else:
        # Header row
        st.markdown("""<table class="sc-table"><thead>
<tr><th>SYMBOL</th><th class="r">PRICE</th><th class="r">CHG %</th><th class="r">VOLUME</th></tr>
</thead></table>""", unsafe_allow_html=True)

        for q in page_rows:
            sym = clean(q["ticker"])
            pct = q["pct"]
            cc  = "c-pos" if (pct or 0) >= 0 else "c-neg"
            col1, col2, col3, col4 = st.columns([3, 2, 2, 2])
            with col1:
                if st.button(f"{'🟢' if is_bull else '🔴'} {sym}", key=f"btn_{page_key}_{sym}", use_container_width=True):
                    if st.session_state.get("selected_ticker") == sym:
                        st.session_state["selected_ticker"] = None
                        st.session_state["selected_quote"]  = None
                    else:
                        st.session_state["selected_ticker"] = sym
                        st.session_state["selected_quote"]  = q
                    st.rerun()
            with col2:
                st.markdown(f'<div class="c-price" style="padding-top:6px">{fmt_price(q["price"])}</div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="{cc}" style="padding-top:6px">{fmt_pct(pct)}</div>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<div class="c-vol" style="padding-top:6px">{fmt_vol(q.get("volume"))}</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="sc-pg"><span class="pg-info">Showing {start+1}–{min(start+ROWS_PER_PAGE,len(rows))} of {len(rows)}</span></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    _pg_controls(page_key, len(rows))


def render_gap_panel(title, rows, direction, page_key):
    is_up = direction == "UP"
    if page_key not in st.session_state: st.session_state[page_key] = 1
    page  = min(st.session_state[page_key], max(1, (len(rows) + ROWS_PER_PAGE - 1) // ROWS_PER_PAGE))
    start = (page - 1) * ROWS_PER_PAGE
    page_rows = rows[start: start + ROWS_PER_PAGE]

    av_cls    = "av-up"  if is_up else "av-dn"
    panel_cls = "sc-panel-gap-up" if is_up else "sc-panel-gap-dn"
    cnt_cls   = "sc-count-gap-up" if is_up else "sc-count-gap-dn"
    badge     = f"GAP {'UP ▲' if is_up else 'DOWN ▼'} · {len(rows)}"

    st.markdown(f"""<div class="sc-panel {panel_cls}">
  <div class="sc-panel-head">
    <span class="sc-panel-title">{title}</span>
    <span class="sc-count {cnt_cls}">{badge}</span>
  </div>""", unsafe_allow_html=True)

    if not page_rows:
        st.markdown('<div class="sc-empty">NO GAP DATA — FINNHUB KEY REQUIRED FOR ACCURATE OPEN vs PREV CLOSE</div>', unsafe_allow_html=True)
    else:
        gap_cls = "c-gap-up" if is_up else "c-gap-dn"
        st.markdown("""<table class="sc-table"><thead>
<tr><th>SYMBOL</th><th class="r">PREV CLOSE</th><th class="r">OPEN</th><th class="r">GAP %</th><th class="r">DAY CHG %</th><th class="r">VOLUME</th></tr>
</thead></table>""", unsafe_allow_html=True)

        for q in page_rows:
            sym    = clean(q["ticker"])
            pct_cc = "c-pos" if (q["pct"] or 0) >= 0 else "c-neg"
            col1, col2, col3, col4, col5, col6 = st.columns([2, 2, 2, 2, 2, 2])
            with col1:
                if st.button(f"{'▲' if is_up else '▼'} {sym}", key=f"btn_{page_key}_{sym}", use_container_width=True):
                    if st.session_state.get("selected_ticker") == sym:
                        st.session_state["selected_ticker"] = None
                        st.session_state["selected_quote"]  = None
                    else:
                        st.session_state["selected_ticker"] = sym
                        st.session_state["selected_quote"]  = q
                    st.rerun()
            with col2:
                st.markdown(f'<div class="c-price" style="padding-top:6px">{fmt_price(q["prev_close"])}</div>', unsafe_allow_html=True)
            with col3:
                st.markdown(f'<div class="c-price" style="padding-top:6px">{fmt_price(q["open"])}</div>', unsafe_allow_html=True)
            with col4:
                st.markdown(f'<div class="{gap_cls}" style="padding-top:6px">{fmt_pct(q["gap_pct"])}</div>', unsafe_allow_html=True)
            with col5:
                st.markdown(f'<div class="{pct_cc}" style="padding-top:6px">{fmt_pct(q["pct"])}</div>', unsafe_allow_html=True)
            with col6:
                st.markdown(f'<div class="c-vol" style="padding-top:6px">{fmt_vol(q.get("volume"))}</div>', unsafe_allow_html=True)

        st.markdown(f'<div class="sc-pg"><span class="pg-info">Showing {start+1}–{min(start+ROWS_PER_PAGE,len(rows))} of {len(rows)}</span></div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
    _pg_controls(page_key, len(rows))


def render_news_panel(news_items):
    if not news_items:
        body = '<div class="sc-empty">NO NEWS — checking all free sources failed. Add MARKETAUX_API_KEY to secrets for reliable data.</div>'
    else:
        rows_html = ""
        for item in news_items:
            tickers_html = "".join(f'<span class="news-ticker">{t}</span>' for t in item.get("tickers", []))
            h = clean(item["headline"])
            link = item.get("link", "")
            h_html = f'<a class="news-link" href="{link}" target="_blank">{h}</a>' if link else h
            pub = item.get("published", "")
            src = clean(item.get("source", ""))
            meta = f"{src}{' · ' + pub if pub else ''}"
            rows_html += f"""<div class="news-row">
  <div class="news-dot"></div>
  <div class="news-body">
    <div>{tickers_html}</div>
    <div class="news-headline">{h_html}</div>
    <div class="news-meta">{meta}</div>
  </div>
</div>"""
        body = rows_html

    st.markdown(f"""<div class="sc-panel sc-panel-news">
  <div class="sc-panel-head">
    <span class="sc-panel-title">Catalyst News</span>
    <span class="sc-count sc-count-news">{len(news_items)} stories</span>
  </div>{body}</div>""", unsafe_allow_html=True)



# ── options flow ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_options_flow(min_premium=500_000, limit=30):
    """
    Pull unusual options flow via Finnhub unusual activity endpoint,
    falling back to scanning top tickers manually via yfinance.
    """
    items = []

    # Finnhub unusual options activity (requires paid tier — gracefully skipped if not available)
    if FINNHUB_API_KEY:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/stock/option-unusual?token={FINNHUB_API_KEY}",
                timeout=15
            )
            js = r.json() if r.content else {}
            data = js.get("data") or js.get("activity") or []
            for x in data[:limit]:
                sym     = str(x.get("symbol", x.get("ticker", ""))).upper()
                cp      = str(x.get("cp", x.get("type", ""))).upper()
                strike  = x.get("strike") or x.get("strikePrice")
                exp     = str(x.get("exp") or x.get("expirationDate") or "")[:10]
                prem    = x.get("premium") or x.get("totalPremium") or 0
                side    = str(x.get("side") or x.get("aggressor", "")).lower()
                spot    = x.get("spot") or x.get("underlyingPrice") or 0
                dte     = x.get("dte") or 0
                is_sweep = bool(x.get("sweep") or x.get("isSweep"))
                is_block = bool(x.get("block") or x.get("isBlock"))
                if sym and prem >= min_premium:
                    items.append({
                        "sym": sym, "cp": cp[:1], "strike": strike,
                        "exp": exp, "prem": prem, "side": side,
                        "spot": spot, "dte": dte,
                        "sweep": is_sweep, "block": is_block,
                        "time": datetime.now().strftime("%H:%M"),
                    })
            if items:
                return sorted(items, key=lambda x: x["prem"], reverse=True)
        except Exception:
            pass

    # yfinance fallback — scan top tickers for large unusual OI/volume options
    top = ["AAPL","MSFT","NVDA","TSLA","META","AMZN","GOOGL","AMD","SPY","QQQ",
           "JPM","NFLX","BAC","V","XOM","DIS","INTC","PYPL","CRM","UBER"]
    for sym in top:
        try:
            tk   = yf.Ticker(sym)
            info = tk.info or {}
            spot = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            exps = tk.options
            if not exps:
                continue
            exp = exps[0]
            chain = tk.option_chain(exp)
            for df, cp in [(chain.calls, "C"), (chain.puts, "P")]:
                if df is None or df.empty:
                    continue
                df = df.copy()
                df["premium"] = df["lastPrice"] * df["volume"].fillna(0) * 100
                df = df[df["volume"].fillna(0) > 50]
                df = df[df["premium"] >= min_premium]
                for _, row in df.iterrows():
                    vol = int(row.get("volume") or 0)
                    oi  = int(row.get("openInterest") or 1)
                    items.append({
                        "sym": sym, "cp": cp,
                        "strike": row.get("strike"),
                        "exp": exp, "prem": row["premium"],
                        "side": "ask" if vol > oi else "mid",
                        "spot": spot, "dte": 0,
                        "sweep": False, "block": False,
                        "time": datetime.now().strftime("%H:%M"),
                    })
        except Exception:
            continue

    return sorted(items, key=lambda x: x["prem"], reverse=True)[:limit]


def render_options_flow(items, min_prem_filter):
    filtered = [x for x in items if x["prem"] >= min_prem_filter]

    st.markdown(f"""<div class="sc-panel sc-panel-flow">
  <div class="sc-panel-head">
    <span class="sc-panel-title">Options Flow</span>
    <span class="sc-count sc-count-flow">{len(filtered)} trades</span>
  </div>""", unsafe_allow_html=True)

    # Filter bar
    col_a, col_b, col_c, col_d = st.columns([2, 2, 2, 4])
    with col_a:
        cp_filter = st.selectbox("Type", ["All","Calls","Puts"], key="flow_cp", label_visibility="collapsed")
    with col_b:
        side_filter = st.selectbox("Side", ["All","Ask","Bid","Mid"], key="flow_side", label_visibility="collapsed")
    with col_c:
        tag_filter = st.selectbox("Tag", ["All","Sweep","Block"], key="flow_tag", label_visibility="collapsed")

    # Apply filters
    rows = filtered
    if cp_filter == "Calls":  rows = [x for x in rows if x["cp"] == "C"]
    if cp_filter == "Puts":   rows = [x for x in rows if x["cp"] == "P"]
    if side_filter != "All":  rows = [x for x in rows if x["side"].lower() == side_filter.lower()]
    if tag_filter == "Sweep": rows = [x for x in rows if x["sweep"]]
    if tag_filter == "Block": rows = [x for x in rows if x["block"]]

    if not rows:
        st.markdown('<div class="sc-empty">NO FLOW MATCHING FILTERS</div>', unsafe_allow_html=True)
    else:
        st.markdown("""<div class="flow-head">
  <span>SYMBOL</span><span>TYPE</span><span>STRIKE</span><span>EXPIRY</span>
  <span>SIDE</span><span>DTE</span><span>PREMIUM</span><span style="text-align:right">TIME</span>
</div>""", unsafe_allow_html=True)

        rows_html = ""
        for x in rows[:25]:
            cp_cls   = "flow-call" if x["cp"] == "C" else "flow-put"
            cp_label = "CALL" if x["cp"] == "C" else "PUT"
            prem     = x["prem"]
            prem_cls = "flow-prem-lg" if prem >= 1_000_000 else "flow-prem-md"
            prem_str = f"${prem/1_000_000:.2f}M" if prem >= 1_000_000 else f"${prem/1_000:.0f}K"
            side_lbl = x["side"].lower()
            if side_lbl == "ask":   side_html = f'<span class="flow-side-ask">ASK</span>'
            elif side_lbl == "bid": side_html = f'<span class="flow-side-bid">BID</span>'
            else:                   side_html = f'<span class="flow-side-mid">MID</span>'
            tags = ""
            if x.get("sweep"): tags += '<span class="flow-tag-sweep">SWEEP</span>'
            if x.get("block"): tags += '<span class="flow-tag-block">BLOCK</span>'
            exp_short = x["exp"][5:] if len(x["exp"]) >= 7 else x["exp"]
            strike_str = f"${x['strike']:.0f}" if x['strike'] else '—'
            rows_html += f"""<div class="flow-row">
  <span class="flow-sym">{x['sym']}</span>
  <span class="{cp_cls}">{cp_label}</span>
  <span class="flow-strike">{strike_str}</span>
  <span class="flow-exp">{exp_short}</span>
  <span>{side_html}{tags}</span>
  <span class="flow-exp">{x['dte']}d</span>
  <span class="{prem_cls} flow-prem">{prem_str}</span>
  <span class="flow-time">{x['time']}</span>
</div>"""
        st.markdown(rows_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ── volume spikes ─────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_volume_spikes(tickers_tuple):
    tickers = list(tickers_tuple)
    spikes = []
    watchlist = ["AAPL","MSFT","NVDA","TSLA","META","AMZN","GOOGL","AMD","SPY","QQQ",
                 "JPM","NFLX","BAC","V","XOM","DIS","INTC","PYPL","CRM","UBER",
                 "COIN","PLTR","SOFI","MARA","RIOT","GME","AMC","SMCI","ARM","SNOW"]
    all_tickers = list(dict.fromkeys(tickers + watchlist))[:60]

    for t in all_tickers:
        try:
            tk   = yf.Ticker(t)
            info = tk.info or {}
            avg_vol = info.get("averageVolume") or info.get("averageDailyVolume10Day") or 0
            if avg_vol < 500_000:
                continue
            hist = tk.history(period="1d", interval="1m")
            if hist.empty:
                continue
            today_vol = int(hist["Volume"].sum())
            price     = float(hist.iloc[-1]["Close"])
            # Extrapolate to full day (market is 390 min; estimate elapsed)
            now_mins  = (datetime.now().hour * 60 + datetime.now().minute)
            market_open_mins = 9 * 60 + 30
            elapsed   = max(1, now_mins - market_open_mins)
            proj_vol  = int(today_vol * (390 / elapsed)) if elapsed < 390 else today_vol
            ratio     = proj_vol / avg_vol if avg_vol else 0
            if ratio >= 1.5:
                spikes.append({
                    "ticker": t, "price": price,
                    "today_vol": today_vol, "avg_vol": avg_vol,
                    "proj_vol": proj_vol, "ratio": ratio,
                })
        except Exception:
            continue

    return sorted(spikes, key=lambda x: x["ratio"], reverse=True)[:20]


def render_volume_spikes(spikes):
    st.markdown(f"""<div class="sc-panel sc-panel-vol">
  <div class="sc-panel-head">
    <span class="sc-panel-title">Unusual Volume</span>
    <span class="sc-count sc-count-vol">{len(spikes)} spikes</span>
  </div>
  <div class="vol-head">
    <span>SYMBOL</span><span>TODAY VOL</span><span>AVG VOL</span>
    <span>RATIO</span><span style="padding-left:8px">VS AVERAGE</span><span style="text-align:right">PRICE</span>
  </div>""", unsafe_allow_html=True)

    if not spikes:
        st.markdown('<div class="sc-empty">NO UNUSUAL VOLUME DETECTED</div>', unsafe_allow_html=True)
    else:
        rows_html = ""
        for s in spikes:
            ratio     = s["ratio"]
            ratio_cls = "vol-ratio-high" if ratio >= 3 else "vol-ratio-med"
            bar_w     = min(100, int((ratio / 5) * 100))
            rows_html += f"""<div class="vol-row">
  <span class="vol-sym">{s['ticker']}</span>
  <span class="vol-num">{fmt_vol(s['today_vol'])}</span>
  <span class="vol-num">{fmt_vol(s['avg_vol'])}</span>
  <span class="{ratio_cls}">{ratio:.1f}x</span>
  <span><div class="vol-bar-wrap"><div class="vol-bar-fill" style="width:{bar_w}%"></div></div></span>
  <span class="vol-num" style="text-align:right">${fmt_price(s['price'])}</span>
</div>"""
        st.markdown(rows_html, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ── earnings & economics calendar ─────────────────────────────────────────────
@st.cache_data(ttl=3600)
def fetch_earnings_calendar():
    items = []
    today = datetime.now().date()

    # ── 1. Finnhub (best, if key provided) ───────────────────────────────────
    if FINNHUB_API_KEY:
        try:
            from_date = today.strftime("%Y-%m-%d")
            to_date   = (datetime(today.year, today.month + 1, 1) if today.month < 12
                         else datetime(today.year + 1, 1, 1)).strftime("%Y-%m-%d")
            r = requests.get(
                f"https://finnhub.io/api/v1/calendar/earnings?from={from_date}&to={to_date}&token={FINNHUB_API_KEY}",
                timeout=15
            )
            js = r.json() if r.content else {}
            for x in (js.get("earningsCalendar") or [])[:60]:
                sym     = str(x.get("symbol","")).upper()
                date_s  = str(x.get("date",""))
                hour    = str(x.get("hour","")).lower()
                eps_est = x.get("epsEstimate")
                if sym and date_s:
                    items.append({
                        "sym": sym, "date": date_s,
                        "timing": "BMO" if "before" in hour else ("AMC" if "after" in hour else "—"),
                        "eps_est": f"${eps_est:.2f}" if eps_est else "—",
                        "type": "earnings",
                    })
            if items:
                return sorted(items, key=lambda x: x["date"])
        except Exception:
            pass

    # ── 2. Scrape Yahoo Finance earnings calendar (no key needed) ─────────────
    try:
        from bs4 import BeautifulSoup
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        r = requests.get("https://finance.yahoo.com/calendar/earnings", headers=headers, timeout=20)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            # Yahoo renders a table with id="cal-res-table" or class containing "calendar"
            table = (soup.find("table", {"id": "cal-res-table"}) or
                     soup.find("table", class_=re.compile(r"W\(100\%\)")) or
                     soup.find("table"))
            if table:
                for row in table.find_all("tr")[1:]:
                    cols = row.find_all("td")
                    if len(cols) >= 3:
                        sym      = cols[0].get_text(strip=True).upper()
                        company  = cols[1].get_text(strip=True) if len(cols) > 1 else ""
                        date_raw = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                        eps_est  = cols[3].get_text(strip=True) if len(cols) > 3 else "—"
                        timing   = cols[4].get_text(strip=True) if len(cols) > 4 else "—"
                        if not sym or not date_raw:
                            continue
                        # Parse date — Yahoo uses "Apr 18, 2026" or "2026-04-18"
                        date_val = None
                        for fmt in ["%b %d, %Y", "%Y-%m-%d", "%m/%d/%Y"]:
                            try:
                                date_val = datetime.strptime(date_raw[:12].strip(), fmt).date()
                                break
                            except ValueError:
                                continue
                        if date_val and str(date_val) >= str(today):
                            # Normalize EPS
                            if eps_est in ("N/A","--","","None"): eps_est = "—"
                            elif not eps_est.startswith("$"):
                                try: eps_est = f"${float(eps_est):.2f}"
                                except Exception: pass
                            # Normalize timing
                            timing_norm = "BMO" if any(x in timing.lower() for x in ("before","bmo","morning")) \
                                     else "AMC" if any(x in timing.lower() for x in ("after","amc","close")) \
                                     else "—"
                            items.append({
                                "sym": sym[:6], "date": str(date_val),
                                "timing": timing_norm,
                                "eps_est": eps_est,
                                "type": "earnings",
                            })
            if items:
                return sorted(items, key=lambda x: x["date"])[:40]
    except Exception:
        pass

    # ── 3. yfinance earnings_dates (most reliable yfinance method) ───────────
    watchlist = ["AAPL","MSFT","NVDA","TSLA","META","AMZN","GOOGL","AMD","JPM",
                 "NFLX","BAC","V","XOM","DIS","INTC","PYPL","CRM","COIN","PLTR",
                 "UBER","SNAP","SHOP","RBLX","SPOT","ARM","SMCI","MU","QCOM","AVGO"]
    for sym in watchlist:
        try:
            tk = yf.Ticker(sym)
            # earnings_dates is the most reliable in yfinance 0.2+
            try:
                ed = tk.earnings_dates
                if ed is not None and not ed.empty:
                    # Filter to future dates only
                    ed_reset = ed.reset_index()
                    date_col = ed_reset.columns[0]
                    for _, row in ed_reset.iterrows():
                        raw = row[date_col]
                        try:
                            d = raw.date() if hasattr(raw, "date") else datetime.strptime(str(raw)[:10], "%Y-%m-%d").date()
                            if d >= today:
                                eps = row.get("EPS Estimate", row.get("epsEstimate"))
                                eps_str = f"${float(eps):.2f}" if eps and str(eps) not in ("nan","None","") else "—"
                                items.append({"sym": sym, "date": str(d), "timing": "—", "eps_est": eps_str, "type": "earnings"})
                                break  # only take next upcoming date
                        except Exception:
                            continue
                    continue
            except Exception:
                pass

            # Fallback to info dict
            info = tk.info or {}
            for key in ("earningsDate", "earningsTimestamp", "nextEarningsDate"):
                raw = info.get(key)
                if not raw:
                    continue
                try:
                    if isinstance(raw, (int, float)):
                        d = datetime.fromtimestamp(raw).date()
                    elif isinstance(raw, str):
                        d = datetime.strptime(raw[:10], "%Y-%m-%d").date()
                    elif hasattr(raw, "date"):
                        d = raw.date()
                    else:
                        continue
                    if d >= today:
                        eps = info.get("forwardEps")
                        items.append({"sym": sym, "date": str(d), "timing": "—",
                                      "eps_est": f"${eps:.2f}" if eps else "—", "type": "earnings"})
                    break
                except Exception:
                    continue
        except Exception:
            continue

    return sorted(items, key=lambda x: x["date"])[:40]


@st.cache_data(ttl=1800)
def fetch_econ_calendar():
    """Scrape Forex Factory for economic calendar data, fall back to Finnhub."""
    items = []
    today = datetime.now().date()

    # ── 1. Forex Factory scrape ───────────────────────────────────────────────
    try:
        from bs4 import BeautifulSoup
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.forexfactory.com/",
        }
        r = requests.get("https://www.forexfactory.com/calendar", headers=headers, timeout=20)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            table = soup.find("table", class_=re.compile(r"calendar"))
            if not table:
                table = soup.find("table")
            current_date = str(today)
            if table:
                for row in table.find_all("tr", class_=re.compile(r"calendar_row|flexbox")):
                    try:
                        # Date cell — only present on first row of each day
                        date_cell = row.find("td", class_=re.compile(r"date|day"))
                        if date_cell and date_cell.get_text(strip=True):
                            raw_date = date_cell.get_text(strip=True)
                            # FF format: "Mon Apr 15" or "Apr 15"
                            for fmt in ["%a %b %d", "%b %d", "%A %B %d"]:
                                try:
                                    parsed = datetime.strptime(f"{raw_date} {today.year}", f"{fmt} %Y")
                                    current_date = parsed.strftime("%Y-%m-%d")
                                    break
                                except ValueError:
                                    continue

                        # Time
                        time_cell = row.find("td", class_=re.compile(r"time"))
                        time_str  = time_cell.get_text(strip=True) if time_cell else ""

                        # Currency
                        cur_cell  = row.find("td", class_=re.compile(r"currency"))
                        currency  = cur_cell.get_text(strip=True) if cur_cell else ""

                        # Impact — FF uses icon classes: high, medium, low
                        imp_cell  = row.find("td", class_=re.compile(r"impact"))
                        impact    = "LOW"
                        if imp_cell:
                            imp_html = str(imp_cell)
                            if "high" in imp_html.lower():   impact = "HIGH"
                            elif "medium" in imp_html.lower() or "med" in imp_html.lower(): impact = "MED"

                        # Event name
                        ev_cell   = row.find("td", class_=re.compile(r"event"))
                        event     = ev_cell.get_text(strip=True) if ev_cell else ""

                        # Actual / Forecast / Previous
                        act_cell  = row.find("td", class_=re.compile(r"actual"))
                        fore_cell = row.find("td", class_=re.compile(r"forecast"))
                        prev_cell = row.find("td", class_=re.compile(r"previous"))
                        actual    = act_cell.get_text(strip=True)  if act_cell  else "—"
                        forecast  = fore_cell.get_text(strip=True) if fore_cell else "—"
                        previous  = prev_cell.get_text(strip=True) if prev_cell else "—"

                        if event and current_date >= str(today):
                            items.append({
                                "event":    clean(event),
                                "date":     current_date,
                                "time":     time_str or "—",
                                "currency": currency or "USD",
                                "impact":   impact,
                                "estimate": forecast or "—",
                                "actual":   actual   or "—",
                                "previous": previous or "—",
                                "type":     "econ",
                                "source":   "forexfactory",
                            })
                    except Exception:
                        continue

        if items:
            return sorted(items, key=lambda x: (x["date"], x["impact"] != "HIGH", x["currency"] != "USD"))
    except Exception:
        pass

    # ── 2. Finnhub fallback ───────────────────────────────────────────────────
    if FINNHUB_API_KEY:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/calendar/economic?token={FINNHUB_API_KEY}",
                timeout=15
            )
            js = r.json() if r.content else {}
            for x in (js.get("economicCalendar") or [])[:40]:
                event  = clean(x.get("event",""))
                date_s = str(x.get("time",""))[:10]
                impact = str(x.get("impact","")).lower()
                actual = x.get("actual","")
                est    = x.get("estimate","")
                if event and date_s >= str(today):
                    imp_label = "HIGH" if "high" in impact else ("MED" if "medium" in impact or "med" in impact else "LOW")
                    items.append({
                        "event": event, "date": date_s,
                        "time": "—", "currency": "USD",
                        "impact": imp_label,
                        "estimate": str(est) if est else "—",
                        "actual":   str(actual) if actual else "—",
                        "previous": "—",
                        "type": "econ", "source": "finnhub",
                    })
            if items:
                return sorted(items, key=lambda x: (x["date"], x["impact"] != "HIGH"))
        except Exception:
            pass

    # ── 3. Static fallback ────────────────────────────────────────────────────
    fallback = [
        {"event": "FOMC Meeting Minutes", "impact": "HIGH"},
        {"event": "CPI (Core) YoY",       "impact": "HIGH"},
        {"event": "Initial Jobless Claims","impact": "MED"},
        {"event": "Nonfarm Payrolls",      "impact": "HIGH"},
        {"event": "GDP Growth Rate QoQ",   "impact": "HIGH"},
        {"event": "Retail Sales MoM",      "impact": "MED"},
        {"event": "PCE Price Index YoY",   "impact": "HIGH"},
        {"event": "Consumer Confidence",   "impact": "MED"},
        {"event": "ISM Manufacturing PMI", "impact": "MED"},
        {"event": "Fed Chair Speech",      "impact": "HIGH"},
    ]
    for ev in fallback:
        items.append({**ev, "date": str(today), "time": "—", "currency": "USD",
                      "estimate": "—", "actual": "—", "previous": "—",
                      "type": "econ", "source": "static"})
    return items


@st.cache_data(ttl=300)
def fetch_expected_moves(syms):
    """
    For each symbol, calculate expected move from ATM straddle on the
    nearest options expiration. Returns dict: sym -> {move_pct, move_dollar, price, exp}
    """
    results = {}
    for sym in syms:
        try:
            tk    = yf.Ticker(sym)
            info  = tk.info or {}
            price = info.get("currentPrice") or info.get("regularMarketPrice")
            if not price:
                hist  = tk.history(period="1d", interval="1m")
                price = float(hist.iloc[-1]["Close"]) if not hist.empty else None
            if not price:
                continue

            exps = tk.options
            if not exps:
                continue

            # Use nearest expiration
            exp = exps[0]
            chain = tk.option_chain(exp)
            calls = chain.calls
            puts  = chain.puts
            if calls is None or puts is None or calls.empty or puts.empty:
                continue

            # Find ATM strike (closest to current price)
            strikes = calls["strike"].tolist()
            atm_strike = min(strikes, key=lambda s: abs(s - price))

            atm_call = calls[calls["strike"] == atm_strike]
            atm_put  = puts[puts["strike"]  == atm_strike]
            if atm_call.empty or atm_put.empty:
                continue

            call_price = float(atm_call.iloc[0].get("lastPrice", 0) or 0)
            put_price  = float(atm_put.iloc[0].get("lastPrice",  0) or 0)
            straddle   = call_price + put_price

            if straddle <= 0:
                continue

            move_pct    = (straddle / price) * 100
            results[sym] = {
                "move_dollar": straddle,
                "move_pct":    move_pct,
                "price":       price,
                "exp":         exp,
                "straddle":    straddle,
            }
        except Exception:
            continue
    return results


def render_calendar(earnings, econ, expected_moves=None):
    if expected_moves is None:
        expected_moves = {}
    import calendar as cal_lib
    today      = datetime.now().date()
    today_str  = str(today)

    # ── session state ─────────────────────────────────────────────────────────
    if "cal_tab"   not in st.session_state: st.session_state["cal_tab"]   = "earnings"
    if "cal_month" not in st.session_state: st.session_state["cal_month"] = today.month
    if "cal_year"  not in st.session_state: st.session_state["cal_year"]  = today.year

    month = st.session_state["cal_month"]
    year  = st.session_state["cal_year"]

    earn_count = len(earnings)
    econ_high  = len([e for e in econ if e["impact"] == "HIGH"])

    # ── panel header ──────────────────────────────────────────────────────────
    st.markdown(f"""<div class="sc-panel sc-panel-cal">
  <div class="sc-panel-head">
    <span class="sc-panel-title">Earnings &amp; Economics Calendar</span>
    <span class="sc-count sc-count-cal">{earn_count} earnings · {econ_high} high-impact econ</span>
  </div>""", unsafe_allow_html=True)

    # ── tab + month nav row ───────────────────────────────────────────────────
    c_earn, c_econ, c_sp, c_prev, c_month, c_next = st.columns([2, 2, 3, 1, 3, 1])
    with c_earn:
        if st.button("📅 Earnings",  key="tab_earn", use_container_width=True):
            st.session_state["cal_tab"] = "earnings"; st.rerun()
    with c_econ:
        if st.button("🏦 Economics", key="tab_econ", use_container_width=True):
            st.session_state["cal_tab"] = "econ"; st.rerun()
    with c_prev:
        if st.button("‹", key="cal_prev", use_container_width=True):
            m, y = month - 1, year
            if m < 1: m, y = 12, y - 1
            st.session_state["cal_month"] = m
            st.session_state["cal_year"]  = y
            st.rerun()
    with c_month:
        st.markdown(f'<div style="text-align:center;font-family:\'IBM Plex Mono\',monospace;'
                    f'font-size:13px;font-weight:700;color:#e8eaf0;padding-top:6px">'
                    f'{cal_lib.month_name[month]} {year}</div>', unsafe_allow_html=True)
    with c_next:
        if st.button("›", key="cal_next", use_container_width=True):
            m, y = month + 1, year
            if m > 12: m, y = 1, y + 1
            st.session_state["cal_month"] = m
            st.session_state["cal_year"]  = y
            st.rerun()

    tab = st.session_state["cal_tab"]

    # ── build lookup: date_str -> list of items ───────────────────────────────
    if tab == "earnings":
        events_by_date = {}
        for e in earnings:
            events_by_date.setdefault(e["date"], []).append(e)
    else:
        events_by_date = {}
        for e in econ:
            events_by_date.setdefault(e["date"], []).append(e)

    # ── calendar grid CSS ─────────────────────────────────────────────────────
    st.markdown("""<style>
.mcal-wrap { padding: 8px 12px 12px; }
.mcal-dow  {
    display: grid; grid-template-columns: repeat(7, 1fr);
    gap: 3px; margin-bottom: 3px;
}
.mcal-dow span {
    text-align: center; font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; font-weight: 700; letter-spacing: 1px;
    color: #3d4158; text-transform: uppercase; padding: 4px 0;
}
.mcal-grid { display: grid; grid-template-columns: repeat(7, 1fr); gap: 3px; }
.mcal-cell {
    min-height: 90px; background: rgba(255,255,255,.02);
    border: 1px solid rgba(255,255,255,.04); border-radius: 6px;
    padding: 5px 5px 4px; position: relative; overflow: hidden;
    transition: background .15s;
}
.mcal-cell:hover { background: rgba(99,102,241,.06); }
.mcal-cell.today {
    border-color: rgba(99,102,241,.4);
    background: rgba(99,102,241,.07);
}
.mcal-cell.other-month { opacity: .3; }
.mcal-cell.weekend { background: rgba(0,0,0,.15); }
.mcal-day {
    font-family: 'IBM Plex Mono', monospace; font-size: 10px;
    font-weight: 700; color: #4a4e62; margin-bottom: 3px; display: block;
}
.mcal-cell.today .mcal-day {
    color: #fff; background: #6366f1; border-radius: 50%;
    width: 18px; height: 18px; display: inline-flex;
    align-items: center; justify-content: center; font-size: 9px;
}
.mcal-earn {
    display: block; font-family: 'IBM Plex Mono', monospace;
    font-size: 9px; font-weight: 700; padding: 1px 4px;
    border-radius: 3px; margin-bottom: 2px; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis; cursor: default;
}
.mcal-earn.bmo { background: rgba(34,197,94,.15);  color: #4ade80; border: 1px solid rgba(34,197,94,.2); }
.mcal-earn.amc { background: rgba(245,158,11,.12); color: #fcd34d; border: 1px solid rgba(245,158,11,.2); }
.mcal-earn.unk { background: rgba(255,255,255,.06); color: #9ca3af; border: 1px solid rgba(255,255,255,.1); }
.mcal-econ {
    display: block; font-size: 9px; padding: 1px 4px;
    border-radius: 3px; margin-bottom: 2px; white-space: nowrap;
    overflow: hidden; text-overflow: ellipsis;
}
.mcal-econ.high { background: rgba(239,68,68,.12); color: #f87171; border: 1px solid rgba(239,68,68,.2); }
.mcal-econ.med  { background: rgba(245,158,11,.1); color: #fcd34d; border: 1px solid rgba(245,158,11,.18); }
.mcal-econ.low  { background: rgba(255,255,255,.04); color: #6b7280; border: 1px solid rgba(255,255,255,.08); }
.mcal-more { font-size: 8px; color: #4a4e62; font-family: 'IBM Plex Mono', monospace; padding-left: 2px; }
.mcal-legend { display: flex; gap: 14px; padding: 8px 12px 4px; border-top: 1px solid rgba(255,255,255,.04); flex-wrap: wrap; }
.mcal-leg-item { display: flex; align-items: center; gap: 5px; font-family: 'IBM Plex Mono', monospace; font-size: 9px; color: #4a4e62; letter-spacing: .5px; }
.mcal-leg-dot { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }
</style>""", unsafe_allow_html=True)

    # ── build calendar grid ───────────────────────────────────────────────────
    first_weekday, days_in_month = cal_lib.monthrange(year, month)
    # first_weekday: 0=Mon ... 6=Sun, convert to Sun-first
    start_offset = (first_weekday + 1) % 7

    # Previous month overflow days
    if month == 1: prev_year, prev_month = year - 1, 12
    else:          prev_year, prev_month = year, month - 1
    _, prev_days_in_month = cal_lib.monthrange(prev_year, prev_month)

    cells = []
    # Leading empty cells from prev month
    for i in range(start_offset):
        d = prev_days_in_month - start_offset + 1 + i
        cells.append({"day": d, "month": prev_month, "year": prev_year, "other": True})
    # This month
    for d in range(1, days_in_month + 1):
        cells.append({"day": d, "month": month, "year": year, "other": False})
    # Trailing cells from next month
    remainder = (7 - len(cells) % 7) % 7
    for d in range(1, remainder + 1):
        nm = month + 1 if month < 12 else 1
        ny = year if month < 12 else year + 1
        cells.append({"day": d, "month": nm, "year": ny, "other": True})

    # ── render grid HTML ──────────────────────────────────────────────────────
    days_html = ""
    for cell in cells:
        date_str   = f"{cell['year']:04d}-{cell['month']:02d}-{cell['day']:02d}"
        is_today   = date_str == today_str
        is_weekend = datetime.strptime(date_str, "%Y-%m-%d").weekday() >= 5
        cell_cls   = "mcal-cell"
        if is_today:        cell_cls += " today"
        if cell["other"]:   cell_cls += " other-month"
        if is_weekend:      cell_cls += " weekend"

        day_label = f'<span class="mcal-day">{cell["day"]}</span>'

        evs = events_by_date.get(date_str, [])
        ev_html = ""
        max_show = 3
        for ev in evs[:max_show]:
            if tab == "earnings":
                t = ev.get("timing","—")
                cls = "bmo" if t == "BMO" else ("amc" if t == "AMC" else "unk")
                label = ev["sym"]
                eps = ev.get("eps_est","")
                em  = expected_moves.get(label)
                em_str = f" ±{em['move_pct']:.1f}%" if em else ""
                tip = f'{label} | EPS est: {eps}{em_str}'.strip()
                ev_html += f'<span class="mcal-earn {cls}" title="{tip}">{label}{em_str}</span>'
            else:
                imp = ev.get("impact","LOW").lower()
                name = ev.get("event","")[:22]
                ev_title = ev.get("event","")
                ev_html += f'<span class="mcal-econ {imp}" title="{ev_title}">{name}</span>'
        if len(evs) > max_show:
            ev_html += f'<span class="mcal-more">+{len(evs)-max_show} more</span>'

        days_html += f'<div class="{cell_cls}">{day_label}{ev_html}</div>'

    # Legend
    if tab == "earnings":
        legend = """
  <span class="mcal-leg-item"><span class="mcal-leg-dot" style="background:rgba(34,197,94,.3)"></span>BMO — Before Market Open</span>
  <span class="mcal-leg-item"><span class="mcal-leg-dot" style="background:rgba(245,158,11,.3)"></span>AMC — After Market Close</span>
  <span class="mcal-leg-item"><span class="mcal-leg-dot" style="background:rgba(255,255,255,.1)"></span>Unknown timing</span>"""
    else:
        ff_src = econ[0].get("source","") if econ else ""
        ff_badge = ('&nbsp;·&nbsp;<a href="https://www.forexfactory.com/calendar" target="_blank" '
                    'style="color:#f59e0b;text-decoration:none;font-weight:700">🏭 Forex Factory ↗</a>'
                    if ff_src == "forexfactory" else "")
        legend = f"""
  <span class="mcal-leg-item"><span class="mcal-leg-dot" style="background:rgba(239,68,68,.4)"></span>HIGH impact</span>
  <span class="mcal-leg-item"><span class="mcal-leg-dot" style="background:rgba(245,158,11,.4)"></span>MED impact</span>
  <span class="mcal-leg-item"><span class="mcal-leg-dot" style="background:rgba(255,255,255,.15)"></span>LOW impact</span>
  <span class="mcal-leg-item" style="margin-left:auto">{ff_badge}</span>"""

    st.markdown(f"""<div class="mcal-wrap">
  <div class="mcal-dow">
    <span>Sun</span><span>Mon</span><span>Tue</span><span>Wed</span><span>Thu</span><span>Fri</span><span>Sat</span>
  </div>
  <div class="mcal-grid">{days_html}</div>
</div>
<div class="mcal-legend">{legend}</div>
</div>""", unsafe_allow_html=True)

    # ── selected day detail (earnings only) ───────────────────────────────────
    if tab == "earnings" and earnings:
        today_earns = events_by_date.get(today_str, [])
        upcoming = [e for e in earnings if e.get("date","") >= today_str and e.get("sym")][:5]
        if upcoming:
            st.markdown('<div style="padding:10px 12px 0"><div class="sc-section" style="margin-top:0">Upcoming Earnings</div></div>', unsafe_allow_html=True)
            # Header
            st.markdown("""<div style="display:grid;grid-template-columns:70px 70px 1fr 100px 100px;
  gap:0;padding:6px 14px;border-bottom:1px solid rgba(255,255,255,.04);background:rgba(0,0,0,.2)">
  <span style="font-family:'IBM Plex Mono',monospace;font-size:8px;font-weight:700;letter-spacing:1.5px;color:#2e3148;text-transform:uppercase">DATE</span>
  <span style="font-family:'IBM Plex Mono',monospace;font-size:8px;font-weight:700;letter-spacing:1.5px;color:#2e3148;text-transform:uppercase">SYMBOL</span>
  <span style="font-family:'IBM Plex Mono',monospace;font-size:8px;font-weight:700;letter-spacing:1.5px;color:#2e3148;text-transform:uppercase">EPS EST</span>
  <span style="font-family:'IBM Plex Mono',monospace;font-size:8px;font-weight:700;letter-spacing:1.5px;color:#2e3148;text-transform:uppercase;text-align:right">EXP MOVE</span>
  <span style="font-family:'IBM Plex Mono',monospace;font-size:8px;font-weight:700;letter-spacing:1.5px;color:#2e3148;text-transform:uppercase;text-align:right">TIMING</span>
</div>""", unsafe_allow_html=True)
            rows_html = ""
            for e in upcoming:
                d         = e["date"]
                date_disp = "TODAY" if d == today_str else datetime.strptime(d, "%Y-%m-%d").strftime("%b %d")
                date_cls  = "cal-today" if d == today_str else "cal-date"
                timing    = e.get("timing","—")
                tim_cls   = "cal-bmo" if timing == "BMO" else ("cal-amc" if timing == "AMC" else "")
                sym       = e["sym"]

                # Expected move
                em = expected_moves.get(sym)
                if em:
                    move_pct = em["move_pct"]
                    move_dol = em["move_dollar"]
                    # Color by size: >10% red, 5-10% amber, <5% gray
                    em_color = "#f87171" if move_pct >= 10 else ("#fcd34d" if move_pct >= 5 else "#9ca3af")
                    em_str   = f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:11px;font-weight:700;color:{em_color}">±{move_pct:.1f}%</span>'
                    em_sub   = f'<span style="font-family:\'IBM Plex Mono\',monospace;font-size:9px;color:#4a4e62"> (±${move_dol:.2f})</span>'
                    em_html  = em_str + em_sub
                else:
                    em_html  = '<span style="font-family:\'IBM Plex Mono\',monospace;font-size:10px;color:#3d4158">—</span>'

                rows_html += f"""<div style="display:grid;grid-template-columns:70px 70px 1fr 100px 100px;
  gap:0;padding:8px 14px;border-bottom:1px solid rgba(255,255,255,.03);align-items:center">
  <span class="{date_cls}" style="font-family:'IBM Plex Mono',monospace;font-size:10px">{date_disp}</span>
  <span class="cal-sym">{sym}</span>
  <span class="cal-est" style="color:#6b7280">{e.get('eps_est','—')}</span>
  <span style="text-align:right">{em_html}</span>
  <span class="cal-timing {tim_cls}" style="text-align:right">{timing}</span>
</div>"""
            st.markdown(rows_html, unsafe_allow_html=True)
            # Expected move explainer
            st.markdown("""<div style="padding:8px 14px;font-family:'IBM Plex Mono',monospace;
font-size:9px;color:#3d4158;border-top:1px solid rgba(255,255,255,.03);letter-spacing:.3px">
⚡ EXP MOVE = ATM straddle price on nearest expiry · what options market prices in for earnings day move
</div>""", unsafe_allow_html=True)


# ── market index summary bar ──────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_index_bar():
    indices = [("SPY","S&P 500"),("QQQ","NASDAQ"),("IWM","RUSSELL 2K"),("GLD","GOLD"),("TLT","BONDS")]
    results = []
    for sym, label in indices:
        try:
            tk = yf.Ticker(sym)
            hist = tk.history(period="2d", interval="1d")
            if len(hist) >= 2:
                close = float(hist.iloc[-1]["Close"])
                prev  = float(hist.iloc[-2]["Close"])
                pct   = (close - prev) / prev * 100
                results.append((label, close, pct))
            elif len(hist) == 1:
                results.append((label, float(hist.iloc[-1]["Close"]), 0.0))
        except Exception:
            pass
    return results

index_data = fetch_index_bar()

def _mkt_item(label, val, pct):
    chg_cls = "sc-mkt-chg-pos" if pct >= 0 else "sc-mkt-chg-neg"
    arrow   = "▲" if pct >= 0 else "▼"
    return f"""<div class="sc-mkt-item">
  <div class="sc-mkt-label">{label}</div>
  <div class="sc-mkt-val">{val:,.2f}</div>
  <div class="{chg_cls}">{arrow} {abs(pct):.2f}%</div>
</div>"""

mkt_bar_html = "".join(_mkt_item(l, v, p) for l, v, p in index_data)


# ── main ──────────────────────────────────────────────────────────────────────
if "selected_ticker" not in st.session_state:
    st.session_state["selected_ticker"] = None
    st.session_state["selected_quote"]  = None

now_str = datetime.now().strftime("%b %d, %Y  %H:%M:%S")

with st.spinner("Fetching universe…"):
    tickers = fetch_universe()

with st.spinner("Fetching live quotes…"):
    quotes = fetch_quotes(tickers)

with st.spinner("Fetching catalyst news…"):
    news = fetch_news()

valid     = [q for q in quotes if q["price"] is not None and q["pct"] is not None]
bull      = sorted([q for q in valid if (q["pct"] or 0) >= 0], key=lambda x: x["pct"], reverse=True)
bear      = sorted([q for q in valid if (q["pct"] or 0) <  0], key=lambda x: x["pct"])
gap_valid = [q for q in valid if q.get("gap_pct") is not None]
gap_up    = sorted([q for q in gap_valid if q["gap_pct"] >= GAP_THRESHOLD],  key=lambda x: x["gap_pct"], reverse=True)
gap_dn    = sorted([q for q in gap_valid if q["gap_pct"] <= -GAP_THRESHOLD], key=lambda x: x["gap_pct"])

with st.spinner("Fetching options flow…"):
    flow_items = fetch_options_flow()

with st.spinner("Scanning volume spikes…"):
    vol_spikes = fetch_volume_spikes(tuple(tickers))

with st.spinner("Loading calendar…"):
    earnings_cal = fetch_earnings_calendar()
    econ_cal     = fetch_econ_calendar()

# Expected moves for upcoming earnings tickers
earnings_cal = earnings_cal or []
econ_cal     = econ_cal     or []

try:
    _today_str = str(datetime.now().date())
    _upcoming_syms = tuple(list(dict.fromkeys(
        e.get("sym") for e in earnings_cal
        if e.get("sym") and e.get("date","") >= _today_str
    ))[:15])
except Exception:
    _upcoming_syms = ()

with st.spinner("Fetching expected moves…"):
    expected_moves = fetch_expected_moves(_upcoming_syms)

# ── render ────────────────────────────────────────────────────────────────────
st.markdown('<div class="sc-wrap">', unsafe_allow_html=True)
st.markdown(f"""<div class="sc-header">
  <div class="sc-logo">MS</div>
  <div>
    <div class="sc-title">Market Scanner</div>
    <div class="sc-sub">Live · S&amp;P 500 + Broad Market</div>
  </div>
  <div class="sc-divider"></div>
  <span class="sc-timestamp">🕐 {now_str}</span>
</div>
<div class="sc-mkt-bar">{mkt_bar_html}</div>
""", unsafe_allow_html=True)

# Ticker detail panel — always shown at top when a ticker is selected
if st.session_state.get("selected_ticker"):
    st.markdown('<div class="sc-section">Ticker Detail</div>', unsafe_allow_html=True)
    render_ticker_detail(st.session_state["selected_ticker"], st.session_state["selected_quote"] or {})

# ── tabs ──────────────────────────────────────────────────────────────────────
tab_scans, tab_gaps, tab_flow, tab_volume, tab_calendar, tab_news = st.tabs([
    "📈  Scans",
    "⚡  Gappers",
    "🔥  Options Flow",
    "📊  Volume",
    "📅  Calendar",
    "📰  News",
])

with tab_scans:
    st.markdown('<div class="sc-section">Bullish &amp; Bearish Scans</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1: render_scan_panel("Bullish Scans", bull, "BULL", "bull_page")
    with c2: render_scan_panel("Bearish Scans", bear, "BEAR", "bear_page")

with tab_gaps:
    st.markdown('<div class="sc-section">Daily Gappers</div>', unsafe_allow_html=True)
    c3, c4 = st.columns(2)
    with c3: render_gap_panel("Gappers Up",   gap_up, "UP", "gap_up_page")
    with c4: render_gap_panel("Gappers Down", gap_dn, "DN", "gap_dn_page")

with tab_flow:
    st.markdown('<div class="sc-section">Options Flow</div>', unsafe_allow_html=True)
    min_prem = st.select_slider(
        "Min Premium",
        options=[250_000, 500_000, 1_000_000, 2_000_000, 5_000_000],
        value=500_000,
        format_func=lambda x: f"${x/1_000_000:.1f}M" if x >= 1_000_000 else f"${x//1_000}K",
        key="flow_min_prem",
        label_visibility="collapsed",
    )
    render_options_flow(flow_items, min_prem)

with tab_volume:
    st.markdown('<div class="sc-section">Unusual Volume</div>', unsafe_allow_html=True)
    render_volume_spikes(vol_spikes)

with tab_calendar:
    st.markdown('<div class="sc-section">Earnings &amp; Economics Calendar</div>', unsafe_allow_html=True)
    render_calendar(earnings_cal, econ_cal, expected_moves)

with tab_news:
    st.markdown('<div class="sc-section">Catalyst News</div>', unsafe_allow_html=True)
    render_news_panel(news)

st.markdown('</div>', unsafe_allow_html=True)
