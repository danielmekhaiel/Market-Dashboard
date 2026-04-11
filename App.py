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

st.markdown(
    """
<style>
.block-container {padding-top: 1rem; max-width: 1280px;}
html, body, [class*="css"] {background:#000000; color:#f5f5f5;}
.small-muted {color:#8a8a8a; font-size:0.88rem;}
.section-card {background:#111111; border:1px solid #222222; border-radius:14px; padding:12px 14px; margin-bottom:12px;}
.list-head {display:flex; gap:10px; color:#8f8f8f; font-size:0.68rem; text-transform:uppercase; letter-spacing:.09em; padding:0 8px 6px 8px;}
.list-row {display:flex; gap:10px; align-items:center; padding:8px 8px; border-top:1px solid #202020;}
.list-row:first-child {border-top:none;}
.sym {width:68px; font-weight:800; color:#ffffff; font-size:.92rem;}
.sector {width:200px; color:#c9c9c9; font-size:.85rem;}
.thesis {width:78px; font-weight:700; font-size:.72rem;}
.importance {width:92px; font-size:.72rem; font-weight:700;}
.headline {flex:1; color:#f3f3f3; font-size:.88rem; line-height:1.25;}
.badge {display:inline-block; padding:2px 7px; border-radius:999px; font-size:.64rem; font-weight:800; letter-spacing:.04em;}
.badge.bullish {background:rgba(34,197,94,.12); color:#22c55e; border:1px solid #22c55e;}
.badge.bearish {background:rgba(239,68,68,.12); color:#ef4444; border:1px solid #ef4444;}
.badge.neutral {background:#1a1a1a; color:#9ca3af; border:1px solid #333333;}
.badge.notable {background:rgba(245,158,11,.10); color:#f59e0b; border:1px solid #f59e0b;}
.badge.moderate {background:#1a1a1a; color:#c9c9c9; border:1px solid #333333;}
.badge.high {b
