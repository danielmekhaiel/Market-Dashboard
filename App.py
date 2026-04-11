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
.block-container {padding:0.8rem 1rem 1rem 1rem; max-width:1500px;}
html, body, [class*="css"] {background:#050607; color:#f2f4f8;}
header, footer, #MainMenu {visibility:hidden;}
[data-testid="stSidebar"] {background:#0b0f14; border-right:1px solid #1d2733;}
.topbar {display:flex; justify-content:space-between; align-items:center; background:linear-gradient(180deg,#0f1620,#0b0f14); border:1px solid #1f2a36; border-radius:14px; padding:14px 16px; margin-bottom:12px;}
.brand {font-size:1.2rem; font-weight:800; letter-spacing:.12em;}
.subtle {color:#93a1b2; font-size:.82rem;}
.card {background:#0b0f14; border:1px solid #1f2a36; border-radius:14px; overflow:hidden; margin-bottom:12px;}
.card-h {padding:10px 12px; border-bottom:1px solid #1f2a36; display:flex; justify-content:space-between; align-items:center; background:#0f1620;}
.card-t {font-size:.74rem; text-transform:uppercase; letter-spacing:.14em; color:#9db0c6; font-weight:800;}
.card-b {padding:8px 12px 10px 12px;}
.row {display:grid; grid-template-columns:72px 126px 78px 84px 1fr; gap:10px; align-items:center; padding:8px 0; border-top:1px solid #16202c;}
.row:first-child {border-top:none;}
.sym {font-weight:900; color:#ffffff;}
.sector {color:#aab6c4; font-size:.82rem;}
.badge {display:inline-flex; align-items:center; justify-content:center; padding:3px 8px; border-radius:999px; font-size:.64rem; font-weight:800; letter-spacing:.08em; border:1px solid transparent; white-space:nowr
