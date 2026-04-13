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
.neutral {background:#121921; color:#b5c0cf; bor
