"""
HisseLab — v11.0  (Hybrid Chart Architecture + Timeframes + Ghost Sort Headers)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. CHARTS  : Dashboard → TradingView Advanced Widget (iframe)
             Backtest  → streamlit-lightweight-charts (AL/SAT markers)
2. TIMEFRAMES: 1m/5m/15m/30m/1h/4h/1d/1wk/1mo with auto period cap
3. SORT HEADERS: Ghost tertiary buttons as table column headers
4. LWC: Ichimoku cloud fill improved, volume scaleMargins 0.85
5. SIDEBAR: Slogan replaces indicator list, tighter padding
"""

import json, os, base64, io
import streamlit as st
import streamlit.components.v1 as _stc
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
from datetime import datetime
from typing import Optional
from PIL import Image as _PIL

# ── TradingView Lightweight Charts ──────────────────────────────────────────
try:
    from streamlit_lightweight_charts import renderLightweightCharts
    _LWC_AVAILABLE = True
except ImportError:
    _LWC_AVAILABLE = False   # graceful fallback to Plotly

try:
    from dotenv import load_dotenv; load_dotenv()
except ImportError: pass

import requests as _req

# ── Timeframe definitions ────────────────────────────────────────────────────
# Each entry: (display_label, yfinance_interval, max_yfinance_period)
TIMEFRAMES = [
    ("1 Dakika",   "1m",  "7d"),
    ("5 Dakika",   "5m",  "60d"),
    ("15 Dakika",  "15m", "60d"),
    ("30 Dakika",  "30m", "60d"),
    ("1 Saat",     "1h",  "730d"),
    ("4 Saat",     "4h",  "730d"),
    ("1 Gün",      "1d",  "5y"),
    ("1 Hafta",    "1wk", "10y"),
    ("1 Ay",       "1mo", "20y"),
]
TF_LABELS   = [t[0] for t in TIMEFRAMES]
TF_INTERVAL = {t[0]: t[1] for t in TIMEFRAMES}
TF_PERIOD   = {t[0]: t[2] for t in TIMEFRAMES}
TF_DEFAULT  = "1 Gün"

def tf_selectbox(key: str, label: str = "Zaman Dilimi", default: str = TF_DEFAULT) -> tuple[str, str]:
    """Render timeframe selectbox. Returns (interval, period)."""
    try:   idx = TF_LABELS.index(default)
    except: idx = 6   # 1 Gün fallback
    chosen = st.selectbox(label, TF_LABELS, index=idx, key=key, label_visibility="collapsed")
    return TF_INTERVAL[chosen], TF_PERIOD[chosen]

# ─────────────────────────────────────────────────────────────────────────────
# ICON  (base64 for sidebar HTML embedding)
# ─────────────────────────────────────────────────────────────────────────────
def _load_icon_b64() -> str:
    try:
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png")
        with open(icon_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except FileNotFoundError:
        return ""
    except Exception as e:
        print(f"[WARN] Icon encoding failed: {e}")
        return ""

ICON_B64 = _load_icon_b64()

try:
    _pil_icon = _PIL.open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "icon.png"))
except FileNotFoundError:
    _pil_icon = "📈"
except Exception as e:
    print(f"[WARN] PIL icon load failed: {e}")
    _pil_icon = "📈"

# ─────────────────────────────────────────────────────────────────────────────
# SUPABASE
# ─────────────────────────────────────────────────────────────────────────────
def get_supabase():
    url = os.getenv("SUPABASE_URL",""); key = os.getenv("SUPABASE_KEY","")
    if not url or not key: return None
    try:
        from supabase import create_client
        return create_client(url, key)
    except Exception as e:
        print(f"[WARN] Supabase init failed: {e}. Running in demo mode.")
        return None

SUPABASE = get_supabase()

# ─────────────────────────────────────────────────────────────────────────────
# SYMBOL HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def display_sym(s: str) -> str:
    """ASELS.IS → ASELS   (UI only, API calls still use full symbol)"""
    for sfx in (".IS",".DE",".L",".PA",".MI",".AS"):
        if s.upper().endswith(sfx): return s[:-len(sfx)]
    return s

def api_sym(display: str, suffix: str = ".IS") -> str:
    """ASELS → ASELS.IS   (reverse of display_sym for BIST)"""
    if "." in display: return display          # already has suffix
    return display + suffix

# ─────────────────────────────────────────────────────────────────────────────
# BIST SYMBOLS  — İş Yatırım primary, large static fallback
# ─────────────────────────────────────────────────────────────────────────────
_BIST_STATIC = [
    "A1CAP","ACSEL","ADEL","ADESE","ADGYO","AEFES","AFYON","AGESA","AGYO","AHGAZ",
    "AKBNK","AKCNS","AKFGY","AKFYE","AKGRT","AKMGY","AKPAZ","AKSGY","AKSUE","AKYHO",
    "ALARK","ALBRK","ALGYO","ALKA","ALKIM","ALMAD","ALTINS","ALTNY","ALVES","ALYAG",
    "ANELE","ANGEN","ANHYT","ANSGR","ARASE","ARBUL","ARDYZ","ARENA","ARSAN","ASELS",
    "ASLAN","ASTOR","ATAGY","ATAKP","ATEKS","AVISA","AVOD","AYGAZ","AZTEK","BAGFS",
    "BAKAB","BALAT","BANVT","BASGZ","BAYRK","BERA","BEYAZ","BIENY","BIMAS","BJKAS",
    "BLCYT","BMEKS","BNTAS","BOBET","BOSSA","BRYAT","BUCIM","BURCE","BURVA","BVSAN",
    "CCOLA","CELHA","CEMAS","CEMTS","CIMSA","CLEBI","CMBTN","CMENT","CONSE","COSMO",
    "CRFSA","CUSAN","DAGI","DAPGM","DARDL","DENGE","DERIM","DESA","DEVA","DGATE",
    "DGNMO","DITAS","DMSAS","DNISI","DOAS","DOBUR","DOGUB","DOHOL","DOKTA","DYOBY",
    "DZGYO","ECILC","ECZYT","EDATA","EGEEN","EGEPO","EGPRO","EGSER","EKGYO","ELITE",
    "EMKEL","EMNIS","ENKAI","ERCB","EREGL","ERSU","ESCAR","ESCOM","ESEN","ETILR",
    "ETYAT","EUHOL","EUPWR","EUREN","FAVORI","FENER","FLAP","FONET","FORTE","FROTO",
    "FZLGY","GARAN","GARFA","GEREL","GESAN","GILDI","GLBMD","GLRYH","GLYHO","GMTAS",
    "GOKNUR","GOLTS","GOODY","GOZDE","GSDDE","GSDHO","GSRAY","GUBRF","GWIND","HATEK",
    "HEKTS","HLGYO","HTTBT","HUBVC","HUNER","HURGZ","ICBCT","IDGYO","IEYHO","IHAAS",
    "IHEVA","IHGZT","IHLAS","IHLGM","IHYAY","IMASM","INDES","INFO","INGRM","INTEM",
    "IPEKE","ISATR","ISCTR","ISFIN","ISGSY","ISGYO","ISYAT","ITTFK","IZENR","IZFAS",
    "IZINV","IZMDC","JANTS","KAPLM","KARTN","KAYSE","KBORU","KCAER","KCHOL","KENT",
    "KERVN","KFEIN","KGYO","KLGYO","KLKIM","KLMSN","KLNMA","KLRHO","KMPUR","KNFRT",
    "KONKA","KONTR","KONYA","KOPOL","KORDS","KOZAA","KOZAL","KRDMA","KRDMB","KRDMD",
    "KRVGD","KSTUR","KTLEV","KUTPO","KUVVA","KUYAS","LINK","LKMNH","LOGO","LRSHO",
    "LUKSK","LYDHO","MAALT","MAGEN","MAKIM","MANAS","MARBL","MARTI","MAVI","MEDTR",
    "MEGAP","MEPET","MERCN","MERKO","METRO","METUR","MIATK","MIPAZ","MMCAS","MNDRS",
    "MNGYO","MOBTL","MPARK","MRGYO","MSGYO","MTRKS","MTRYO","MULGA","MUTLU","NATEN",
    "NETAS","NIBAS","NILFA","NUGYO","NUHCM","NWSA","OBAMS","OBASE","ODAS","ODINE",
    "OFSYM","ONCSM","ORCAY","ORGE","ORION","ORKLD","OSMEN","OSTIM","OTKAR","OYAKC",
    "OYAYO","OYLUM","OZGYO","OZKGY","PAGYO","PAPIL","PARSN","PASEU","PCILT","PEKGY",
    "PENGD","PENTA","PETKM","PETUN","PGSUS","PINSU","PKENT","PLTUR","PNLSN","POLHO",
    "POLTK","PRDAX","PRFBK","PRKAB","PRKME","PRZMA","PSDTC","PTOFS","QNBFB","QNBFL",
    "RALYH","RAYSG","RHEAG","RTALB","RUBNS","RYGYO","RZGYO","SAFGY","SAGYO","SAHOL",
    "SANEL","SANFM","SANKO","SASA","SAYAS","SDTTR","SEKFK","SEKUR","SELEC","SELGD",
    "SELVA","SEYKM","SILVR","SISE","SKBNK","SKTAS","SMART","SNGYO","SNPAM","SOKM",
    "SRVGY","SUWEN","TABGD","TATGD","TAVHL","TBORG","TCELL","TDGYO","TEKTU","TETMT",
    "THYAO","TKFEN","TKNSA","TKURU","TLMAN","TMPOL","TMSN","TNZTP","TOASO","TRCAS","TRGYO",
    "TRILC","TSKB","TTKOM","TTRAK","TUCLK","TUDDF","TUPRS","TUREX","TURGG","TURSG",
    "ULUFA","ULUSE","ULYMO","UMPAS","UNLU","USAK","UTPYA","UZERB","VAKBN","VAKFN",
    "VAKKO","VBTS","VERTU","VESBE","VESTL","VKFYO","VKGYO","WFGYO","YAPRK","YATAS",
    "YESIL","YETKN","YGGYO","YKBNK","YKSLN","YKSGR","YUNSA","YYAPI","ZEDUR","ZOREN","ZORLU",
]
_BIST_FALLBACK = sorted({t+".IS" for t in _BIST_STATIC})

@st.cache_data(ttl=86400, show_spinner=False)
def fetch_bist_categorised() -> dict:
    hdrs = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://www.isyatirim.com.tr/"}

    def to_ticker(raw):
        t = raw.strip().upper().replace(" ","")
        for s in (".IS",".E",":IS"): t = t[:-len(s)] if t.endswith(s) else t
        return (t+".IS") if t and t.isalpha() and 2<=len(t)<=8 else None

    for url in [
        "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/HisseGosterim",
        "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/HisseSenetleriListe",
        "https://www.isyatirim.com.tr/api/Data/GetEquityScreenerData?exchange=XIST&fields=CODE,MARKET",
    ]:
        try:
            r = _req.get(url, headers=hdrs, timeout=12)
            if r.status_code != 200: continue
            raw_data = r.json()
            items = raw_data if isinstance(raw_data, list) else (
                raw_data.get("value") or raw_data.get("data") or raw_data.get("Data") or [])
            if not isinstance(items, list) or len(items) < 10: continue
            cats: dict = {}
            for row in items:
                code = str(row.get("code") or row.get("CODE") or
                           row.get("ticker") or row.get("TICKER") or "")
                market = str(row.get("market") or row.get("MARKET") or
                             row.get("pazar") or row.get("PAZAR") or "").upper()
                tk = to_ticker(code)
                if not tk: continue
                if any(k in market for k in ["YILD","STAR"]): key = "BIST Yıldız Pazar"
                elif any(k in market for k in ["ANA","MAIN"]): key = "BIST Ana Pazar"
                elif any(k in market for k in ["ALT","SUB"]):  key = "BIST Alt Pazar"
                else: key = "BIST Ana Pazar"
                cats.setdefault(key, []).append(tk)
            cats = {k: sorted(set(v)) for k, v in cats.items() if v}
            if cats:
                cats["BIST Tüm Hisseler"] = sorted({t for v in cats.values() for t in v})
                return cats
        except Exception as e:
            print(f"[DEBUG] BIST category parsing failed: {e}")
            continue

    return {"BIST Tüm Hisseler": _BIST_FALLBACK}

STATIC_MARKETS = {
    "🪙 Kripto (USD)": ["BTC-USD","ETH-USD","BNB-USD","SOL-USD","XRP-USD",
                         "ADA-USD","AVAX-USD","DOGE-USD","DOT-USD","MATIC-USD",
                         "LINK-USD","UNI-USD","LTC-USD","ATOM-USD","TRX-USD"],
    "🇺🇸 S&P 500": ["AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA",
                     "BRK-B","JPM","V","UNH","XOM","JNJ","PG","MA",
                     "HD","CVX","MRK","ABBV","LLY"],
    "🇩🇪 DAX": ["SAP.DE","SIE.DE","ALV.DE","MRK.DE","DTE.DE",
                 "BMW.DE","MBG.DE","BAYN.DE","BAS.DE","VOW3.DE"],
    "🥇 Emtia / ETF": ["GC=F","SI=F","CL=F","NG=F","ZW=F","SPY","QQQ","GLD","SLV","USO"],
}

def get_markets() -> dict:
    bist = fetch_bist_categorised()
    emap = {"BIST Yıldız Pazar":"⭐ BIST Yıldız Pazar","BIST Ana Pazar":"🇹🇷 BIST Ana Pazar",
            "BIST Alt Pazar":"📋 BIST Alt Pazar","BIST Tüm Hisseler":"🏦 BIST Tüm Hisseler",
            "🏦 BIST Tüm Hisseler":"🏦 BIST Tüm Hisseler"}
    result = {}
    for k in ["BIST Yıldız Pazar","BIST Ana Pazar","BIST Alt Pazar",
              "BIST Tüm Hisseler","🏦 BIST Tüm Hisseler"]:
        if k in bist:
            dk = emap.get(k, k)
            if dk not in result: result[dk] = bist[k]
    result.update(STATIC_MARKETS)
    return result

PAGE_SIZE = 15

# ─────────────────────────────────────────────────────────────────────────────
# INDICATOR DEFINITIONS  — 20 professional indicators
# ─────────────────────────────────────────────────────────────────────────────
IND_META = {
    # ── Oscillators ──────────────────────────────────────────────────────────
    "RSI": {
        "category": "oscillator", "label": "RSI — Relative Strength Index",
        "params": [("period",int,14,2,200)],
        "conditions": [">","<",">=","<=","Yukarı Kesen","Aşağı Kesen"],
        "cross_targets": ["30","50","70"],
    },
    "MACD": {
        "category": "oscillator", "label": "MACD — Moving Avg Convergence",
        "params": [("fast",int,12,2,100),("slow",int,26,2,200),("signal",int,9,2,100)],
        "conditions": [">","<",">=","<=","Yukarı Kesen (Signal)","Aşağı Kesen (Signal)","Sıfırı Yukarı Kesti","Sıfırı Aşağı Kesti"],
        "cross_targets": [],
    },
    "Stochastic": {
        "category": "oscillator", "label": "Stochastic Oscillator (%K/%D)",
        "params": [("k_period",int,14,1,100),("d_period",int,3,1,50),("smooth",int,3,1,20)],
        "conditions": [">","<","Yukarı Kesen","Aşağı Kesen","Aşırı Alım (>80)","Aşırı Satım (<20)"],
        "cross_targets": [],
    },
    "ADX": {
        "category": "oscillator", "label": "ADX — Average Directional Index",
        "params": [("period",int,14,2,100)],
        "conditions": [">","<",">=","<="],
        "cross_targets": [],
    },
    "CCI": {
        "category": "oscillator", "label": "CCI — Commodity Channel Index",
        "params": [("period",int,20,5,200)],
        "conditions": [">","<","Yukarı Kesen","Aşağı Kesen"],
        "cross_targets": ["100","-100","0"],
    },
    "Williams %R": {
        "category": "oscillator", "label": "Williams %R",
        "params": [("period",int,14,2,100)],
        "conditions": [">","<","Aşırı Alım (>-20)","Aşırı Satım (<-80)"],
        "cross_targets": [],
    },
    "MFI": {
        "category": "oscillator", "label": "MFI — Money Flow Index",
        "params": [("period",int,14,2,100)],
        "conditions": [">","<","Yukarı Kesen","Aşağı Kesen"],
        "cross_targets": ["20","80"],
    },
    "ROC": {
        "category": "oscillator", "label": "ROC — Rate of Change (%)",
        "params": [("period",int,12,1,200)],
        "conditions": [">","<","Sıfırı Yukarı Kesti","Sıfırı Aşağı Kesti"],
        "cross_targets": [],
    },
    "OBV": {
        "category": "oscillator", "label": "OBV — On-Balance Volume",
        "params": [],
        "conditions": ["Artıyor","Azalıyor"],
        "cross_targets": [],
    },
    # ── Overlays ─────────────────────────────────────────────────────────────
    "SMA": {
        "category": "overlay", "label": "SMA — Simple Moving Average",
        "params": [("period",int,20,2,500)],
        "conditions": ["Fiyat Üstünde","Fiyat Altında","Yukarı Kesti","Aşağı Kesti"],
        "cross_targets": [],
    },
    "EMA": {
        "category": "overlay", "label": "EMA — Exponential Moving Average",
        "params": [("period",int,20,2,500)],
        "conditions": ["Fiyat Üstünde","Fiyat Altında","Yukarı Kesti","Aşağı Kesti"],
        "cross_targets": [],
    },
    "Bollinger": {
        "category": "overlay", "label": "Bollinger Bands",
        "params": [("period",int,20,2,200),("std_dev",float,2.0,0.5,5.0)],
        "conditions": ["Fiyat Üst Band Üstünde","Fiyat Alt Band Altında",
                       "Üst Bandı Yukarı Kesti","Alt Bandı Aşağı Kesti","%B > 1","%B < 0"],
        "cross_targets": [],
    },
    "Ichimoku": {
        "category": "overlay", "label": "Ichimoku Cloud",
        "params": [("tenkan",int,9,5,50),("kijun",int,26,10,100),("senkou_b",int,52,20,200)],
        "conditions": ["Fiyat Bulut Üstünde","Fiyat Bulut Altında",
                       "Tenkan Kijun'u Yukarı Kesti","Tenkan Kijun'u Aşağı Kesti"],
        "cross_targets": [],
    },
    "VWAP": {
        "category": "overlay", "label": "VWAP — Volume Weighted Avg Price",
        "params": [],
        "conditions": ["Fiyat VWAP Üstünde","Fiyat VWAP Altında",
                       "VWAP'ı Yukarı Kesti","VWAP'ı Aşağı Kesti"],
        "cross_targets": [],
    },
    "ATR": {
        "category": "overlay", "label": "ATR — Average True Range",
        "params": [("period",int,14,2,100)],
        "conditions": [">","<"],
        "cross_targets": [],
    },
    "Parabolic SAR": {
        "category": "overlay", "label": "Parabolic SAR",
        "params": [("step",float,0.02,0.01,0.1),("max_step",float,0.2,0.1,0.5)],
        "conditions": ["SAR Fiyatın Altında (Yükseliş)","SAR Fiyatın Üstünde (Düşüş)",
                       "SAR Yön Değiştirdi (Yukarı)","SAR Yön Değiştirdi (Aşağı)"],
        "cross_targets": [],
    },
    "Keltner": {
        "category": "overlay", "label": "Keltner Channel",
        "params": [("period",int,20,5,100),("atr_mult",float,2.0,1.0,4.0)],
        "conditions": ["Fiyat Üst Kanal Üstünde","Fiyat Alt Kanal Altında",
                       "Üst Kanalı Yukarı Kesti","Alt Kanalı Aşağı Kesti"],
        "cross_targets": [],
    },
    "Donchian": {
        "category": "overlay", "label": "Donchian Channel",
        "params": [("period",int,20,5,200)],
        "conditions": ["Yeni 20-Bar Yüksek","Yeni 20-Bar Düşük",
                       "Orta Bandın Üstünde","Orta Bandın Altında"],
        "cross_targets": [],
    },
    "Aroon": {
        "category": "oscillator", "label": "Aroon Oscillator",
        "params": [("period",int,25,5,100)],
        "conditions": [">","<","Yukarı Kesen","Aşağı Kesen"],
        "cross_targets": ["0","50","-50"],
    },
    "Ultimate": {
        "category": "oscillator", "label": "Ultimate Oscillator",
        "params": [("p1",int,7,2,50),("p2",int,14,2,100),("p3",int,28,5,200)],
        "conditions": [">","<","Yukarı Kesen","Aşağı Kesen"],
        "cross_targets": ["30","50","70"],
    },
}

IND_NAMES = list(IND_META.keys())
OVERLAY_INDS  = [k for k,v in IND_META.items() if v["category"]=="overlay"]
OSC_INDS      = [k for k,v in IND_META.items() if v["category"]=="oscillator"]

# ─────────────────────────────────────────────────────────────────────────────
# THEME
# ─────────────────────────────────────────────────────────────────────────────
DEFAULT_THEME = {
    "accent":"#00d4ff","accent_rgb":"0,212,255",
    "bg_primary":"#080c14","bg_card":"#111827","border":"#1e2d45","font_size":"15",
}
def get_theme(): return st.session_state.get("theme", DEFAULT_THEME.copy())

# ─────────────────────────────────────────────────────────────────────────────
# PAGE CONFIG — FIRST STREAMLIT CALL
# ─────────────────────────────────────────────────────────────────────────────
st.set_page_config(page_title="HisseLab", page_icon=_pil_icon,
                   layout="wide", initial_sidebar_state="expanded")

# ─────────────────────────────────────────────────────────────────────────────
# CSS
# ─────────────────────────────────────────────────────────────────────────────
def inject_css():
    t = get_theme()
    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Sora:wght@300;400;500;600&display=swap');
:root{{
    --bg:{t['bg_primary']};--card:{t['bg_card']};--hover:#1a2235;--brd:{t['border']};
    --acc:{t['accent']};--acc-rgb:{t['accent_rgb']};
    --grn:#00e676;--red:#ff4757;--gld:#ffd700;
    --txt:#e8f0fe;--txt2:#8ba3c9;--muted:#4a6080;--fs:{t['font_size']}px;
}}
html,body,.stApp{{background:var(--bg)!important;font-family:'Sora',sans-serif;font-size:var(--fs);}}
/* Zero wasted vertical space */
.main .block-container{{
    padding:0rem 1.4rem 0.8rem!important;
    max-width:1440px!important;
}}
.block-container{{padding-top:0!important;}}
[data-testid="stSidebar"]+div{{padding-top:0!important;}}
/* Kill Streamlit's default element spacing */
.element-container{{margin-bottom:0!important;}}
[data-testid="stVerticalBlock"]>div:empty{{display:none!important;}}
/* st.divider slim */
[data-testid="stDivider"]{{margin:0.2rem 0!important;}}
h1,h2,h3,h4{{font-family:'Space Mono',monospace!important;color:var(--txt)!important;margin:0 0 .4rem!important;}}
/* Remove top padding injected by Streamlit in wide mode */
section[data-testid="stSidebar"]+div>div:first-child{{padding-top:0!important;margin-top:0!important;}}
[data-testid="stStatusWidget"]{{display:none!important;}}
[data-testid="stSidebar"]{{background:linear-gradient(180deg,#080c14,#0a1020)!important;
    border-right:1px solid var(--brd)!important;min-width:230px!important;max-width:260px!important;}}
[data-testid="collapsedControl"],[data-testid="stSidebarCollapseButton"],
[data-testid="stSidebarCollapseButton"] button,
button[data-testid="stBaseButton-headerNoPadding"],
button[aria-label="Close sidebar"],button[aria-label="Open sidebar"]{{display:none!important;}}
[data-testid="stSidebar"] *{{color:var(--txt2);}}
[data-testid="stSidebar"] .stRadio label{{color:var(--txt2)!important;font-size:.86rem;
    padding:.3rem .4rem;border-radius:6px;transition:all .15s;}}
[data-testid="stSidebar"] .stRadio label:hover{{color:var(--txt)!important;background:rgba(255,255,255,.05);}}
/* sidebar locked */
.sh{{display:flex;align-items:center;gap:.55rem;padding:.25rem 0;
    border-bottom:none!important;
    margin-bottom:0!important;
    padding-bottom:0!important;}}
.sh-dot{{width:7px;height:7px;border-radius:50%;background:var(--acc);box-shadow:0 0 6px var(--acc);}}
.sh h3{{margin:0;font-size:.88rem;letter-spacing:.07em;
    color:var(--txt)!important;font-family:'Space Mono',monospace!important;}}
.sh + div{{margin-top:-20px!important;}}
.mc{{background:var(--card);border:1px solid var(--brd);border-radius:11px;
    padding:.9rem 1.1rem;position:relative;overflow:hidden;margin-bottom:.6rem;transition:border-color .2s;}}
.mc:hover{{border-color:var(--acc);}}
.mc::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
    background:linear-gradient(90deg,var(--acc),transparent);}}
.mc-lbl{{font-size:.62rem;letter-spacing:.12em;text-transform:uppercase;
    color:var(--muted);font-family:'Space Mono',monospace;margin-bottom:.25rem;}}
.mc-val{{font-size:1.35rem;font-weight:700;font-family:'Space Mono',monospace;color:var(--txt);line-height:1.2;}}
.mc-sub{{font-size:.65rem;color:var(--muted);margin-top:.15rem;}}
.mc-blue .mc-val{{color:var(--acc);}} .mc-green .mc-val{{color:var(--grn);}}
.mc-red  .mc-val{{color:var(--red);}} .mc-gold  .mc-val{{color:var(--gld);}}
/* tbl rows: now st.columns-based, mb-tbl removed */
.stButton>button{{
    background:linear-gradient(135deg,rgba(var(--acc-rgb),.12),rgba(var(--acc-rgb),.06));
    border:1px solid var(--acc);color:var(--acc);
    font-family:'Space Mono',monospace;font-size:.74rem;
    letter-spacing:.07em;border-radius:8px;padding:.45rem 1.1rem;
    transition:all .2s;text-transform:uppercase;}}
.stButton>button:hover{{
    background:linear-gradient(135deg,rgba(var(--acc-rgb),.26),rgba(var(--acc-rgb),.13));
    box-shadow:0 0 14px rgba(var(--acc-rgb),.22);}}
.green-btn>button{{
    background:linear-gradient(135deg,rgba(0,230,118,.12),rgba(0,230,118,.06))!important;
    border-color:var(--grn)!important;color:var(--grn)!important;
    width:100%;padding:.65rem!important;}}
/* Default tertiary: ✖ delete button (red icon) */
[data-testid="stButton"] button[kind="tertiary"]{{
    background:transparent!important;border:none!important;
    color:rgba(255,71,87,.7)!important;padding:0 4px!important;
    font-size:.85rem!important;min-height:unset!important;height:20px!important;
    box-shadow:none!important;text-transform:none!important;
    letter-spacing:0!important;line-height:1!important;}}
[data-testid="stButton"] button[kind="tertiary"]:hover{{
    color:var(--red)!important;background:rgba(255,71,87,.08)!important;}}
/* ── Sort header buttons: ALL tertiary buttons white (global) ── */
/* This targets ALL tertiary buttons sitewide so no wrapper div needed */
[data-testid="stButton"] button[kind="tertiary"] p {{
    color:#ffffff!important;
    font-size:0.72rem!important;
    margin-bottom:0!important;
}}
[data-testid="stButton"] button[kind="tertiary"] {{
    color:#ffffff!important;
    font-size:0.72rem!important;
    font-family:'Space Mono',monospace!important;
    text-transform:uppercase!important;
    letter-spacing:.08em!important;
    background:transparent!important;
    border:none!important;
    border-bottom:1px solid var(--brd)!important;
    border-radius:0!important;
    padding:3px 2px!important;
    height:auto!important;
    min-height:unset!important;
    box-shadow:none!important;
    width:100%!important;
    text-align:left!important;
    font-weight:500!important;
    line-height:1.2!important;
    margin-bottom:0!important;
}}
[data-testid="stButton"] button[kind="tertiary"]:hover {{
    color:var(--acc)!important;
    background:transparent!important;
    border-bottom-color:var(--acc)!important;
}}
/* Sayfalama rakamlarının alt alta kaymasını engeller */
[data-testid="stButton"] button,
[data-testid="stButton"] button p {{
    white-space:nowrap!important;
}}
/* Sayfalama butonları — ortalanmış, kompakt */
.pagination-row [data-testid="stButton"] button,
.pagination-row [data-testid="stButton"] button[kind="secondary"] {{
    padding:0.15rem 0.35rem!important;
    min-width:28px!important;
    height:auto!important;
    min-height:unset!important;
    display:flex!important;
    justify-content:center!important;
    align-items:center!important;
    text-align:center!important;
    white-space:nowrap!important;
    font-size:0.65rem!important;
    line-height:1.4!important;
}}
/* İçinde kırmızı çarpı (tertiary buton) olan tüm satırların boşluğunu sıfırlar */
.element-container:has(button[kind="tertiary"]) {{
    margin-top:0!important;
    margin-bottom:0!important;
}}
/* Table row cells */
.tbl-row-cell{{
    padding:.24rem 0 .24rem .1rem;
    border-bottom:1px solid #0d1421;
    margin:0!important;
    line-height:1;
}}
.element-container:has(.tbl-row-cell){{
    margin-top:0!important;margin-bottom:0!important;
}}
/* ── Indicator multiselect — modern pill design ── */
.stMultiSelect>div>div{{
    background:linear-gradient(135deg,rgba(13,20,33,.95),rgba(17,24,39,.9))!important;
    border:1px solid var(--brd)!important;
    border-radius:10px!important;
    min-height:40px!important;
    box-shadow:inset 0 1px 3px rgba(0,0,0,.3)!important;
    transition:border-color .2s,box-shadow .2s!important;}}
.stMultiSelect>div>div:hover{{
    border-color:rgba(var(--acc-rgb),.4)!important;}}
.stMultiSelect>div>div:focus-within{{
    border-color:var(--acc)!important;
    box-shadow:0 0 0 1px rgba(var(--acc-rgb),.35),inset 0 1px 3px rgba(0,0,0,.3)!important;}}
/* Selected tags = glowing pills */
.stMultiSelect span[data-baseweb="tag"]{{
    background:linear-gradient(135deg,rgba(var(--acc-rgb),.25),rgba(var(--acc-rgb),.1))!important;
    border:1px solid rgba(var(--acc-rgb),.55)!important;
    color:var(--acc)!important;
    font-size:.67rem!important;
    font-family:'Space Mono',monospace!important;
    border-radius:5px!important;
    padding:2px 7px!important;
    letter-spacing:.04em!important;
    box-shadow:0 0 4px rgba(var(--acc-rgb),.15)!important;}}
.stMultiSelect span[data-baseweb="tag"] span{{
    color:var(--acc)!important;opacity:.65;}}
.stMultiSelect [data-baseweb="input"]{{
    background:transparent!important;}}
/* Dropdown list items */
[data-baseweb="menu"] li{{
    background:var(--card)!important;color:var(--txt2)!important;
    font-size:.78rem!important;}}
[data-baseweb="menu"] li:hover{{
    background:rgba(var(--acc-rgb),.1)!important;color:var(--txt)!important;}}
/* Toggle */
.stToggle label{{color:var(--txt2)!important;font-size:.75rem!important;}}
.stToggle [data-baseweb="checkbox"] div{{background:var(--acc)!important;}}
/* Inputs */
.stTextInput>div>div>input,.stSelectbox>div>div>div,.stNumberInput>div>div>input{{
    background:var(--card)!important;border:1px solid var(--brd)!important;
    color:var(--txt)!important;border-radius:8px!important;
    font-family:'Space Mono',monospace!important;}}
.sig-alert{{background:linear-gradient(135deg,rgba(0,230,118,.08),rgba(0,230,118,.03));
    border:1px solid var(--grn);border-radius:10px;padding:.9rem 1.3rem;
    margin:.6rem 0;animation:pulse 2s infinite;}}
@keyframes pulse{{0%,100%{{box-shadow:0 0 5px rgba(0,230,118,.2);}}50%{{box-shadow:0 0 14px rgba(0,230,118,.5);}}}}
.sig-title{{color:var(--grn);font-family:'Space Mono',monospace;font-size:.83rem;font-weight:700;}}
.sig-body{{color:var(--txt2);font-size:.8rem;margin-top:.25rem;}}
.live-badge{{display:inline-flex;align-items:center;gap:5px;
    background:rgba(0,230,118,.08);border:1px solid var(--grn);border-radius:20px;padding:2px 9px;
    font-size:.65rem;font-family:'Space Mono',monospace;color:var(--grn);
    text-transform:uppercase;letter-spacing:.1em;}}
.ldot{{width:5px;height:5px;border-radius:50%;background:var(--grn);animation:blink 1.2s infinite;}}
@keyframes blink{{0%,100%{{opacity:1;}}50%{{opacity:.15;}}}}
.logo{{padding:.3rem 0 .9rem 0;text-align:center;}}
.logo-inner{{display:flex;align-items:center;justify-content:center;gap:.5rem;}}
.logo-img{{width:26px;height:26px;border-radius:6px;object-fit:contain;}}
.logo-t{{font-family:'Space Mono',monospace;font-size:1rem;color:var(--acc);letter-spacing:.16em;}}
.logo-s{{font-size:.54rem;color:var(--muted);letter-spacing:.14em;text-transform:uppercase;margin-top:2px;}}
hr{{border-color:var(--brd)!important;margin:1rem 0!important;}}
::-webkit-scrollbar{{width:4px;}}::-webkit-scrollbar-track{{background:var(--bg);}}
::-webkit-scrollbar-thumb{{background:var(--brd);border-radius:4px;}}
#MainMenu,footer,header{{visibility:hidden;}}.stDeployButton{{display:none;}}
.param-box{{background:rgba(0,212,255,.04);border:1px solid rgba(0,212,255,.15);
    border-radius:8px;padding:.75rem .9rem;margin-top:.4rem;}}
/* ── Bot Status Card ── */
.bot-card{{background:var(--card);border:1px solid var(--brd);border-radius:12px;
    padding:.75rem 1rem;margin-bottom:.5rem;transition:border-color .2s;}}
.bot-card:hover{{border-color:rgba(var(--acc-rgb),.4);}}
.bot-card-sym{{color:var(--acc);font-family:'Space Mono',monospace;
    font-size:.85rem;font-weight:700;}}
.bot-card-ind{{color:var(--txt2);font-size:.76rem;margin:.15rem 0;}}
.bot-card-cond{{color:var(--gld);font-size:.72rem;font-family:'Space Mono',monospace;}}
/* ── Terminal Log ── */
.terminal{{background:#020914;border:1px solid #1a3a1a;border-radius:8px;
    padding:.7rem .9rem;font-family:'Space Mono',monospace;font-size:.72rem;
    color:#00e676;line-height:1.7;max-height:240px;overflow-y:auto;
    box-shadow:inset 0 0 20px rgba(0,230,118,.03);}}
.terminal .t-ts{{color:#2a6b2a;}}
.terminal .t-trig{{color:#00e676;font-weight:700;}}
.terminal .t-none{{color:#1d5c3a;}}
/* ── Paper Trading Card ── */
.paper-card{{background:linear-gradient(135deg,rgba(var(--acc-rgb),.08),rgba(var(--acc-rgb),.03));
    border:1px solid rgba(var(--acc-rgb),.25);border-radius:12px;padding:.9rem 1.2rem;
    margin-bottom:.6rem;}}
.paper-bal{{font-family:'Space Mono',monospace;font-size:1.2rem;
    color:var(--acc);font-weight:700;letter-spacing:.06em;}}
.paper-lbl{{font-size:.6rem;color:var(--muted);text-transform:uppercase;
    letter-spacing:.12em;margin-bottom:.2rem;font-family:'Space Mono',monospace;}}
/* ── Trade Journal Table ── */
.tj-tbl{{width:100%;border-collapse:collapse;font-family:'Space Mono',monospace;font-size:.72rem;}}
.tj-tbl th{{color:var(--muted);font-size:.6rem;text-transform:uppercase;
    letter-spacing:.1em;padding:.35rem .5rem;border-bottom:1px solid var(--brd);text-align:left;}}
.tj-tbl td{{padding:.32rem .5rem;border-bottom:1px solid #0a1525;}}
.tj-win{{color:#00e676;}} .tj-loss{{color:#ff4757;}}
.tj-buy{{color:var(--acc);}} .tj-sell{{color:var(--muted);}}
/* ── Lightweight Charts container — visible border + subtle glow ── */
.lwc-frame{{
    border:1px solid #2e4a70!important;
    border-radius:8px!important;
    overflow:hidden!important;
    box-shadow:0 0 0 1px rgba(46,74,112,.6),
               0 2px 16px rgba(0,0,0,.35)!important;
    margin-top:.3rem!important;
}}
.lwc-frame iframe{{
    border-radius:8px!important;
    display:block!important;
}}
.sort-btn-row{{display:flex;gap:6px;margin-bottom:.4rem;}}
.sort-badge{{background:var(--card);border:1px solid var(--brd);border-radius:6px;
    padding:2px 8px;font-size:.62rem;font-family:'Space Mono',monospace;
    color:var(--txt2);cursor:pointer;}}
.sort-badge.active{{border-color:var(--acc);color:var(--acc);}}
</style>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGINATION — Sliding Window  [‹][1][...][6][7][8][...][20][›]
# Dynamic st.columns — NEVER overflows, never a fixed array length
# ─────────────────────────────────────────────────────────────────────────────
def _pagination_slots(pg: int, n_pg: int) -> list:
    """
    Build the ordered slot list for sliding-window pagination.
    Each element is either an int (0-based page index) or '...' (ellipsis).

    Examples (0-based):
      n=20, pg=6  → [0, '...', 5, 6, 7, '...', 19]
      n=20, pg=1  → [0, 1, 2, '...', 19]
      n=5,  pg=2  → [0, 1, 2, 3, 4]
    """
    if n_pg <= 7:
        return list(range(n_pg))

    first, last = 0, n_pg - 1
    window = {pg - 2, pg - 1, pg, pg + 1, pg + 2}     # neighbours of current page
    always = {first, last}
    visible = sorted(always | {p for p in window if 0 <= p < n_pg})

    slots: list = []
    prev = -1
    for p in visible:
        if p - prev > 2:
            slots.append("...")        # gap > 1 → ellipsis
        elif p - prev == 2:
            slots.append(prev + 1)    # gap == 1 → insert the missing page
        slots.append(p)
        prev = p
    return slots


def render_pagination(pg: int, n_pg: int, pg_key: str):
    if n_pg <= 1:
        return

    slots = _pagination_slots(pg, n_pg)
    # Build column widths: arrows narrow, numbers normal, ellipsis very narrow
    col_ws = [0.45]  # ‹
    for s in slots:
        col_ws.append(0.28 if s == "..." else 0.52)
    col_ws.append(0.45)  # ›

    cols = st.columns(col_ws)   # exactly len(slots)+2 columns — never overflows
    dot_html = '<div style="text-align:center;color:var(--muted);font-family:\'Space Mono\',monospace;font-size:.7rem;padding-top:6px;">…</div>'

    # ‹ prev
    with cols[0]:
        if st.button("‹", key=f"{pg_key}_prev", disabled=(pg == 0)):
            st.session_state[pg_key] = pg - 1; st.rerun()

    # Slots
    for i, slot in enumerate(slots):
        with cols[i + 1]:
            if slot == "...":
                st.markdown(dot_html, unsafe_allow_html=True)
            else:
                lbl = f"**{slot + 1}**" if slot == pg else str(slot + 1)
                if st.button(lbl, key=f"{pg_key}_p{slot}"):
                    st.session_state[pg_key] = slot; st.rerun()

    # › next
    with cols[len(slots) + 1]:
        if st.button("›", key=f"{pg_key}_next", disabled=(pg >= n_pg - 1)):
            st.session_state[pg_key] = pg + 1; st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# AUTOCOMPLETE SELECTBOX — displays clean symbols, returns API symbols
# ─────────────────────────────────────────────────────────────────────────────
def sym_selectbox(label: str, options: list[str], key: str,
                  default: str = "ASELS.IS") -> str:
    """
    Shows display labels (no .IS), returns the raw API symbol with suffix.
    options: list of API symbols (e.g. ["ASELS.IS", "THYAO.IS"])
    """
    display_options = [display_sym(s) for s in options]
    # Find default index
    default_display = display_sym(default)
    try:
        idx = display_options.index(default_display)
    except ValueError:
        idx = 0
    chosen_display = st.selectbox(label, display_options, index=idx, key=key)
    # Map back to API symbol
    try:
        pos = display_options.index(chosen_display)
        return options[pos]
    except ValueError:
        return options[0] if options else default


# ─────────────────────────────────────────────────────────────────────────────
# BATCH QUOTE FETCH — for global sorting in market browser
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_batch_quotes(symbols: tuple) -> dict:
    """
    Stage-1: yf.download batch (fast).
    Stage-2: ThreadPoolExecutor for still-missing symbols (zero blanks).
    Returns {sym: {"price": float, "change": float}} for every symbol.
    """
    import concurrent.futures

    result: dict = {}
    if not symbols:
        return result
    ticker_str = " ".join(symbols)

    # ── Stage 1: bulk download ────────────────────────────────────────────────
    def _parse_close(raw, syms):
        if raw is None or raw.empty: return None
        if isinstance(raw.columns, pd.MultiIndex):
            lvl0 = raw.columns.get_level_values(0)
            if "Close" not in lvl0: return None
            return raw["Close"]
        if "Close" not in raw.columns: return None
        close = raw[["Close"]].copy()
        if len(syms) == 1:
            close.columns = [syms[0]]
        return close

    for period in ("5d", "10d", "1mo"):
        try:
            raw = yf.download(
                ticker_str, period=period,
                auto_adjust=True, progress=False,
                threads=True, show_errors=False,
                group_by="ticker"
            )
            close = _parse_close(raw, symbols)
            if close is None:
                continue
            for sym in symbols:
                if sym in result:
                    continue
                col = sym if sym in close.columns else None
                if col is None:
                    continue
                s = close[col].dropna()
                if len(s) < 2:
                    continue
                p  = float(s.iloc[-1])
                pv = float(s.iloc[-2])
                result[sym] = {"price": p, "change": (p - pv) / pv * 100}
            if len(result) >= len(symbols) * 0.80:
                break
        except Exception:
            continue

    # ── Stage 2: parallel single-ticker fallback for still-missing ────────────
    missing = [s for s in symbols if s not in result or result[s].get("price") is None]
    if missing:
        def _single(sym: str) -> tuple:
            for period in ("5d", "1mo", "3mo"):
                try:
                    h = yf.Ticker(sym).history(period=period)
                    if h.empty:
                        continue
                    h = h.dropna(subset=["Close"])
                    if len(h) < 2:
                        # last resort: use fast_info for latest price only
                        fi = yf.Ticker(sym).fast_info
                        p = float(getattr(fi, "last_price", None) or 0)
                        if p > 0:
                            return sym, {"price": p, "change": 0.0}
                        continue
                    p  = float(h["Close"].iloc[-1])
                    pv = float(h["Close"].iloc[-2])
                    return sym, {"price": p, "change": (p - pv) / (pv if pv != 0 else 1e-10) * 100}
                except Exception:
                    continue
            return sym, {"price": None, "change": None}

        max_workers = min(32, len(missing))
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
            for sym, q in ex.map(_single, missing):
                if q.get("price") is not None:
                    result[sym] = q

    return result


@st.cache_data(ttl=120, show_spinner=False)
def fetch_quick_quote(symbol: str) -> dict:
    """Single-ticker quote with period fallback (5d → 1mo → fast_info)."""
    for period in ("5d", "1mo"):
        try:
            h = yf.Ticker(symbol).history(period=period)
            if h.empty: continue
            h = h.dropna(subset=["Close"])
            if len(h) < 2: continue
            p  = float(h["Close"].iloc[-1])
            pv = float(h["Close"].iloc[-2])
            return {"price": p, "change": (p - pv) / (pv if pv != 0 else 1e-10) * 100}
        except Exception as e:
            print(f"[DEBUG] Historical price fetch failed for {symbol}: {e}")
            continue
    # Last resort: fast_info (no change available)
    try:
        p = float(yf.Ticker(symbol).fast_info.last_price or 0)
        if p > 0: return {"price": p, "change": 0.0}
    except Exception as e:
        print(f"[DEBUG] fast_info fetch failed for {symbol}: {e}")
    return {"price": None, "change": None}


# ─────────────────────────────────────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def fetch_price_data(symbol, period="1y", interval="1d") -> Optional[pd.DataFrame]:
    try:
        df = yf.Ticker(symbol).history(period=period, interval=interval)
        if df.empty: return None
        df.index = pd.to_datetime(df.index)
        # Duplicate zaman damgalarını temizle, sırala ve boş verileri at
        df = df[~df.index.duplicated(keep='last')].sort_index()
        df = df.dropna(subset=["Open", "High", "Low", "Close", "Volume"])
        return df
    except Exception as e:
        print(f"[WARN] fetch_price_data({symbol}): {e}")
        return None

@st.cache_data(ttl=300, show_spinner=False)
def fetch_ticker_info(symbol) -> dict:
    try:
        return yf.Ticker(symbol).info or {}
    except Exception as e:
        print(f"[WARN] fetch_ticker_info({symbol}): {e}")
        return {}


# ─────────────────────────────────────────────────────────────────────────────
# INDICATOR CALCULATIONS — 20 indicators
# ─────────────────────────────────────────────────────────────────────────────
def calc_rsi(s,p=14):
    d=s.diff(); g=d.clip(lower=0); l=-d.clip(upper=0)
    return 100-(100/(1+g.ewm(com=p-1,min_periods=p).mean()/l.ewm(com=p-1,min_periods=p).mean()))

def calc_sma(s,p): return s.rolling(p).mean()
def calc_ema(s,p): return s.ewm(span=p,adjust=False).mean()

def calc_macd(s,fast=12,slow=26,signal=9):
    ml=s.ewm(span=fast,adjust=False).mean()-s.ewm(span=slow,adjust=False).mean()
    sl=ml.ewm(span=signal,adjust=False).mean()
    return ml,sl,ml-sl

def calc_bb(s,p=20,sd=2.0):
    m=s.rolling(p).mean(); sig=s.rolling(p).std()
    return m+sd*sig,m,m-sd*sig

def calc_atr(df,p=14):
    h=df["High"]; l=df["Low"]; c=df["Close"]
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    return tr.ewm(span=p,adjust=False).mean()

def calc_stoch(df,k_p=14,d_p=3,smooth=3):
    lo=df["Low"].rolling(k_p).min(); hi=df["High"].rolling(k_p).max()
    k=(df["Close"]-lo)/(hi-lo+1e-10)*100
    k_sm=k.rolling(smooth).mean()
    d=k_sm.rolling(d_p).mean()
    return k_sm,d

def calc_adx(df,p=14):
    h=df["High"]; l=df["Low"]; c=df["Close"]
    tr=pd.concat([h-l,(h-c.shift()).abs(),(l-c.shift()).abs()],axis=1).max(axis=1)
    dm_p=(h-h.shift()).clip(lower=0); dm_m=(l.shift()-l).clip(lower=0)
    dm_p=dm_p.where(dm_p>dm_m,0); dm_m=dm_m.where(dm_m>dm_p,0)
    atr=tr.ewm(span=p,adjust=False).mean()
    di_p=100*dm_p.ewm(span=p,adjust=False).mean()/atr
    di_m=100*dm_m.ewm(span=p,adjust=False).mean()/atr
    dx=(di_p-di_m).abs()/(di_p+di_m+1e-10)*100
    return dx.ewm(span=p,adjust=False).mean()

def calc_cci(df,p=20):
    tp=(df["High"]+df["Low"]+df["Close"])/3
    ma=tp.rolling(p).mean()
    md=tp.rolling(p).apply(lambda x:(x-x.mean()).abs().mean(),raw=True)
    return (tp-ma)/(0.015*md+1e-10)

def calc_willr(df,p=14):
    hi=df["High"].rolling(p).max(); lo=df["Low"].rolling(p).min()
    return (hi-df["Close"])/(hi-lo+1e-10)*-100

def calc_mfi(df,p=14):
    tp=(df["High"]+df["Low"]+df["Close"])/3
    rmf=tp*df["Volume"]
    pos=rmf.where(tp>tp.shift(),0); neg=rmf.where(tp<tp.shift(),0)
    mfr=pos.rolling(p).sum()/neg.rolling(p).sum().replace(0,1e-10)
    return 100-(100/(1+mfr))

def calc_roc(s,p=12): return (s-s.shift(p))/s.shift(p).replace(0,1e-10)*100

def calc_obv(df):
    direction=df["Close"].diff().apply(lambda x:1 if x>0 else (-1 if x<0 else 0))
    return (direction*df["Volume"]).cumsum()

def calc_vwap(df):
    tp=(df["High"]+df["Low"]+df["Close"])/3
    vc=df["Volume"].cumsum().replace(0,1e-10)
    return (tp*df["Volume"]).cumsum()/vc

def calc_psar(df,step=0.02,max_step=0.2):
    close=df["Close"].values; high=df["High"].values; low=df["Low"].values
    n=len(close); psar=np.zeros(n); bull=True
    ep=low[0]; af=step; psar[0]=high[0]
    for i in range(1,n):
        psar[i]=psar[i-1]+af*(ep-psar[i-1])
        if bull:
            psar[i]=min(psar[i],low[i-1],low[max(0,i-2)])
            if low[i]<psar[i]: bull=False; psar[i]=ep; ep=low[i]; af=step
            else:
                if high[i]>ep: ep=high[i]; af=min(af+step,max_step)
        else:
            psar[i]=max(psar[i],high[i-1],high[max(0,i-2)])
            if high[i]>psar[i]: bull=True; psar[i]=ep; ep=high[i]; af=step
            else:
                if low[i]<ep: ep=low[i]; af=min(af+step,max_step)
    return pd.Series(psar,index=df.index)

def calc_ichimoku(df,tenkan=9,kijun=26,senkou_b=52):
    ten=(df["High"].rolling(tenkan).max()+df["Low"].rolling(tenkan).min())/2
    kij=(df["High"].rolling(kijun).max()+df["Low"].rolling(kijun).min())/2
    span_a=((ten+kij)/2).shift(kijun)
    span_b=((df["High"].rolling(senkou_b).max()+df["Low"].rolling(senkou_b).min())/2).shift(kijun)
    chikou=df["Close"].shift(-kijun)
    return ten,kij,span_a,span_b,chikou

def calc_keltner(df,p=20,atr_mult=2.0):
    mid=calc_ema(df["Close"],p)
    atr=calc_atr(df,p)
    return mid+atr_mult*atr, mid, mid-atr_mult*atr

def calc_donchian(df,p=20):
    hi=df["High"].rolling(p).max(); lo=df["Low"].rolling(p).min()
    return hi,(hi+lo)/2,lo

def calc_aroon(df,p=25):
    hi_idx=df["High"].rolling(p+1).apply(lambda x:x.argmax(),raw=True)
    lo_idx=df["Low"].rolling(p+1).apply(lambda x:x.argmin(),raw=True)
    aroon_up=(p-hi_idx)/p*100; aroon_dn=(p-lo_idx)/p*100
    return aroon_up-aroon_dn

def calc_ultimate(df,p1=7,p2=14,p3=28):
    c=df["Close"]; l=df["Low"]; h=df["High"]
    pc=c.shift(); bp=c-pd.concat([l,pc],axis=1).min(axis=1)
    tr=pd.concat([h,pc],axis=1).max(axis=1)-pd.concat([l,pc],axis=1).min(axis=1)
    def avg(n): return bp.rolling(n).sum()/(tr.rolling(n).sum()+1e-10)
    return 100*(4*avg(p1)+2*avg(p2)+avg(p3))/7


def compute_ind_series(df, ind, params):
    c=df["Close"]
    if ind=="RSI":        return calc_rsi(c,params.get("period",14))
    if ind=="SMA":        return calc_sma(c,params.get("period",20))
    if ind=="EMA":        return calc_ema(c,params.get("period",20))
    if ind=="MACD":       return calc_macd(c,params.get("fast",12),params.get("slow",26),params.get("signal",9))[0]
    if ind=="Bollinger":  return calc_bb(c,params.get("period",20),params.get("std_dev",2.0))[1]
    if ind=="ATR":        return calc_atr(df,params.get("period",14))
    if ind=="Stochastic": return calc_stoch(df,params.get("k_period",14),params.get("d_period",3),params.get("smooth",3))[0]
    if ind=="ADX":        return calc_adx(df,params.get("period",14))
    if ind=="CCI":        return calc_cci(df,params.get("period",20))
    if ind=="Williams %R": return calc_willr(df,params.get("period",14))
    if ind=="MFI":        return calc_mfi(df,params.get("period",14))
    if ind=="ROC":        return calc_roc(c,params.get("period",12))
    if ind=="OBV":        return calc_obv(df)
    if ind=="VWAP":       return calc_vwap(df)
    if ind=="Aroon":      return calc_aroon(df,params.get("period",25))
    if ind=="Ultimate":   return calc_ultimate(df,params.get("p1",7),params.get("p2",14),params.get("p3",28))
    if ind=="Ichimoku":   return calc_ichimoku(df,params.get("tenkan",9),params.get("kijun",26))[0]
    if ind=="Parabolic SAR": return calc_psar(df,params.get("step",0.02),params.get("max_step",0.2))
    if ind=="Keltner":    return calc_keltner(df,params.get("period",20),params.get("atr_mult",2.0))[1]
    if ind=="Donchian":   return calc_donchian(df,params.get("period",20))[1]
    return c

def build_entry_signal(df, ind, params, condition, threshold):
    """
    > < >= <=  → STATE  (mevcut bar koşulu sağlıyor mu?)
    "Kesen" / "Kesti" → CROSSOVER  (sadece kesişim anı)
    "Üstünde" / "Altında" (fiyat-MA/bulut) → STATE
    """
    c   = df["Close"]
    thr = float(threshold) if threshold is not None else 0.0

    def cross_above(a, b): return (a > b) & (a.shift(1) <= b.shift(1))
    def cross_below(a, b): return (a < b) & (a.shift(1) >= b.shift(1))

    if ind == "RSI":
        rsi = calc_rsi(c, params.get("period", 14))
        if condition == ">":  return rsi > thr
        if condition == "<":  return rsi < thr
        if condition == ">=": return rsi >= thr
        if condition == "<=": return rsi <= thr
        if "Yukarı Kesen" in condition: return cross_above(rsi, pd.Series(thr, index=c.index))
        if "Aşağı Kesen"  in condition: return cross_below(rsi, pd.Series(thr, index=c.index))

    if ind == "MACD":
        ml, sl, _ = calc_macd(c, params.get("fast",12), params.get("slow",26), params.get("signal",9))
        ref = sl if "Signal" in condition else pd.Series(0.0, index=c.index)
        if "Yukarı Kesen"  in condition: return cross_above(ml, ref)
        if "Aşağı Kesen"   in condition: return cross_below(ml, ref)
        if "Sıfırı Yukarı" in condition: return cross_above(ml, pd.Series(0, index=c.index))
        if "Sıfırı Aşağı"  in condition: return cross_below(ml, pd.Series(0, index=c.index))
        if condition == ">":  return ml > thr
        if condition == "<":  return ml < thr
        if condition == ">=": return ml >= thr
        if condition == "<=": return ml <= thr

    if ind in ("SMA", "EMA"):
        ma = calc_sma(c, params.get("period",20)) if ind=="SMA" else calc_ema(c, params.get("period",20))
        if "Üstünde" in condition: return c > ma      # state
        if "Altında"  in condition: return c < ma     # state
        if "Yukarı"   in condition: return cross_above(c, ma)
        if "Aşağı"    in condition: return cross_below(c, ma)

    if ind == "Bollinger":
        upper, mid, lower = calc_bb(c, params.get("period",20), params.get("std_dev",2.0))
        if "Üst Band Üstünde" in condition: return c > upper   # state
        if "Alt Band Altında" in condition: return c < lower   # state
        if "Üst Bandı Yukarı" in condition: return cross_above(c, upper)
        if "Alt Bandı Aşağı"  in condition: return cross_below(c, lower)

    if ind == "Stochastic":
        k, d = calc_stoch(df, params.get("k_period",14), params.get("d_period",3), params.get("smooth",3))
        if "Yukarı Kesen" in condition: return cross_above(k, d)
        if "Aşağı Kesen"  in condition: return cross_below(k, d)
        if "Alım"  in condition: return k > 80    # state: aşırı alım bölgesinde
        if "Satım" in condition: return k < 20    # state: aşırı satım bölgesinde
        if condition == ">":  return k > thr
        if condition == "<":  return k < thr

    if ind == "Ichimoku":
        ten, kij, span_a, span_b, _ = calc_ichimoku(df, params.get("tenkan",9), params.get("kijun",26), params.get("senkou_b",52))
        cloud_top = pd.concat([span_a, span_b], axis=1).max(axis=1)
        cloud_bot = pd.concat([span_a, span_b], axis=1).min(axis=1)
        if "Bulut Üstünde"         in condition: return c > cloud_top   # state
        if "Bulut Altında"         in condition: return c < cloud_bot   # state
        if "Tenkan Kijun'u Yukarı" in condition: return cross_above(ten, kij)
        if "Tenkan Kijun'u Aşağı"  in condition: return cross_below(ten, kij)

    if ind == "VWAP":
        vwap = calc_vwap(df)
        if "Üstünde" in condition: return c > vwap   # state
        if "Altında"  in condition: return c < vwap  # state
        if "Yukarı"   in condition: return cross_above(c, vwap)
        if "Aşağı"    in condition: return cross_below(c, vwap)

    if ind == "Parabolic SAR":
        psar = calc_psar(df, params.get("step",0.02), params.get("max_step",0.2))
        if "Altında" in condition: return psar < c   # state: SAR fiyatın altında
        if "Üstünde" in condition: return psar > c   # state: SAR fiyatın üstünde
        if "Yukarı"  in condition: return cross_above(c, psar)
        if "Aşağı"   in condition: return cross_below(c, psar)

    if ind == "OBV":
        obv = calc_obv(df)
        if "Artıyor"  in condition: return obv > obv.shift(1)
        if "Azalıyor" in condition: return obv < obv.shift(1)

    # Generic numeric (ADX, CCI, Williams, MFI, ROC, ATR, Aroon, Ultimate, Keltner, Donchian)
    s   = compute_ind_series(df, ind, params)
    ref = pd.Series(thr, index=s.index)
    if condition == ">":  return s > thr
    if condition == "<":  return s < thr
    if condition == ">=": return s >= thr
    if condition == "<=": return s <= thr
    if "Yukarı Kesen" in condition: return cross_above(s, ref)
    if "Aşağı Kesen"  in condition: return cross_below(s, ref)
    if "Yukarı"       in condition: return cross_above(s, ref)
    if "Aşağı"        in condition: return cross_below(s, ref)

    return pd.Series(False, index=df.index)


# ─────────────────────────────────────────────────────────────────────────────
# BACKTEST ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def _invert_condition(cond: str) -> str:
    """Invert a condition for exit signals: > ↔ <, Yukarı ↔ Aşağı, etc."""
    # Order matters: check for compound operators first
    c = cond
    c = c.replace(">=", "‰TGE").replace("<=", "‰TLE").replace(">", "‰GT").replace("<", "‰LT")
    c = c.replace("‰TGE", "<=").replace("‰TLE", ">=").replace("‰GT", "<").replace("‰LT", ">")
    c = c.replace("Yukarı", "‰UP").replace("Aşağı", "‰DOWN")
    c = c.replace("‰UP", "Aşağı").replace("‰DOWN", "Yukarı")
    c = c.replace("Üstünde", "‰ABOVE").replace("Altında", "‰BELOW")
    c = c.replace("‰ABOVE", "Altında").replace("‰BELOW", "Üstünde")
    return c


# ─────────────────────────────────────────────────────────────────────────────
# BACKTEST ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def run_backtest(df,ind,params,condition,threshold,capital=10_000.0,
                ind2=None,params2=None,cond2=None,thr2=None, tp_pct=0.0, sl_pct=0.0):
    df=df.copy(); df.dropna(inplace=True)
    sig1=build_entry_signal(df,ind,params,condition,threshold).fillna(False)
    if ind2 and cond2 is not None:
        sig2=build_entry_signal(df,ind2,params2 or {},cond2,thr2).fillna(False)
        df["entry"]=(sig1 & sig2)
    else:
        df["entry"]=sig1
    
    # ✓ FİKS: Lookahead bias kaldırıldı — entry_price bfill (geriye dönük doldurma) kullanıldı
    # Entry olduğu mumun Close fiyatını al ve geriye doğru doldur (entry sırasındaki fiyat)
    df["entry_price"] = df["Close"].where(df["entry"]).bfill().where(df["entry"].cumsum() > 0)
    
    # Exit logic: reversal signal + DİNAMİK TP/SL
    opposite_condition = _invert_condition(condition)
    
    try:
        exit_signal = build_entry_signal(df, ind, params, opposite_condition, threshold).fillna(False)
    except Exception as e:
        # If reversal fails, use TP/SL only
        print(f"[WARN] exit_signal buildup failed: {e}. Using TP/SL only.")
        exit_signal = pd.Series(False, index=df.index)
    
    # YENİ DİNAMİK TP/SL MANTIĞI
    tp_cond = (df["Close"] >= df["entry_price"] * (1 + tp_pct/100.0)) if tp_pct > 0 else pd.Series(False, index=df.index)
    sl_cond = (df["Close"] <= df["entry_price"] * (1 - sl_pct/100.0)) if sl_pct > 0 else pd.Series(False, index=df.index)
    exit_tp_sl = tp_cond | sl_cond
    
    df["exit"] = (exit_signal | exit_tp_sl) & df["entry_price"].notna() & ~df["entry"]
    
    cash,shares,in_t=capital,0.0,False; eq,trades,ep=[],[],0.0
    # KANAYAN YARAYI ÇÖZEN KISIM: Sadece gerçek işlem anlarını kaydet
    actual_entries = pd.Series(False, index=df.index)
    actual_exits   = pd.Series(False, index=df.index)
    
    for idx,r in df.iterrows():
        p=float(r["Close"])
        if not in_t and r["entry"]: 
            shares,ep,cash,in_t=cash/p,p,0.0,True
            actual_entries.loc[idx] = True # Sadece cüzdandan para çıktığında
        elif in_t and r["exit"]:
            trades.append(shares*p>shares*ep); cash,shares,in_t=shares*p,0.0,False
            actual_exits.loc[idx] = True # Sadece hisse satıldığında
        eq.append(cash+shares*p)
    
    # ── ZORLA KAPAT: Son pozisyon açıksa, son gün fiyatından kapatsın ─────────
    if in_t and len(df) > 0:
        last_idx = df.index[-1]
        last_price = float(df["Close"].iloc[-1])
        trades.append(shares*last_price > shares*ep)  # Win/loss hesapla
        cash = shares*last_price
        shares = 0.0
        in_t = False
        actual_exits.loc[last_idx] = True  # Son çubuğu exit olarak işaretle
        eq.pop()  # Son equity değeri şimdi yanlış, düzelt
        eq.append(cash)
    
    df["equity"]=eq
    df["trade_entry"] = actual_entries # Grafiğe gidecek temiz veri
    df["trade_exit"]  = actual_exits   # Grafiğe gidecek temiz veri
    es=pd.Series(eq); dd=(es-es.cummax())/es.cummax()*100
    return dict(df=df,initial_capital=capital,final_capital=cash,
                total_return=(cash-capital)/capital*100,
                win_rate=sum(trades)/len(trades)*100 if trades else 0.0,
                max_drawdown=dd.min(),num_trades=len(trades),
                equity_series=es,drawdown_series=dd,indicator=ind,params=params)


# ─────────────────────────────────────────────────────────────────────────────
# CHART ENGINE — streamlit-lightweight-charts (TradingView style)
# Plotly kept ONLY for equity / PnL curve chart
# ─────────────────────────────────────────────────────────────────────────────

# ── LWC theme helpers ────────────────────────────────────────────────────────
def _lwc_layout(height: int = 460) -> dict:
    t = get_theme()
    grid_color   = "#2a3f5f"
    border_color = "#2e4a70"
    return {
        "layout": {
            "background": {"type": "solid", "color": t["bg_card"]},
            "textColor":  "#c8d6e8",
            "fontSize":   12,
            "fontFamily": "Space Mono, monospace",
        },
        "grid": {
            "vertLines": {"color": grid_color,  "style": 0},
            "horzLines": {"color": grid_color,  "style": 0},
        },
        "crosshair": {
            "mode": 0,
            "vertLine": {
                "color":                "#93b3d8",
                "width":                1,
                "style":                2,
                "visible":              True,
                "labelVisible":         True,
                "labelBackgroundColor": "#1e3a5f",
            },
            "horzLine": {
                "color":                "#93b3d8",
                "width":                1,
                "style":                2,
                "visible":              True,
                "labelVisible":         True,
                "labelBackgroundColor": "#1e3a5f",
            },
        },
        "rightPriceScale": {
            "borderColor":  border_color,
            "borderVisible": True,
            "scaleMargins": {"top": 0.05, "bottom": 0.05},
        },
        "leftPriceScale":  {"visible": False},
        "timeScale": {
            "borderColor":    border_color,
            "borderVisible":  True,
            "timeVisible":    True,
            "secondsVisible": False,
            "barSpacing":     8,
            "fixLeftEdge":    False,
            "fixRightEdge":   False,
        },
    }

def _df_to_ohlcv(df: pd.DataFrame) -> tuple[list, list]:
    """
    Convert DataFrame to LWC candle + volume dicts.
    Returns (candle_list, volume_list) — both sorted by time asc.
    """
    df = df.sort_index()
    candles, volumes = [], []
    for ts, row in df.iterrows():
        t_val = int(ts.timestamp())
        candles.append({
            "time":  t_val,
            "open":  round(float(row["Open"]),   4),
            "high":  round(float(row["High"]),   4),
            "low":   round(float(row["Low"]),    4),
            "close": round(float(row["Close"]),  4),
        })
        is_up = float(row["Close"]) >= float(row["Open"])
        volumes.append({
            "time":  t_val,
            "value": float(row["Volume"]),
            "color": "rgba(38,166,154,0.35)" if is_up else "rgba(239,83,80,0.35)",
        })
    return candles, volumes


def _series_to_lwc(series: pd.Series, color: str, name: str = "") -> list:
    """Convert a pandas Series to LWC LineSeries data list."""
    out = []
    for ts, v in series.dropna().items():
        out.append({"time": int(ts.timestamp()), "value": round(float(v), 4)})
    return out


def _hist_to_lwc(series: pd.Series, pos_color="#26a69a", neg_color="#ef5350") -> list:
    """Convert histogram series (e.g. MACD hist) to LWC HistogramSeries data."""
    out = []
    for ts, v in series.dropna().items():
        fv = float(v)
        out.append({"time": int(ts.timestamp()),
                    "value": round(fv, 4),
                    "color": pos_color if fv >= 0 else neg_color})
    return out



def _extend_df_for_ichimoku(df: pd.DataFrame, kijun: int = 26) -> pd.DataFrame:
    """
    Extend df index forward by `kijun` business days so that Ichimoku
    Span A/B (which are shifted forward) fall within the chart range.
    Only the date index is extended; OHLCV columns stay NaN for future rows.
    """
    import pandas.tseries.offsets as _off
    last_date = df.index[-1]
    if hasattr(last_date, 'tzinfo') and last_date.tzinfo is not None:
        future_idx = pd.date_range(start=last_date + _off.BDay(1),
                                   periods=kijun, freq="B", tz=last_date.tzinfo)
    else:
        future_idx = pd.date_range(start=last_date + _off.BDay(1),
                                   periods=kijun, freq="B")
    empty = pd.DataFrame(index=future_idx, columns=df.columns, dtype=float)
    return pd.concat([df, empty])

def render_custom_lwc_js(charts_data: list, symbol_name: str, height: int = 460) -> None:
    import json as _json
    charts_json = _json.dumps(charts_data)
    html = f"""<!DOCTYPE html>
<html>
<head>
<script src="https://unpkg.com/lightweight-charts@4.1.0/dist/lightweight-charts.standalone.production.js"></script>
<style>
  body {{ margin:0; padding:0; background:transparent; overflow:hidden; }}
  .chart-wrapper {{ position:relative; width:100%; margin-bottom:4px; }}
</style>
</head>
<body>
<script>
const chartsData = {charts_json};
const sym = {_json.dumps(symbol_name)};
const tvCharts = [];

function initializeCharts() {{
    chartsData.forEach((config, index) => {{
        const container = document.createElement('div');
        container.className = 'chart-wrapper';
        const chartHeight = (config.chart && config.chart.height) ? config.chart.height : {height};
        container.style.height = chartHeight + 'px';
        document.body.appendChild(container);
        
        // Chart options'ı hazırla
        let chartOptions = {{}};
        if (config.chart) {{
            // Tüm options'ı kopyala ama height key'ini çıkart
            for (const key in config.chart) {{
                if (key !== 'height') {{
                    chartOptions[key] = config.chart[key];
                }}
            }}
        }}
        
        // Container'ın gerçek boyutlarını elde et
        let width = container.clientWidth;
        let height = container.clientHeight;
        
        // Fallback: Eğer 0 ise, style'dan al
        if (width === 0) width = parseInt(container.style.width || 800);
        if (height === 0) height = parseInt(container.style.height || {height});
        
        // Chart oluştur
        try {{
            const chart = LightweightCharts.createChart(container, {{
                width: Math.max(width, 100),
                height: Math.max(height, 100),
                layout: chartOptions.layout || {{ background: {{ type: 'solid', color: '#111827' }}, textColor: '#c8d6e8' }},
                grid: chartOptions.grid || {{ vertLines: {{ color: '#2a3f5f', style: 0 }}, horzLines: {{ color: '#2a3f5f', style: 0 }} }},
                crosshair: chartOptions.crosshair || {{ mode: 0 }},
                timeScale: chartOptions.timeScale || {{ borderColor: '#2e4a70', borderVisible: true, timeVisible: true }},
                rightPriceScale: chartOptions.rightPriceScale || {{ borderColor: '#2e4a70', borderVisible: true }},
                leftPriceScale: chartOptions.leftPriceScale || {{ visible: false }}
            }});
            
            tvCharts.push(chart);
            
            // ResizeObserver
            const resizeObserver = new ResizeObserver(entries => {{
                if (entries.length === 0) return;
                const rect = entries[0].contentRect;
                if (rect.width > 10 && rect.height > 10) {{
                    chart.applyOptions({{ width: rect.width, height: rect.height }});
                }}
            }});
            resizeObserver.observe(container);
            
            let candleSeries = null;
            
            // Legend (ana chart için)
            if (index === 0) {{
                const legend = document.createElement('div');
                legend.style = "position:absolute; left:12px; top:12px; z-index:2; color:#c8d6e8; font-family:'Space Mono', monospace; font-size:13px; background:rgba(17,24,39,0.75); padding:6px 10px; border-radius:6px; border:1px solid #2e4a70; pointer-events:none;";
                container.appendChild(legend);
                legend.innerHTML = `<span style="font-weight:700;color:#00d4ff;font-size:14px;">${{sym}}</span>`;
                
                chart.subscribeCrosshairMove((param) => {{
                    if (param.time && param.seriesData.size > 0 && candleSeries) {{
                        const d = param.seriesData.get(candleSeries);
                        if (d && d.open !== undefined) {{
                            const chg = (((d.close - d.open) / d.open) * 100).toFixed(2);
                            const cColor = d.close >= d.open ? '#00e676' : '#ff4757';
                            legend.innerHTML = `
                                <span style="font-weight:700;color:#00d4ff;font-size:14px;">${{sym}}</span>&nbsp;&nbsp;
                                <span style="color:#8ba3c9">A:</span><span style="color:#fff"> ${{d.open.toFixed(2)}}</span>&nbsp;
                                <span style="color:#8ba3c9">Y:</span><span style="color:#fff"> ${{d.high.toFixed(2)}}</span>&nbsp;
                                <span style="color:#8ba3c9">D:</span><span style="color:#fff"> ${{d.low.toFixed(2)}}</span>&nbsp;
                                <span style="color:#8ba3c9">K:</span><span style="color:#fff"> ${{d.close.toFixed(2)}}</span>&nbsp;
                                <span style="color:${{cColor}}"> ${{chg >= 0 ? '+' : ''}}${{chg}}%</span>
                            `;
                            return;
                        }}
                    }}
                    legend.innerHTML = `<span style="font-weight:700;color:#00d4ff;font-size:14px;">${{sym}}</span>`;
                }});
            }}
            
            // Serileri ekle
            if (config.series && config.series.length > 0) {{
                config.series.forEach(s => {{
                    const sOpts = s.options || {{}};
                    let cleanOpts = {{}};
                    const validKeys = ['color', 'upColor', 'downColor', 'borderUpColor', 'borderDownColor',
                                       'wickUpColor', 'wickDownColor', 'lineWidth', 'lineStyle', 'priceFormat',
                                       'priceScaleId', 'title', 'priceLineVisible'];
                    for (const k of validKeys) {{
                        if (sOpts[k] !== undefined) cleanOpts[k] = sOpts[k];
                    }}
                    
                    try {{
                        let seriesObj = null;
                        if (s.type === 'Candlestick') {{
                            seriesObj = chart.addCandlestickSeries(cleanOpts);
                            candleSeries = seriesObj;
                        }} else if (s.type === 'Histogram') {{
                            seriesObj = chart.addHistogramSeries(cleanOpts);
                        }} else if (s.type === 'Line') {{
                            seriesObj = chart.addLineSeries(cleanOpts);
                        }} else if (s.type === 'Area') {{
                            seriesObj = chart.addAreaSeries(cleanOpts);
                        }}
                        
                        if (seriesObj) {{
                            if (s.data) seriesObj.setData(s.data);
                            if (s.markers) seriesObj.setMarkers(s.markers);
                            
                            if (sOpts.scaleMargins) {{
                                const scaleId = sOpts.priceScaleId !== undefined ? sOpts.priceScaleId : '';
                                chart.priceScale(scaleId).applyOptions({{ scaleMargins: sOpts.scaleMargins }});
                            }}
                        }}
                    }} catch(e) {{
                        console.error("Series error:", e);
                    }}
                }});
                // Veriler yüklendikten sonra SADECE 1 KERE ortala
                chart.timeScale().fitContent();
            }}
        }} catch(e) {{
            console.error("Chart init error:", e);
        }}
    }});
    
    // Çoklu chart senkronizasyonu
    if (tvCharts.length > 1) {{
        tvCharts[0].timeScale().subscribeVisibleLogicalRangeChange(r => {{
            if(!window.isSyncing){{ window.isSyncing=true; tvCharts[1].timeScale().setVisibleLogicalRange(r); window.isSyncing=false; }}
        }});
        tvCharts[1].timeScale().subscribeVisibleLogicalRangeChange(r => {{
            if(!window.isSyncing){{ window.isSyncing=true; tvCharts[0].timeScale().setVisibleLogicalRange(r); window.isSyncing=false; }}
        }});
    }}
}}

// DOM hazırsa hemen başlat, değilse bekle
if (document.readyState === 'loading') {{
    document.addEventListener('DOMContentLoaded', initializeCharts);
}} else {{
    initializeCharts();
}}

// Güvenlik: 100ms sonra tekrar kontrol et
setTimeout(initializeCharts, 100);
</script>
</body>
</html>"""
    
    total_height = sum(c.get("chart", {}).get("height", height) for c in charts_data)
    _stc.html(html, height=total_height, scrolling=False)


# ── Main dashboard chart (LWC) — multi-overlay, volume toggle, OHLC legend ───
def chart_dashboard_lwc(df: pd.DataFrame, symbol: str,
                        overlay_inds: Optional[list] = None,
                        sep_vol: bool = False) -> None:
    """
    Renders TradingView-style LWC chart.
    overlay_inds : list of overlay indicator names (multi-select)
    sep_vol      : if True, volume in a 2nd synced chart; else embedded bottom 15%
    """
    if not _LWC_AVAILABLE:
        st.plotly_chart(chart_dashboard_plotly(df, symbol), use_container_width=True)
        return

    t     = get_theme()
    c     = df["Close"]
    candles, volumes = _df_to_ohlcv(df)
    inds  = overlay_inds or []

    # ── Candle series ──────────────────────────────────────────────────────────
    candle_series: dict = {
    "type":   "Candlestick",
    "data":   candles,
    "options": {
        "upColor":         "#26a69a",
        "downColor":       "#ef5350",
        "borderUpColor":   "#26a69a",
        "borderDownColor": "#ef5350",
        "wickUpColor":     "#26a69a",
        "wickDownColor":   "#ef5350",
        "priceLineVisible": True,
        "title": display_sym(symbol),
    },
}

    # ── Volume series (inline or separate) ────────────────────────────────────
    vol_inline: dict = {
        "type": "Histogram",
        "data": volumes,
        "options": {
            "priceFormat":  {"type": "volume"},
            "priceScaleId": "",               # separate scale, overlaid
            "scaleMargins": {"top": 0.85, "bottom": 0},
        },
    }
    vol_separate: dict = {
        "type": "Histogram",
        "data": volumes,
        "options": {
            "priceFormat": {"type": "volume"},
            "color":       "rgba(38,166,154,0.45)",
        },
    }

    # ── Build overlay series for EVERY selected indicator ─────────────────────
    def _make_overlay_series(ind_name: str) -> list[dict]:
        """Return list of LWC series dicts for a single overlay indicator."""
        out: list[dict] = []
        if ind_name == "SMA":
            sma = calc_sma(c, 20)
            out.append({"type":"Line","data":_series_to_lwc(sma,"#ffd700"),
                        "options":{"color":"#ffd700","lineWidth":1,"lineStyle":1,
                                   "title":"SMA 20","priceLineVisible":False}})
        elif ind_name == "EMA":
            ema = calc_ema(c, 20)
            out.append({"type":"Line","data":_series_to_lwc(ema,"#ff9f43"),
                        "options":{"color":"#ff9f43","lineWidth":1,"lineStyle":1,
                                   "title":"EMA 20","priceLineVisible":False}})
        elif ind_name == "Bollinger":
            upper,mid,lower = calc_bb(c, 20, 2.0)
            for s_data,clr,ttl in [(upper,"rgba(0,212,255,.9)","BB Üst"),
                                    (mid,  "rgba(0,212,255,.55)","BB Orta"),
                                    (lower,"rgba(0,212,255,.9)","BB Alt")]:
                out.append({"type":"Line","data":_series_to_lwc(s_data,clr),
                            "options":{"color":clr,"lineWidth":1,
                                       "title":ttl,"priceLineVisible":False}})
        elif ind_name == "Ichimoku":
            # Extend df forward 26 bars so Span A/B projects into future
            df_ext = _extend_df_for_ichimoku(df, kijun=26)
            ten,kij,sa,sb,_ = calc_ichimoku(df_ext, 9, 26, 52)
            # Tenkan + Kijun as thin lines
            out.append({"type":"Line","data":_series_to_lwc(ten.dropna(),"#ef5350"),
                        "options":{"color":"#ef5350","lineWidth":1,"title":"Tenkan","priceLineVisible":False}})
            out.append({"type":"Line","data":_series_to_lwc(kij.dropna(),"#2962ff"),
                        "options":{"color":"#2962ff","lineWidth":1,"title":"Kijun","priceLineVisible":False}})
            # Span A — kalın yeşil çizgi (lineWidth:3) — AreaSeries kaldırıldı (grafiği kirletiyordu)
            out.append({"type":"Line","data":_series_to_lwc(sa.dropna(),"#00e676"),
                        "options":{"color":"#00e676","lineWidth":3,
                                   "title":"Span A (Kumo)","priceLineVisible":False}})
            # Span B — kalın kırmızı çizgi (lineWidth:3)
            out.append({"type":"Line","data":_series_to_lwc(sb.dropna(),"#ff4757"),
                        "options":{"color":"#ff4757","lineWidth":3,
                                   "title":"Span B (Kumo)","priceLineVisible":False}})
        elif ind_name == "VWAP":
            out.append({"type":"Line","data":_series_to_lwc(calc_vwap(df),"#b48eff"),
                        "options":{"color":"#b48eff","lineWidth":1,"lineStyle":0,
                                   "title":"VWAP","priceLineVisible":False}})
        elif ind_name == "Parabolic SAR":
            out.append({"type":"Line","data":_series_to_lwc(
                            calc_psar(df,0.02,0.2),"#ffd700"),
                        "options":{"color":"#ffd700","lineWidth":1,"lineStyle":4,
                                   "title":"PSAR","priceLineVisible":False}})
        elif ind_name == "Keltner":
            up,mi,lo = calc_keltner(df,20,2.0)
            for s_data,clr,ttl in [(up,"rgba(255,159,67,.8)","KC Üst"),
                                    (lo,"rgba(255,159,67,.8)","KC Alt")]:
                out.append({"type":"Line","data":_series_to_lwc(s_data,clr),
                            "options":{"color":clr,"lineWidth":1,
                                       "title":ttl,"priceLineVisible":False}})
        elif ind_name == "Donchian":
            hi,mi,lo = calc_donchian(df,20)
            for s_data,clr,ttl in [(hi,"rgba(180,142,255,.8)","DC Üst"),
                                    (lo,"rgba(180,142,255,.8)","DC Alt")]:
                out.append({"type":"Line","data":_series_to_lwc(s_data,clr),
                            "options":{"color":clr,"lineWidth":1,
                                       "title":ttl,"priceLineVisible":False}})
        elif ind_name == "ATR":
            out.append({"type":"Line","data":_series_to_lwc(
                            calc_atr(df,14),"#ff9f43"),
                        "options":{"color":"#ff9f43","lineWidth":1,
                                   "title":"ATR 14","priceLineVisible":False}})
        return out

    # ── Assemble main chart series ─────────────────────────────────────────────
    main_series: list[dict] = [candle_series]
    if not sep_vol:
        main_series.append(vol_inline)

    # Default SMA 20 when no indicators selected
    if not inds:
        sma20 = calc_sma(c, 20)
        main_series.append({
            "type":"Line","data":_series_to_lwc(sma20, t["accent"]),
            "options":{"color":t["accent"],"lineWidth":1,"lineStyle":2,
                       "title":"SMA 20","priceLineVisible":False}
        })
    else:
        for ind_name in inds:
            main_series.extend(_make_overlay_series(ind_name))

    # ── Assemble main chart layout (watermark removed — legend handles OHLC) ───
    main_chart_layout = {
    **_lwc_layout(460),
}
    charts: list[dict] = [{"chart": main_chart_layout, "series": main_series}]

    # ── Optional separate volume panel ─────────────────────────────────────────
    if sep_vol:
        vol_chart_layout = {
            **_lwc_layout(120),
            "rightPriceScale": {
                "borderColor": t["border"],
                "scaleMargins": {"top": 0.1, "bottom": 0},
            },
        }
        charts.append({"chart": vol_chart_layout, "series": [vol_separate]})

    # Unique key ensures full re-render when symbol or settings change
    chart_key = f"dash_{symbol}_{'_'.join(sorted(inds))}_{'sv' if sep_vol else 'iv'}"
    # Fix 5: wrap chart in a styled div for visible border + glow
    st.markdown('<div class="lwc-frame">', unsafe_allow_html=True)
    render_custom_lwc_js(charts, display_sym(symbol), height=460)
    st.markdown('</div>', unsafe_allow_html=True)


# ── Backtest chart with indicator + AL/SAT markers (LWC) ────────────────────
def chart_with_indicator_lwc(df: pd.DataFrame, symbol: str,
                              ind: str, params: dict,
                              entry_series: Optional[pd.Series] = None,
                              exit_series:  Optional[pd.Series] = None) -> None:
    """
    Multi-chart layout:
      • Overlay inds → single chart (candle + overlay + volume)
      • Oscillators  → two stacked charts (synced crosshair via same key)
    AL/SAT markers rendered as arrowUp/arrowDown on candle chart.
    """
    if not _LWC_AVAILABLE:
        st.plotly_chart(chart_with_indicator_plotly(df, symbol, ind, params),
                        use_container_width=True)
        return

    t = get_theme()
    c = df["Close"]
    candles, volumes = _df_to_ohlcv(df)
    category = IND_META[ind]["category"]

    # ── Build AL/SAT markers ──────────────────────────────────────────────────
    # ✓ FİKS: Marker time format Unix timestamp'e standardize edildi (mum verileriyle uyuşmak için)
    markers = []
    if entry_series is not None:
        for ts, val in entry_series.items():
            if val:
                markers.append({
                    "time":     int(ts.timestamp()),
                    "position": "belowBar",
                    "color":    "#26a69a",
                    "shape":    "arrowUp",
                    "text":     "AL",
                    "size":     1,
                })
    if exit_series is not None:
        for ts, val in exit_series.items():
            if val:
                markers.append({
                    "time":     int(ts.timestamp()),
                    "position": "aboveBar",
                    "color":    "#ef5350",
                    "shape":    "arrowDown",
                    "text":     "SAT",
                    "size":     1,
                })

    # Candle series with markers
    candle_series = {
        "type":    "Candlestick",
        "data":    candles,
        "markers": markers,
        "options": {
            "upColor":         "#26a69a", "downColor":       "#ef5350",
            "borderUpColor":   "#26a69a", "borderDownColor": "#ef5350",
            "wickUpColor":     "#26a69a", "wickDownColor":   "#ef5350",
        },
    }
    vol_series = {
        "type": "Histogram",
        "data": volumes,
        "options": {"priceFormat":{"type":"volume"},"priceScaleId":"","scaleMargins":{"top":0.85,"bottom":0}},
    }

    # ── Overlay indicator series ──────────────────────────────────────────────
    overlay_series = []
    if category == "overlay":
        if ind == "SMA":
            overlay_series.append({"type":"Line","data":_series_to_lwc(calc_sma(c,params.get("period",20)),"#ffd700"),
                                   "options":{"color":"#ffd700","lineWidth":1,"lineStyle":1}})
        elif ind == "EMA":
            overlay_series.append({"type":"Line","data":_series_to_lwc(calc_ema(c,params.get("period",20)),"#ff9f43"),
                                   "options":{"color":"#ff9f43","lineWidth":1,"lineStyle":1}})
        elif ind == "Bollinger":
            upper,mid,lower = calc_bb(c,params.get("period",20),params.get("std_dev",2.0))
            for s_d,clr in [(upper,"rgba(0,212,255,.8)"),(mid,"rgba(0,212,255,.5)"),(lower,"rgba(0,212,255,.8)")]:
                overlay_series.append({"type":"Line","data":_series_to_lwc(s_d,clr),"options":{"color":clr,"lineWidth":1}})
        elif ind == "Ichimoku":
            # Extend df forward so Span A/B cloud projects into future
            df_ext = _extend_df_for_ichimoku(df, kijun=params.get("kijun", 26))
            ten,kij,sa,sb,_ = calc_ichimoku(df_ext,
                                            params.get("tenkan",9),
                                            params.get("kijun",26),
                                            params.get("senkou_b",52))
            overlay_series.append({"type":"Line","data":_series_to_lwc(ten.dropna(),"#ef5350"),
                                   "options":{"color":"#ef5350","lineWidth":1,"title":"Tenkan","priceLineVisible":False}})
            overlay_series.append({"type":"Line","data":_series_to_lwc(kij.dropna(),"#2962ff"),
                                   "options":{"color":"#2962ff","lineWidth":1,"title":"Kijun","priceLineVisible":False}})
            # Span A — kalın yeşil çizgi lineWidth:3 (AreaSeries kaldırıldı)
            overlay_series.append({"type":"Line","data":_series_to_lwc(sa.dropna(),"#00e676"),
                                   "options":{"color":"#00e676","lineWidth":3,
                                              "title":"Span A (Kumo)","priceLineVisible":False}})
            # Span B — kalın kırmızı çizgi lineWidth:3
            overlay_series.append({"type":"Line","data":_series_to_lwc(sb.dropna(),"#ff4757"),
                                   "options":{"color":"#ff4757","lineWidth":3,
                                              "title":"Span B (Kumo)","priceLineVisible":False}})
        elif ind == "VWAP":
            overlay_series.append({"type":"Line","data":_series_to_lwc(calc_vwap(df),"#b48eff"),
                                   "options":{"color":"#b48eff","lineWidth":1}})
        elif ind == "Parabolic SAR":
            overlay_series.append({"type":"Line","data":_series_to_lwc(calc_psar(df,params.get("step",.02),params.get("max_step",.2)),"#ffd700"),
                                   "options":{"color":"#ffd700","lineWidth":1,"lineStyle":4}})
        elif ind == "Keltner":
            up,mi,lo = calc_keltner(df,params.get("period",20),params.get("atr_mult",2.0))
            for s_d,clr in [(up,"rgba(255,159,67,.7)"),(lo,"rgba(255,159,67,.7)")]:
                overlay_series.append({"type":"Line","data":_series_to_lwc(s_d,clr),"options":{"color":clr,"lineWidth":1}})
        elif ind == "Donchian":
            hi,mi,lo = calc_donchian(df,params.get("period",20))
            for s_d,clr in [(hi,"rgba(180,142,255,.7)"),(lo,"rgba(180,142,255,.7)")]:
                overlay_series.append({"type":"Line","data":_series_to_lwc(s_d,clr),"options":{"color":clr,"lineWidth":1}})
        elif ind == "ATR":
            overlay_series.append({"type":"Line","data":_series_to_lwc(calc_atr(df,params.get("period",14)),"#ff9f43"),
                                   "options":{"color":"#ff9f43","lineWidth":1}})

    # ── Oscillator panel series ───────────────────────────────────────────────
    osc_series = []
    if category == "oscillator":
        if ind == "RSI":
            rsi = calc_rsi(c, params.get("period", 14))
            osc_series.append({"type":"Line","data":_series_to_lwc(rsi,"#b48eff","RSI"),
                               "options":{"color":"#b48eff","lineWidth":1}})
        elif ind == "MACD":
            ml,sl,hist = calc_macd(c, params.get("fast",12), params.get("slow",26), params.get("signal",9))
            osc_series.append({"type":"Histogram","data":_hist_to_lwc(hist),"options":{"lineWidth":1}})
            osc_series.append({"type":"Line","data":_series_to_lwc(ml,t["accent"],"MACD"),"options":{"color":t["accent"],"lineWidth":1}})
            osc_series.append({"type":"Line","data":_series_to_lwc(sl,"#ffd700","Signal"),"options":{"color":"#ffd700","lineWidth":1,"lineStyle":2}})
        elif ind == "Stochastic":
            k,d = calc_stoch(df, params.get("k_period",14), params.get("d_period",3), params.get("smooth",3))
            osc_series.append({"type":"Line","data":_series_to_lwc(k,t["accent"],"%K"),"options":{"color":t["accent"],"lineWidth":1}})
            osc_series.append({"type":"Line","data":_series_to_lwc(d,"#ffd700","%D"),"options":{"color":"#ffd700","lineWidth":1,"lineStyle":2}})
        elif ind == "ADX":
            adx = calc_adx(df, params.get("period",14))
            osc_series.append({"type":"Line","data":_series_to_lwc(adx,"#ff9f43","ADX"),"options":{"color":"#ff9f43","lineWidth":1}})
        elif ind == "CCI":
            cci = calc_cci(df, params.get("period",20))
            osc_series.append({"type":"Line","data":_series_to_lwc(cci,"#b48eff","CCI"),"options":{"color":"#b48eff","lineWidth":1}})
        elif ind in ("Williams %R","MFI","ROC","Aroon","Ultimate"):
            s = compute_ind_series(df, ind, params)
            osc_series.append({"type":"Line","data":_series_to_lwc(s,t["accent"],ind),"options":{"color":t["accent"],"lineWidth":1}})
        else:
            s = compute_ind_series(df, ind, params)
            osc_series.append({"type":"Line","data":_series_to_lwc(s,t["accent"],ind),"options":{"color":t["accent"],"lineWidth":1}})

    # ── Assemble multi-chart payload ──────────────────────────────────────────
    if category == "overlay":
        charts = [{
            "chart":  _lwc_layout(460),
            "series": [candle_series] + overlay_series + [vol_series],
        }]
    else:
        # Two synced charts — LWC sync is via same container group (shared timeScale)
        charts = [
            {
                "chart":  _lwc_layout(300),
                "series": [candle_series, vol_series],
            },
            {
                "chart":  _lwc_layout(180),
                "series": osc_series,
            },
        ]

    st.markdown('<div class="lwc-frame">', unsafe_allow_html=True)
    # ESKİ renderLightweightCharts YERİNE BİZİN JS MOTORUMUZ:
    render_custom_lwc_js(charts, display_sym(symbol), height=460)
    st.markdown('</div>', unsafe_allow_html=True)


# ── Plotly fallbacks (used when LWC not installed, or for equity chart) ──────
def _lay_plotly(**kw):
    t=get_theme()
    b=dict(paper_bgcolor="rgba(0,0,0,0)",plot_bgcolor="rgba(13,20,33,.6)",
           font=dict(family="Sora,sans-serif",color="#8ba3c9"),
           xaxis=dict(gridcolor=t["border"],showgrid=True,zeroline=False),
           yaxis=dict(gridcolor=t["border"],showgrid=True,zeroline=False),
           margin=dict(l=40,r=20,t=44,b=36),
           legend=dict(bgcolor="rgba(0,0,0,0)",bordercolor=t["border"]),
           hovermode="x unified")
    b.update(kw); return b

def chart_dashboard_plotly(df, symbol, overlay_ind=None, overlay_params=None):
    t=get_theme()
    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,row_heights=[.75,.25],vertical_spacing=.03)
    fig.add_trace(go.Candlestick(x=df.index,open=df["Open"],high=df["High"],low=df["Low"],close=df["Close"],
        name=display_sym(symbol),increasing_line_color="#26a69a",decreasing_line_color="#ef5350",
        increasing_fillcolor="rgba(38,166,154,.18)",decreasing_fillcolor="rgba(239,83,80,.18)"),row=1,col=1)
    colors=["rgba(38,166,154,.4)" if c>=o else "rgba(239,83,80,.4)" for c,o in zip(df["Close"],df["Open"])]
    fig.add_trace(go.Bar(x=df.index,y=df["Volume"],marker_color=colors,showlegend=False),row=2,col=1)
    fig.update_layout(**_lay_plotly(title=dict(text=f"<b>{display_sym(symbol)}</b>",font=dict(size=13,color="#e8f0fe")),
        xaxis_rangeslider_visible=False,height=500))
    return fig

def chart_with_indicator_plotly(df, symbol, ind, params):
    t=get_theme()
    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,row_heights=[.7,.3],vertical_spacing=.04)
    fig.add_trace(go.Candlestick(x=df.index,open=df["Open"],high=df["High"],low=df["Low"],close=df["Close"],
        name=display_sym(symbol),increasing_line_color="#26a69a",decreasing_line_color="#ef5350",
        increasing_fillcolor="rgba(38,166,154,.18)",decreasing_fillcolor="rgba(239,83,80,.18)"),row=1,col=1)
    s=compute_ind_series(df,ind,params)
    fig.add_trace(go.Scatter(x=df.index,y=s,name=ind,line=dict(color=t["accent"],width=1.5)),row=2,col=1)
    fig.update_layout(**_lay_plotly(title=dict(text=f"<b>{display_sym(symbol)}</b> — {ind}",font=dict(size=13,color="#e8f0fe")),
        xaxis_rangeslider_visible=False,height=500))
    return fig

def chart_equity(result):
    """Equity / PnL curve — always Plotly (LWC has no area/line chart mode needed here)."""
    t=get_theme(); df=result["df"]; es=result["equity_series"]; dd=result["drawdown_series"]
    fig=make_subplots(rows=2,cols=1,shared_xaxes=True,row_heights=[.7,.3],vertical_spacing=.04,
                      subplot_titles=["Portföy Değeri","Drawdown (%)"])
    fig.add_trace(go.Scatter(x=df.index,y=es,name="Strateji",
                             line=dict(color=t["accent"],width=2),fill="tozeroy",
                             fillcolor=f"rgba({t['accent_rgb']},.06)"),row=1,col=1)
    bh=result["initial_capital"]*df["Close"]/df["Close"].iloc[0]
    fig.add_trace(go.Scatter(x=df.index,y=bh,name="Buy & Hold",
                             line=dict(color="#ffd700",width=1.2,dash="dash")),row=1,col=1)
    fig.add_trace(go.Scatter(x=df.index,y=dd,name="Drawdown",
                             line=dict(color="#ef5350",width=1),fill="tozeroy",
                             fillcolor="rgba(239,83,80,.1)"),row=2,col=1)
    fig.update_layout(**_lay_plotly(height=420,
        title=dict(text="<b>Backtest Sonuçları</b>",font=dict(size=13,color="#e8f0fe"))))
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# TRADINGVIEW ADVANCED CHART WIDGET  — Dashboard only
# ─────────────────────────────────────────────────────────────────────────────
_TV_EXCHANGE_MAP = {
    # BIST
    ".IS":  "BIST",
    # German
    ".DE":  "XETRA",
    # London
    ".L":   "LSE",
    # Paris
    ".PA":  "EURONEXT",
    # Milan
    ".MI":  "MIL",
}

_TV_CRYPTO_MAP = {
    "BTC-USD":   "BINANCE:BTCUSDT",
    "ETH-USD":   "BINANCE:ETHUSDT",
    "BNB-USD":   "BINANCE:BNBUSDT",
    "SOL-USD":   "BINANCE:SOLUSDT",
    "XRP-USD":   "BINANCE:XRPUSDT",
    "ADA-USD":   "BINANCE:ADAUSDT",
    "AVAX-USD":  "BINANCE:AVAXUSDT",
    "DOGE-USD":  "BINANCE:DOGEUSDT",
    "DOT-USD":   "BINANCE:DOTUSDT",
    "MATIC-USD": "BINANCE:MATICUSDT",
    "LINK-USD":  "BINANCE:LINKUSDT",
    "UNI-USD":   "BINANCE:UNIUSDT",
    "LTC-USD":   "BINANCE:LTCUSDT",
    "ATOM-USD":  "BINANCE:ATOMUSDT",
    "TRX-USD":   "BINANCE:TRXUSDT",
}

_TV_COMMODITY_MAP = {
    "GC=F": "TVC:GOLD",
    "SI=F": "TVC:SILVER",
    "CL=F": "TVC:USOIL",
    "NG=F": "TVC:NATURALGAS",
    "ZW=F": "CBOT:ZW1!",
}

def _to_tv_symbol(api_sym: str) -> str:
    """
    Convert yfinance API symbol to TradingView symbol string.
    Priority: Crypto → Commodity → BIST (.IS) → Other exchanges → US equities.
    BIST symbols (.IS suffix) are ALWAYS mapped to BIST: — never NASDAQ/NYSE.
    """
    s = api_sym.strip()
    # 1. Crypto exact match
    if s in _TV_CRYPTO_MAP:
        return _TV_CRYPTO_MAP[s]
    # 2. Commodity / futures exact match
    if s in _TV_COMMODITY_MAP:
        return _TV_COMMODITY_MAP[s]
    # 3. BIST — .IS suffix (most important, must come before generic suffix loop)
    if s.upper().endswith(".IS"):
        ticker = s[:-3].upper()
        return f"BIST:{ticker}"
    # 4. Other exchange suffixes (.DE, .L, .PA, .MI, .AS)
    for sfx, exchange in _TV_EXCHANGE_MAP.items():
        if sfx == ".IS":          # already handled above
            continue
        if s.upper().endswith(sfx.upper()):
            ticker = s[:-len(sfx)].upper()
            return f"{exchange}:{ticker}"
    # 5. Known NASDAQ tickers
    _NASDAQ = {
        "AAPL","MSFT","GOOGL","GOOG","AMZN","NVDA","META","TSLA","INTC","AMD",
        "QCOM","PYPL","NFLX","ADBE","CSCO","ORCL","CRM","AVGO","TXN","MU","LRCX",
        "SPY","QQQ","GLD","SLV","USO","TQQQ","SQQQ",
    }
    if s.upper() in _NASDAQ:
        return f"NASDAQ:{s.upper()}"
    # 6. Known NYSE tickers
    _NYSE = {
        "BRK-B","JPM","V","UNH","XOM","JNJ","PG","MA","HD","CVX","MRK","ABBV",
        "LLY","BAC","WMT","KO","PFE","DIS","VZ","T","GM","F",
    }
    if s.upper().replace("-","") in {x.replace("-","") for x in _NYSE}:
        return f"NYSE:{s.upper()}"
    # 7. Default: assume NYSE for unknown no-suffix symbols
    return f"NYSE:{s.upper()}"


def render_tv_widget(api_sym: str, height: int = 560) -> None:
    """
    Embed TradingView Advanced Real-Time Chart Widget via st.components.v1.html.
    Uses dark theme matching app palette. Removes overlay indicator selector.
    """
    tv_sym = _to_tv_symbol(api_sym)
    t = get_theme()
    bg_color = t["bg_card"].lstrip("#")

    # Force a unique HTML string per symbol so Streamlit re-renders the component.
    # st.components.v1.html has no `key` param — uniqueness is achieved via HTML content diff.
    container_id = f"tv_{tv_sym.replace(':','_').replace('-','_').replace('=','_').replace('.','_')}"

    html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
  body {{ margin:0; padding:0; background:#{bg_color}; }}
  #{container_id} {{ width:100%; height:{height}px; }}
</style>
</head>
<body>
<!-- symbol={tv_sym} height={height} -->
<div id="{container_id}"></div>
<script type="text/javascript">
(function() {{
  var script = document.createElement('script');
  script.type = 'text/javascript';
  script.src = 'https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
  script.async = true;
  script.innerHTML = JSON.stringify({{
    "container_id": "{container_id}",
    "width": "100%",
    "height": {height},
    "symbol": "{tv_sym}",
    "interval": "D",
    "timezone": "Europe/Istanbul",
    "theme": "dark",
    "style": "1",
    "locale": "tr",
    "toolbar_bg": "#{bg_color}",
    "enable_publishing": false,
    "hide_top_toolbar": false,
    "hide_legend": false,
    "save_image": false,
    "calendar": false,
    "hide_volume": false,
    "support_host": "https://www.tradingview.com",
    "studies": ["RSI@tv-basicstudies","MACD@tv-basicstudies"],
    "show_popup_button": true,
    "popup_width": "1000",
    "popup_height": "650"
  }});
  document.getElementById('{container_id}').appendChild(script);
}})();
</script>
</body>
</html>"""

    _stc.html(html, height=height + 10, scrolling=False)


# ─────────────────────────────────────────────────────────────────────────────
# UI HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def sh(icon,title):
    st.markdown(f'<div class="sh"><div class="sh-dot"></div><h3>{icon}&nbsp;{title}</h3></div>',
                unsafe_allow_html=True)

def mc(label,value,sub="",cls=""):
    sub_html=f'<div class="mc-sub">{sub}</div>' if sub else ""
    st.markdown(f'<div class="mc {cls}"><div class="mc-lbl">{label}</div>'
                f'<div class="mc-val">{value}</div>{sub_html}</div>',unsafe_allow_html=True)

def indicator_form(prefix:str):
    """Dynamic indicator form. Returns (ind, params, condition, threshold)."""
    # Build display labels safely — no split("—") IndexError risk
    ind_display_options = []
    for k,v in IND_META.items():
        label_parts = v['label'].split('—')
        short = label_parts[1].strip() if len(label_parts) > 1 else v['label']
        ind_display_options.append(f"{k} — {short}")

    chosen = st.selectbox("İndikatör", ind_display_options, key=f"{prefix}_ind")
    ind = chosen.split(" — ")[0].strip()   # safe: always has " — " from our format above
    meta=IND_META[ind]; params:dict={}
    if meta["params"]:
        pcols=st.columns(len(meta["params"]))
        for col,(pname,ptype,default,pmin,pmax) in zip(pcols,meta["params"]):
            with col:
                lbl={"period":"Periyot","fast":"Fast","slow":"Slow","signal":"Signal",
                     "std_dev":"Std Sapma","k_period":"K Periyot","d_period":"D Periyot",
                     "smooth":"Düzleştirme","tenkan":"Tenkan","kijun":"Kijun",
                     "senkou_b":"Senkou B","step":"Adım","max_step":"Maks Adım",
                     "atr_mult":"ATR Çarpanı","p1":"Hızlı","p2":"Orta","p3":"Yavaş"}.get(pname,pname)
                if ptype is int:
                    params[pname]=st.number_input(lbl,int(pmin),int(pmax),int(default),key=f"{prefix}_{pname}")
                else:
                    params[pname]=st.number_input(lbl,float(pmin),float(pmax),float(default),step=0.01,key=f"{prefix}_{pname}")
    cond_col,thr_col=st.columns([1.5,1.5])
    with cond_col:
        condition=st.selectbox("Şart",meta["conditions"],key=f"{prefix}_cond")
    threshold:float|None=None
    is_numeric=condition in (">","<",">=","<=")
    with thr_col:
        if is_numeric:
            threshold=st.number_input("Değer",-10000.0,10000.0,
                                       30.0 if ind=="RSI" else 0.0,step=0.5,key=f"{prefix}_thr")
        elif meta.get("cross_targets") and "Kesen" in condition:
            tgt=st.selectbox("Hedef",meta["cross_targets"],key=f"{prefix}_tgt")
            threshold=float(tgt) if tgt.lstrip("-").replace(".","").isdigit() else 0.0
        else:
            st.write("")
    return ind,params,condition,threshold


# ─────────────────────────────────────────────────────────────────────────────
# DATABASE HELPERS  — period column is TEXT (after migration.sql)
# ─────────────────────────────────────────────────────────────────────────────
def _encode_params(ind,params,condition,threshold):
    return json.dumps({"indicator":ind,"params":params,"condition":condition,"threshold":threshold})

def _decode_params(row):
    p=row.get("period","")
    try:
        d=json.loads(str(p))
        if isinstance(d,dict) and "indicator" in d: return d
    except ValueError as e:
        print(f"[DEBUG] Invalid params JSON in row {row.get('indicator')}: {e}")
    return {"indicator":row.get("indicator","RSI"),
            "params":{"period":int(p) if str(p).isdigit() else 14},
            "condition":row.get("condition","<"),"threshold":float(row.get("threshold",30))}

# ─────────────────────────────────────────────────────────────────────────────
# PREFERENCES  — theme + watchlist persistent via Supabase users.preferences
# ─────────────────────────────────────────────────────────────────────────────
def _prefs_load(user: dict) -> None:
    """Load preferences from Supabase or session_state (demo mode fallback)."""
    # SUPABASE JSONB döndürüyor — güvenli parse
    raw_prefs = user.get("preferences", {})
    if isinstance(raw_prefs, str):
        try:
            prefs = json.loads(raw_prefs)
        except:
            prefs = {}
    else:
        prefs = raw_prefs if raw_prefs else {}
    
    # If empty in Supabase, try session_state cache (demo mode)
    if not prefs:
        cached = st.session_state.get(f"_prefs_{user['id']}", "")
        try:
            prefs = json.loads(cached) if cached else {}
        except ValueError as e:
            print(f"[DEBUG] Corrupted preferences JSON in session_state: {e}")
            prefs = {}
    
    # Load theme
    if "theme" in prefs and isinstance(prefs["theme"], dict):
        st.session_state["theme"] = {**DEFAULT_THEME, **prefs["theme"]}
    elif "theme" not in st.session_state:
        st.session_state["theme"] = DEFAULT_THEME.copy()
    
    # Load watchlist
    wl_key = f"wl_{user['id']}"
    if "watchlist" in prefs and isinstance(prefs["watchlist"], list):
        st.session_state[wl_key] = prefs["watchlist"]
    elif wl_key not in st.session_state:
        st.session_state[wl_key] = ["BTC-USD"]
    
    # Load paper trading state
    pb_key = f"paper_balance_{user['id']}"
    pp_key = f"paper_positions_{user['id']}"
    if pb_key not in st.session_state:
        st.session_state[pb_key] = float(prefs.get("paper_balance", 100_000.0))
    if pp_key not in st.session_state:
        st.session_state[pp_key] = dict(prefs.get("paper_positions", {}))


def _prefs_save(user: dict) -> None:
    """Save preferences to Supabase (or session_state fallback if no Supabase)."""
    wl_key = f"wl_{user['id']}"
    pb_key = f"paper_balance_{user['id']}"
    pp_key = f"paper_positions_{user['id']}"
    prefs = {
        "theme":           st.session_state.get("theme", DEFAULT_THEME.copy()),
        "watchlist":       st.session_state.get(wl_key, ["BTC-USD"]),
        "paper_balance":   st.session_state.get(pb_key, 100_000.0),
        "paper_positions": st.session_state.get(pp_key, {}),
    }
    
    # Try Supabase first
    if SUPABASE:
        try:
            res = SUPABASE.table("users").upsert([{
                "id": user["id"],
                "email": user.get("email", ""),
                "preferences": prefs
            }]).execute()
        except Exception as e:
            print(f"[WARN] Failed to upsert preferences to Supabase: {e}")
    
    # Always save to session_state for demo mode persistence
    st.session_state[f"_prefs_{user['id']}"] = json.dumps(prefs)


def db_register(email,pwd):
    if not SUPABASE:
        st.session_state.setdefault("_users",{})
        if email in st.session_state["_users"]: return False,"Bu e-posta kayıtlı."
        st.session_state["_users"][email]=pwd; return True,"ok"
    try:    SUPABASE.auth.sign_up({"email":email,"password":pwd}); return True,"ok"
    except Exception as e: return False,str(e)

def db_login(email, pwd):
    """Login + load preferences from Supabase into session_state."""
    if not SUPABASE:
        u = st.session_state.get("_users", {})
        if email in u and u[email] == pwd:
            # In demo mode, restore cached preferences from session_state
            cached_prefs = st.session_state.get(f"_prefs_{email}", "")
            user = {"id": email, "email": email,
                    "subscription_tier": "free", "telegram_chat_id": "",
                    "preferences": cached_prefs}  # ← Restore from cache
            _prefs_load(user)
            return True, "", user
        return False, "E-posta veya şifre hatalı.", {}
    try:
        r   = SUPABASE.auth.sign_in_with_password({"email": email, "password": pwd})
        uid = r.user.id
        pr  = SUPABASE.table("users").select("*").eq("id", uid).single().execute()
        d   = pr.data or {}
        d.update({"id": uid, "email": email})
        _prefs_load(d)   # ← apply saved theme + watchlist immediately
        return True, "", d
    except Exception as e:
        err = str(e).lower()
        if "email not confirmed" in err:
            return False, "📧 E-posta doğrulanmamış.", {}
        return False, "E-posta veya şifre hatalı.", {}

def db_save_strategy(uid,symbol,ind,params,condition,threshold):
    # str() İPTAL EDİLDİ, JSONB doğrudan dict alıyor
    encoded_dict = _encode_params(ind,params,condition,threshold)
    row=dict(user_id=uid,symbol=symbol,indicator=ind,condition=condition,
             threshold=float(threshold) if threshold is not None else 0.0,
             period=encoded_dict,is_active=True)
    if not SUPABASE:
        st.session_state.setdefault("_strats",[])
        row["id"]=len(st.session_state["_strats"])
        st.session_state["_strats"].append(row); return True
    try:
        SUPABASE.table("strategies").insert(row).execute(); return True
    except Exception as e:
        print(f"[DB ERROR] Strategy insert failed: {e} — saving to session_state")
        st.session_state.setdefault("_strats",[])
        row["id"]=len(st.session_state["_strats"])
        st.session_state["_strats"].append(row)
        return False  # Signal UI of failure but still save locally

def db_get_strategies(uid):
    if not SUPABASE:
        return [s for s in st.session_state.get("_strats",[]) if s["user_id"]==uid]
    try:    return SUPABASE.table("strategies").select("*").eq("user_id",uid).execute().data or []
    except: return []

def db_toggle(sid,active):
    if not SUPABASE:
        for s in st.session_state.get("_strats",[]):
            if s["id"]==sid: s["is_active"]=active
        return
    try:    SUPABASE.table("strategies").update({"is_active":active}).eq("id",sid).execute()
    except: pass


# ─────────────────────────────────────────────────────────────────────────────
# TELEGRAM
# ─────────────────────────────────────────────────────────────────────────────
def send_telegram_alert(symbol,signal,price,indicator,value,chat_id=""):
    token=os.getenv("TELEGRAM_BOT_TOKEN","")
    target=chat_id  # Fallback kaldırıldı — sadece kullanıcının kendi chat_id'si kullanılır
    if not token or not target: return
    msg=(f"🚨 *HisseLab Sinyal*\n\n📌 `{display_sym(symbol)}`\n🔔 *{signal}*\n"
         f"💰 `{price:.4f}`\n📊 {indicator}: `{value:.2f}`\n"
         f"🕐 `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`")
    try: _req.post(f"https://api.telegram.org/bot{token}/sendMessage",
                   data={"chat_id":target,"text":msg,"parse_mode":"Markdown"},timeout=6)
    except: pass


# ─────────────────────────────────────────────────────────────────────────────
# AUTH PAGE
# ─────────────────────────────────────────────────────────────────────────────
def page_auth():
    # ── Centered logo + wordmark ──────────────────────────────────────────────
    if ICON_B64:
        logo_block = (
            f'<img src="data:image/png;base64,{ICON_B64}" '
            f'style="width:70px;height:70px;border-radius:12px;'
            f'object-fit:contain;margin-bottom:.6rem;">'
        )
    else:
        logo_block = ""

    st.markdown(f"""
    <div style="text-align:center;padding:2rem 0 1.4rem">
        {logo_block}
        <div style="font-family:'Space Mono',monospace;font-size:1.7rem;
                    color:var(--acc);letter-spacing:.2em;margin-top:.1rem;">HisseLab</div>
        <div style="font-size:.68rem;color:var(--muted);letter-spacing:.14em;
                    text-transform:uppercase;margin-top:5px;">
            Algoritmik Borsa Analiz Platformu
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Two-column layout ─────────────────────────────────────────────────────
    col_left, col_right = st.columns([1.15, 1], gap="large")

    # LEFT — Value Propositions
    with col_left:
        st.markdown("""
<div style="padding:1rem .6rem 1rem .4rem;">
  <div style="font-family:'Space Mono',monospace;font-size:.66rem;color:var(--acc);
              letter-spacing:.14em;text-transform:uppercase;margin-bottom:1.2rem;
              border-bottom:1px solid var(--brd);padding-bottom:.5rem;">
    Neden HisseLab?
  </div>
  <div style="display:flex;flex-direction:column;gap:1.1rem;">
    <div style="display:flex;gap:.85rem;align-items:flex-start;">
      <div style="font-size:1.3rem;line-height:1.1;min-width:26px;">📊</div>
      <div>
        <div style="color:var(--txt);font-size:.83rem;font-weight:600;margin-bottom:.15rem;">
          TradingView Entegrasyonu</div>
        <div style="color:var(--muted);font-size:.74rem;line-height:1.55;">
          Profesyonel, gerçek zamanlı grafikler. Onlarca indikatör ve çizim aracı.</div>
      </div>
    </div>
    <div style="display:flex;gap:.85rem;align-items:flex-start;">
      <div style="font-size:1.3rem;line-height:1.1;min-width:26px;">🧪</div>
      <div>
        <div style="color:var(--txt);font-size:.83rem;font-weight:600;margin-bottom:.15rem;">
          20+ İndikatör & Backtest</div>
        <div style="color:var(--muted);font-size:.74rem;line-height:1.55;">
          RSI, MACD, Ichimoku, Bollinger ve daha fazlası. 5 yıllık veriyle test edin.</div>
      </div>
    </div>
    <div style="display:flex;gap:.85rem;align-items:flex-start;">
      <div style="font-size:1.3rem;line-height:1.1;min-width:26px;">⚡</div>
      <div>
        <div style="color:var(--txt);font-size:.83rem;font-weight:600;margin-bottom:.15rem;">
          7/24 Kesintisiz Tarama</div>
        <div style="color:var(--muted);font-size:.74rem;line-height:1.55;">
          Arka planda çalışan algoritmalar piyasayı sürekli tarar.</div>
      </div>
    </div>
    <div style="display:flex;gap:.85rem;align-items:flex-start;">
      <div style="font-size:1.3rem;line-height:1.1;min-width:26px;">📱</div>
      <div>
        <div style="color:var(--txt);font-size:.83rem;font-weight:600;margin-bottom:.15rem;">
          Anlık Telegram Bildirimleri</div>
        <div style="color:var(--muted);font-size:.74rem;line-height:1.55;">
          Kuralınız tetiklendiği saniye cebinize bildirim gelir.</div>
      </div>
    </div>
    <div style="display:flex;gap:.85rem;align-items:flex-start;">
      <div style="font-size:1.3rem;line-height:1.1;min-width:26px;">🏦</div>
      <div>
        <div style="color:var(--txt);font-size:.83rem;font-weight:600;margin-bottom:.15rem;">
          500+ BIST & Global Piyasalar</div>
        <div style="color:var(--muted);font-size:.74rem;line-height:1.55;">
          BIST, kripto, S&P 500, DAX ve emtialar tek ekranda.</div>
      </div>
    </div>
  </div>
</div>""", unsafe_allow_html=True)

    # RIGHT — Login / Register form (clean, no wrapper frames)
    with col_right:
        t_li, t_re = st.tabs(["🔑 Giriş Yap", "✅ Kayıt Ol"])

        with t_li:
            email = st.text_input("E-posta", key="li_e", placeholder="ornek@mail.com")
            pwd   = st.text_input("Şifre",   key="li_p", type="password")
            if st.button("Giriş Yap", key="btn_li", use_container_width=True):
                if not email or not pwd:
                    st.error("Tüm alanları doldurunuz.")
                else:
                    ok, err, user = db_login(email, pwd)
                    if ok: st.session_state["user"] = user; st.rerun()
                    else:  st.error(err)
            if not SUPABASE:
                st.info("🔔 Demo Mod aktif — Supabase bağlantısı yok.", icon="ℹ️")

        with t_re:
            re  = st.text_input("E-posta",        key="re_e", placeholder="ornek@mail.com")
            rp  = st.text_input("Şifre",          key="re_p",  type="password")
            rp2 = st.text_input("Şifre (tekrar)", key="re_p2", type="password")
            if st.button("Hesap Oluştur", key="btn_re", use_container_width=True):
                if not re or not rp:  st.error("Tüm alanları doldurunuz.")
                elif rp != rp2:       st.error("Şifreler eşleşmiyor.")
                else:
                    ok, err = db_register(re, rp)
                    if ok: st.success("✅ Kayıt başarılı! Giriş yap sekmesinden devam et.")
                    else:  st.error(err)


# ─────────────────────────────────────────────────────────────────────────────
# SIDEBAR  — with base64 logo
# ─────────────────────────────────────────────────────────────────────────────
def sidebar(user)->str:
    with st.sidebar:
        logo_html=""
        if ICON_B64:
            logo_html=(f'<div class="logo-inner">'
                       f'<img class="logo-img" src="data:image/png;base64,{ICON_B64}">'
                       f'<span class="logo-t">HisseLab</span></div>')
        else:
            logo_html='<div class="logo-inner"><span class="logo-t">📈 HisseLab</span></div>'

        st.markdown(f"""<div class="logo">
            {logo_html}
            <div class="logo-s">{user.get('subscription_tier','free').upper()} PLAN</div>
        </div>""",unsafe_allow_html=True)

        st.markdown(f'<div style="font-size:.66rem;color:var(--muted);text-align:center;'
                    f'margin-bottom:.8rem;font-family:\'Space Mono\',monospace;">'
                    f'👤 {user.get("email","")[:28]}</div>',unsafe_allow_html=True)
        st.markdown("---")
        st.markdown('<p style="font-size:.56rem;letter-spacing:.14em;color:var(--muted);'
                    'text-transform:uppercase;padding-left:2px;margin-bottom:.2rem;">Menü</p>',
                    unsafe_allow_html=True)
        page=st.radio("nav",["📊  Dashboard","🧪  Backtest","⚡  Canlı Sinyaller","🎨  Tema & Ayarlar"],
                      label_visibility="collapsed")
        st.markdown("---")
        st.markdown(
            '<div style="font-size:.62rem;color:var(--muted);text-align:center;'
            'line-height:1.6;font-family:\'Space Mono\',monospace;letter-spacing:.04em;">'
            'Algoritmik Karar Destek Sistemi<br>'
            '<span style="font-size:.54rem;opacity:.6;">20 İndikatör · Backtest · Sinyal</span>'
            '</div>',
            unsafe_allow_html=True)
        st.markdown("---")
        if st.button("🚪 Çıkış",key="logout"):
            for k in ["user","signal_log"]: st.session_state.pop(k,None)
            st.rerun()
        st.markdown(f'<div style="font-size:.54rem;color:var(--muted);text-align:center;'
                    f'font-family:\'Space Mono\',monospace;margin-top:.4rem;">'
                    f'v11.0 · {datetime.now().strftime("%Y-%m-%d")}</div>',unsafe_allow_html=True)
    return page


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: DASHBOARD
# ─────────────────────────────────────────────────────────────────────────────
def page_dashboard(user):
    sh("📊","Market Dashboard")

    # ── Two top-level tabs ─────────────────────────────────────────────────────
    tab_chart, tab_heat = st.tabs(["📈 Grafikler", "\U0001f5fa\ufe0f Isı Haritası"])

    with tab_chart:
        col_w,col_b=st.columns([1,1],gap="medium")
        # ── WATCHLIST ─────────────────────────────────────────────────────────────
        with col_w:
            wl_key=f"wl_{user['id']}"
            if wl_key not in st.session_state:
                st.session_state[wl_key]=["BTC-USD"]
            wl:list=st.session_state[wl_key]

            st.markdown("##### 📌 Takip Listem")

            # Autocomplete selectbox — BIST + crypto merged for watchlist add
            markets=get_markets()
            all_bist=markets.get("🏦 BIST Tüm Hisseler",_BIST_FALLBACK)
            all_crypto=STATIC_MARKETS.get("🪙 Kripto (USD)",[])
            add_pool=all_bist+all_crypto+STATIC_MARKETS.get("🇺🇸 S&P 500",[])
            display_pool=[display_sym(s) for s in add_pool]

            add_c,btn_c=st.columns([4,1])
            with add_c:
                chosen_d=st.selectbox("",display_pool,key="wl_add_sel",label_visibility="collapsed")
            with btn_c:
                if st.button("＋",key="wl_add"):
                    # Map display → API sym
                    try:
                        pos=display_pool.index(chosen_d); api_s=add_pool[pos]
                    except ValueError:
                        api_s=chosen_d+".IS"
                    if api_s and api_s not in wl:
                        wl.append(api_s); st.session_state[wl_key]=wl
                        _prefs_save(user)
                        fetch_quick_quote.clear(); st.rerun()

            # Header
            h1,h2,h3,h4=st.columns([0.5,4,2.5,2])
            for h,lbl in zip([h2,h3,h4],["Sembol","Fiyat","Değişim"]):
                h.markdown(f'<span style="font-size:.58rem;color:var(--muted);font-family:\'Space Mono\','
                           f'monospace;text-transform:uppercase;letter-spacing:.08em;">{lbl}</span>',
                           unsafe_allow_html=True)

            # ── Watchlist pagination ──────────────────────────────────────────
            n_pg_wl = max(1, (len(wl) + PAGE_SIZE - 1) // PAGE_SIZE)
            if "pg_wl" not in st.session_state: st.session_state["pg_wl"] = 0
            pg_wl = min(st.session_state["pg_wl"], n_pg_wl - 1)
            st.session_state["pg_wl"] = pg_wl
            page_wl = wl[pg_wl * PAGE_SIZE : (pg_wl + 1) * PAGE_SIZE]

            to_rm=None
            for idx, sym in enumerate(page_wl):
                q=fetch_quick_quote(sym)
                pr=f"{q['price']:.4f}" if q["price"] else "—"
                if q["change"] is not None:
                    sg="+" if q["change"]>=0 else ""; chg=f"{sg}{q['change']:.2f}%"
                    chg_clr="var(--grn)" if q["change"]>=0 else "var(--red)"
                else: chg="—"; chg_clr="var(--muted)"
                c_x,c_s,c_p,c_c=st.columns([0.5,4,2.5,2],gap="small")
                with c_x:
                    if st.button("✖",key=f"rm_{idx}_{sym}",help=f"{display_sym(sym)} kaldır",type="tertiary"):
                        to_rm=wl.index(sym)
                with c_s:
                    st.markdown(
                        f'<div class="tbl-row-cell"><span style="color:var(--acc);'
                        f'font-family:\'Space Mono\',monospace;font-size:.78rem;'
                        f'font-weight:600;">{display_sym(sym)}</span></div>',
                        unsafe_allow_html=True)
                with c_p:
                    st.markdown(
                        f'<div class="tbl-row-cell"><span style="font-family:\'Space Mono\','
                        f'monospace;color:var(--txt);font-size:.78rem;">{pr}</span></div>',
                        unsafe_allow_html=True)
                with c_c:
                    st.markdown(
                        f'<div class="tbl-row-cell"><span style="font-family:\'Space Mono\','
                        f'monospace;color:{chg_clr};font-size:.78rem;">{chg}</span></div>',
                        unsafe_allow_html=True)

            render_pagination(pg_wl, n_pg_wl, "pg_wl")

            if to_rm is not None:
                wl.pop(to_rm); st.session_state[wl_key]=wl
                _prefs_save(user); st.rerun()

        # ── MARKET BROWSER with GLOBAL SORT ──────────────────────────────────────
        with col_b:
            st.markdown("##### 🌐 Borsa & Piyasa Tarayıcı")

            markets=get_markets()
            market=st.selectbox("",list(markets.keys()),key="mkt_sel",label_visibility="collapsed")
            syms=markets[market]

            # ── Sort headers — ALL THREE are identical tertiary ghost buttons ──────
            sort_key=f"sort_{market}"; sort_dir_key=f"sort_dir_{market}"
            if sort_key     not in st.session_state: st.session_state[sort_key]="none"
            if sort_dir_key not in st.session_state: st.session_state[sort_dir_key]="desc"
            cur_sort=st.session_state[sort_key]; cur_dir=st.session_state[sort_dir_key]

            def _sort_lbl(field, name):
                """Return button label with directional arrow when this field is active."""
                if cur_sort == field:
                    return name + (" ↓" if cur_dir == "desc" else " ↑")
                return name

            def _do_sort(field):
                """Toggle or activate sort on field; reset page to 0."""
                if cur_sort == field:
                    st.session_state[sort_dir_key] = "asc" if cur_dir == "desc" else "desc"
                else:
                    st.session_state[sort_key] = field
                    # Alphabetical sort defaults to A→Z (asc), numeric defaults to high→low (desc)
                    st.session_state[sort_dir_key] = "asc" if field == "sym" else "desc"
                st.session_state[f"pg_{market}"] = 0

            # ── Batch fetch — ALWAYS fetch to filter dead stocks ─────
            batch = fetch_batch_quotes(tuple(syms))

            # ── Critical filter: Remove stocks with no price data BEFORE sorting ──
            syms_with_data = [s for s in syms if batch.get(s, {}).get("price") is not None]

            # ── Sort the filtered list ─────────────────────────────────────────────
            if cur_sort in ("price", "change"):
                def sort_val(s):
                    q = batch.get(s, {}); v = q.get(cur_sort) if q else None
                    return v if v is not None else float("-inf")
                sorted_syms = sorted(syms_with_data, key=sort_val,
                                     reverse=(cur_dir == "desc"))
            elif cur_sort == "sym":
                # Alphabetical sort on display symbol (no API call needed)
                sorted_syms = sorted(syms_with_data,
                                     key=lambda s: display_sym(s).upper(),
                                     reverse=(cur_dir == "desc"))
            else:
                sorted_syms = syms_with_data

            n_pg=max(1,(len(sorted_syms)+PAGE_SIZE-1)//PAGE_SIZE)
            pgk=f"pg_{market}"
            if pgk not in st.session_state: st.session_state[pgk]=0
            pg=min(st.session_state[pgk],n_pg-1); st.session_state[pgk]=pg
            page_syms=sorted_syms[pg*PAGE_SIZE:(pg+1)*PAGE_SIZE]

            # ── Sort header buttons — gap="small" pulls them close to rows ──────────
            hc1, hc2, hc3 = st.columns([2, 1.4, 1.4], gap="small")
            with hc1:
                if st.button(_sort_lbl("sym", "Sembol"), key="sort_sym_btn",
                             type="tertiary", help="Sembole göre alfabetik sırala"):
                    _do_sort("sym"); st.rerun()
            with hc2:
                if st.button(_sort_lbl("price", "Fiyat"), key="sort_price_btn",
                             type="tertiary", help="Fiyata göre sırala"):
                    _do_sort("price"); st.rerun()
            with hc3:
                if st.button(_sort_lbl("change", "Değişim"), key="sort_chg_btn",
                             type="tertiary", help="Değişime göre sırala"):
                    _do_sort("change"); st.rerun()

            # ── Hisse rows — directly below headers, zero gap ─────────────────────
            for sym in page_syms:
                q = batch.get(sym) or fetch_quick_quote(sym)
                pr = f"{q['price']:.4f}" if q.get("price") else "—"
                if q.get("change") is not None:
                    sg = "+" if q["change"] >= 0 else ""
                    chg_str = f"{sg}{q['change']:.2f}%"
                    chg_clr = "var(--grn)" if q["change"] >= 0 else "var(--red)"
                else:
                    chg_str = "—"; chg_clr = "var(--muted)"
                r1, r2, r3 = st.columns([2, 1.5, 1.5])
                with r1:
                    st.markdown(
                        f'<div class="tbl-row-cell"><span style="color:var(--acc);'
                        f'font-family:\'Space Mono\',monospace;font-size:.78rem;'
                        f'font-weight:600;">{display_sym(sym)}</span></div>',
                        unsafe_allow_html=True)
                with r2:
                    st.markdown(
                        f'<div class="tbl-row-cell"><span style="font-family:\'Space Mono\','
                        f'monospace;color:var(--txt);font-size:.78rem;">{pr}</span></div>',
                        unsafe_allow_html=True)
                with r3:
                    st.markdown(
                        f'<div class="tbl-row-cell"><span style="font-family:\'Space Mono\','
                        f'monospace;color:{chg_clr};font-size:.78rem;">{chg_str}</span></div>',
                        unsafe_allow_html=True)

            # ── Sembol count BELOW rows, ABOVE pagination ─────────────────────────
            st.markdown(
                f'<div style="font-size:.6rem;color:var(--muted);margin:.3rem 0 .1rem;'
                f'font-family:\'Space Mono\',monospace;">'
                f'{len(sorted_syms)} sembol · sayfa {pg+1}/{n_pg}</div>',
                unsafe_allow_html=True)

            render_pagination(pg,n_pg,pgk)

        # ── SANAL PORTFÖY — iki tablonun altında, tam genişlik ────────────────────
        st.markdown("<hr style='margin:.5rem 0;'>", unsafe_allow_html=True)
        sh("💼", "Sanal Portföy")

        pb_key = f"paper_balance_{user['id']}"; pp_key = f"paper_positions_{user['id']}"
        bal = st.session_state.get(pb_key, 100_000.0)
        pos = st.session_state.get(pp_key, {})

        bal_c, reset_c = st.columns([5, 1])
        with bal_c:
            st.markdown(
                f'<div style="font-size:.8rem;color:var(--acc);font-family:\'Space Mono\','
                f'monospace;margin-bottom:.4rem;">💵 Nakit: <b>${bal:,.2f}</b></div>',
                unsafe_allow_html=True)
        with reset_c:
            if st.button("↺ Sıfırla", key="dash_paper_reset", help="Portföyü sıfırla"):
                st.session_state[pb_key] = 100_000.0; st.session_state[pp_key] = {}
                _prefs_save(user); st.rerun()

        # ── Hızlı alım formu ──────────────────────────────────────────────────────
        with st.expander("➕ Portföye Ekle", expanded=False):
            fa, fb, fc, fd = st.columns([3, 1.5, 1.5, 1])
            with fa:
                all_syms_p = sorted(set(all_bist + all_crypto + STATIC_MARKETS.get("🇺🇸 S&P 500",[])))
                add_sym_api = sym_selectbox("Sembol", all_syms_p, key="port_add_sym")
            with fb:
                add_q = fetch_quick_quote(add_sym_api)
                add_price = add_q["price"] or 0.0
                st.markdown(
                    f'<div style="padding:.35rem 0;font-size:.75rem;font-family:\'Space Mono\',monospace;">'
                    f'<span style="color:var(--muted);font-size:.58rem;">Son Fiyat</span><br>'
                    f'<span style="color:var(--acc);">${add_price:.4f}</span></div>',
                    unsafe_allow_html=True)
            with fc:
                add_amount = st.number_input("Tutar ($)", min_value=10.0, max_value=float(bal) if bal > 10 else 10.0,
                                             value=1000.0, step=100.0, key="port_add_amount")
            with fd:
                st.markdown('<div style="height:1.6rem;"></div>', unsafe_allow_html=True)
                if st.button("📥 Ekle", key="port_add_btn", use_container_width=True):
                    if add_price > 0:
                        msg = paper_buy(user, add_sym_api, add_price, add_amount)
                        st.success(msg); st.rerun()
                    else:
                        st.error("Fiyat alınamadı.")

        # ── Portföy tablosu ───────────────────────────────────────────────────────
        if not pos:
            st.markdown(
                '<div style="color:var(--muted);font-size:.78rem;padding:.5rem;">Portföy boş.</div>',
                unsafe_allow_html=True)
        else:
            ph1,ph2,ph3,ph4,ph5,ph6,ph7 = st.columns([1.8,1.4,1.4,1.2,1.4,1.4,0.8])
            for col,lbl in zip([ph1,ph2,ph3,ph4,ph5,ph6],
                               ["Sembol","Maliyet","Güncel","Adet","Toplam Değer","K/Z ($)"]):
                col.markdown(
                    f'<span style="font-size:.58rem;color:var(--muted);font-family:\'Space Mono\','
                    f'monospace;text-transform:uppercase;">{lbl}</span>',
                    unsafe_allow_html=True)

            to_sell = None
            for sym, data in pos.items():
                q = fetch_quick_quote(sym)
                cur_p = q["price"]
                if not cur_p: continue
                ep   = data.get("entry", 0.0)
                qty  = data.get("qty", 0.0)
                cost = ep * qty
                cur_val = cur_p * qty
                pnl_usd = cur_val - cost
                pnl_pct = (cur_p - ep) / ep * 100 if ep > 0 else 0.0
                clr = "var(--grn)" if pnl_usd >= 0 else "var(--red)"
                sgn = "+" if pnl_usd >= 0 else ""

                c1,c2,c3,c4,c5,c6,c7 = st.columns([1.8,1.4,1.4,1.2,1.4,1.4,0.8])
                c1.markdown(f"<div class='tbl-row-cell' style='color:var(--acc);font-family:\'Space Mono\',monospace;font-size:.75rem;'>{display_sym(sym)}</div>", unsafe_allow_html=True)
                c2.markdown(f"<div class='tbl-row-cell' style='font-size:.75rem;'>${ep:.2f}</div>", unsafe_allow_html=True)
                c3.markdown(f"<div class='tbl-row-cell' style='font-size:.75rem;'>${cur_p:.2f}</div>", unsafe_allow_html=True)
                c4.markdown(f"<div class='tbl-row-cell' style='font-size:.75rem;color:var(--txt2);'>{qty:.4f}</div>", unsafe_allow_html=True)
                c5.markdown(f"<div class='tbl-row-cell' style='font-size:.75rem;'>${cur_val:,.2f}</div>", unsafe_allow_html=True)
                c6.markdown(f"<div class='tbl-row-cell' style='color:{clr};font-size:.75rem;'>{sgn}${pnl_usd:,.2f} ({sgn}{pnl_pct:.1f}%)</div>", unsafe_allow_html=True)
                with c7:
                    if st.button("Sat", key=f"dash_sell_{sym}", type="tertiary"):
                        to_sell = sym
            if to_sell:
                paper_sell(user, to_sell, fetch_quick_quote(to_sell)["price"])
                st.rerun()

        # ── PRICE CHART — Lightweight Charts (BIST-safe, multi-indicator) ───────────
        sh("📈","Fiyat Grafiği")

        # Row 1: Symbol | Timeframe | Refresh
        sc, tf_c, bc = st.columns([3, 1.2, 0.8])
        with sc:
            all_syms = sorted(set(all_bist + all_crypto + STATIC_MARKETS.get("🇺🇸 S&P 500", [])))
            all_disp = [display_sym(s) for s in all_syms]
            try:    def_idx = all_disp.index("BTC")
            except: def_idx = 0
            chosen_d = st.selectbox("", all_disp, index=def_idx, key="csym_sel",
                                    label_visibility="collapsed")
            try:    pos = all_disp.index(chosen_d); csym = all_syms[pos]
            except: csym = "BTC-USD"
        with tf_c:
            dash_interval, dash_period = tf_selectbox("dash_tf")
        with bc:
            if st.button("⟳ Yenile", key="cfetch"):
                fetch_price_data.clear(); fetch_ticker_info.clear()

        # Row 2: Indicator popover | Volume toggle
        pop_c, vol_c = st.columns([3, 1])
        with pop_c:
            sel_inds = [ind for ind in OVERLAY_INDS if st.session_state.get(f"dash_chk_{ind}", False)]
            active_count = len(sel_inds)
            pop_label = f"⚙️ İndikatörler{f'  ·  {active_count} aktif' if active_count else ''}"
            with st.popover(pop_label, use_container_width=False):
                st.markdown('<div style="font-size:.62rem;color:var(--muted);font-family:\'Space Mono\',monospace;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.5rem;">Overlay İndikatörler</div>', unsafe_allow_html=True)
                pc1, pc2 = st.columns(2)
                for i, ind_name in enumerate(OVERLAY_INDS):
                    col = pc1 if i % 2 == 0 else pc2
                    with col:
                        st.checkbox(ind_name, key=f"dash_chk_{ind_name}")
                if active_count and st.button("✕ Tümünü Kaldır", key="pop_clear_inds"):
                    for ind_name in OVERLAY_INDS:
                        st.session_state[f"dash_chk_{ind_name}"] = False
                    st.rerun()
        with vol_c:
            sep_vol = st.toggle("Hacmi Ayrı Panelde", value=st.session_state.get("dash_sep_vol", False), key="dash_sep_vol")

        df = fetch_price_data(csym, period=dash_period, interval=dash_interval)
        if df is not None and not df.empty and len(df) >= 2:
            last = float(df["Close"].iloc[-1]); prev = float(df["Close"].iloc[-2])
            pct  = (last - prev) / prev * 100;  vol  = float(df["Volume"].iloc[-1])
            info = fetch_ticker_info(csym)
            m1, m2, m3, m4 = st.columns(4)
            with m1: mc("Son Fiyat",  f"{last:.2f}", info.get("currency","TRY"), "mc-blue")
            with m2: mc("Günlük %",   f"{'+'if pct>=0 else''}{pct:.2f}%", "", "mc-green" if pct>=0 else "mc-red")
            with m3: mc("52H Yüksek", f"{df['Close'].max():.2f}", "")
            with m4: mc("Hacim",      f"{vol/1e6:.1f}M" if vol > 1e6 else f"{vol:,.0f}", "")
            chart_dashboard_lwc(df, csym, overlay_inds=list(sel_inds), sep_vol=st.session_state.get("dash_sep_vol", False))
        else:
            st.warning(f"'{display_sym(csym)}' için veri bulunamadı.")

    with tab_heat:
        sh("\U0001f5fa\ufe0f","BIST Sıcaklık Haritası")
        _mkts=get_markets()
        _bist_heat=_mkts.get("\U0001f3e6 BIST Tüm Hisseler",_BIST_FALLBACK)
        ht_mkt=st.selectbox("Piyasa",["\U0001f3e6 BIST Tüm Hisseler","\U0001f1fa\U0001f1f8 S&P 500","\U0001fa99 Kripto (USD)"],key="heat_mkt")
        if ht_mkt=="\U0001f3e6 BIST Tüm Hisseler":
            heat_syms=_bist_heat
        elif ht_mkt=="\U0001f1fa\U0001f1f8 S&P 500":
            heat_syms=STATIC_MARKETS.get("\U0001f1fa\U0001f1f8 S&P 500",[])
        else:
            heat_syms=STATIC_MARKETS.get("\U0001fa99 Kripto (USD)",[])
        render_heatmap(heat_syms)



# ─────────────────────────────────────────────────────────────────────────────
# PAPER TRADING HELPERS
# ─────────────────────────────────────────────────────────────────────────────
def paper_buy(user: dict, symbol: str, price: float, amount: float = 1000.0) -> str:
    pb = f"paper_balance_{user['id']}"; pp = f"paper_positions_{user['id']}"
    bal = st.session_state.get(pb, 100_000.0)
    pos = st.session_state.get(pp, {})
    if bal < amount: return f"⚠ Bakiye yetersiz (${bal:,.0f} < ${amount:,.0f})"
    qty = amount / price
    if symbol in pos:
        old_qty = pos[symbol]["qty"]
        old_cost = pos[symbol]["entry"] * old_qty
        new_qty = old_qty + qty
        new_entry = (old_cost + amount) / new_qty
        pos[symbol] = {"qty": new_qty, "entry": new_entry}
    else:
        pos[symbol] = {"qty": qty, "entry": price}
    st.session_state[pb] = bal - amount
    st.session_state[pp] = pos
    _prefs_save(user)
    return f"✅ AL: {display_sym(symbol)} | ${amount:,.0f} | Ort: ${pos[symbol]['entry']:.2f}"


def paper_sell(user: dict, symbol: str, price: float) -> str:
    pb = f"paper_balance_{user['id']}"; pp = f"paper_positions_{user['id']}"
    bal = st.session_state.get(pb, 100_000.0)
    pos = st.session_state.get(pp, {})
    if symbol not in pos: return f"⚠ {display_sym(symbol)} elde yok."
    qty = pos[symbol]["qty"]; ep = pos[symbol]["entry"]
    proceeds = qty * price
    pnl_pct = (price - ep) / ep * 100
    st.session_state[pb] = bal + proceeds
    del pos[symbol]
    st.session_state[pp] = pos
    _prefs_save(user)
    return f"✅ SAT: {display_sym(symbol)} | K/Z: {'+' if pnl_pct>=0 else ''}{pnl_pct:.2f}%"


# ─────────────────────────────────────────────────────────────────────────────
# HEATMAP
# ─────────────────────────────────────────────────────────────────────────────
def render_heatmap(syms: list) -> None:
    """Render Plotly Treemap heatmap from batch quote data."""
    if not syms:
        st.info("Veri yok."); return
    with st.spinner(f"Isı haritası için {len(syms)} sembol çekiliyor…"):
        batch = fetch_batch_quotes(tuple(syms[:200]))  # cap at 200 for speed
    rows = []
    for s in syms[:200]:
        q = batch.get(s) or {"price": None, "change": None}
        if q.get("change") is not None:
            rows.append({"sym": display_sym(s), "chg": round(q["change"], 2),
                         "val": max(abs(q["change"]), 0.1)})
    if not rows:
        st.warning("Fiyat verisi alınamadı."); return
    df_h = pd.DataFrame(rows)
    fig = px.treemap(
        df_h, path=["sym"], values="val", color="chg",
        color_continuous_scale=[(0,"#c0392b"),(0.5,"#1e2d45"),(1,"#27ae60")],
        color_continuous_midpoint=0,
        custom_data=["chg"],
    )
    fig.update_traces(
        texttemplate="<b>%{label}</b><br>%{customdata[0]:.2f}%",
        textfont=dict(family="Space Mono", size=11),
        hovertemplate="<b>%{label}</b><br>Değişim: %{customdata[0]:.2f}%<extra></extra>",
    )
    fig.update_layout(
        paper_bgcolor="#111827", plot_bgcolor="#111827",
        font=dict(color="#c8d6e8"),
        margin=dict(l=0,r=0,t=0,b=0),
        height=480,
        coloraxis_showscale=False,
    )
    st.plotly_chart(fig, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: BACKTEST
# ─────────────────────────────────────────────────────────────────────────────
def page_backtest():
    sh("🧪","Analiz Laboratuvarı")
    markets=get_markets()
    all_bist=markets.get("🏦 BIST Tüm Hisseler",_BIST_FALLBACK)
    pool=sorted(set(all_bist+STATIC_MARKETS.get("🇺🇸 S&P 500",[])+STATIC_MARKETS.get("🪙 Kripto (USD)",[])))
    disp=[display_sym(s) for s in pool]

    col_form, col_results = st.columns([1, 2.5], gap="medium")

    # ── LEFT: Form Panel ──────────────────────────────────────────────────────
    with col_form:
        st.markdown('<div style="font-size:.62rem;color:var(--acc);font-family:\'Space Mono\','
                    'monospace;text-transform:uppercase;letter-spacing:.12em;'
                    'margin-bottom:.5rem;">⚙️ Strateji Parametreleri</div>',unsafe_allow_html=True)

        try: def_i=disp.index("ASELS")
        except: def_i=0
        ch=st.selectbox("Sembol",disp,index=def_i,key="bsym_sel",label_visibility="visible")
        try: pos=disp.index(ch); bsym=pool[pos]
        except: bsym="ASELS.IS"

        st.markdown('<span style="font-size:.65rem;color:var(--muted);font-family:\'Space Mono\','
                    'monospace;text-transform:uppercase;">Zaman Dilimi</span>',unsafe_allow_html=True)
        bt_interval, bt_period = tf_selectbox("bt_tf")

        # ── Tarih Aralığı Seçimi ──────────────────────────────────────────────
        from datetime import datetime, timedelta
        today = datetime.now().date()
        two_years_ago = today - timedelta(days=730)
        
        d1, d2 = st.columns(2)
        with d1:
            # Başlangıç tarihi bugünden ileri olamaz
            bt_start = st.date_input("Başlangıç", value=two_years_ago, max_value=today, key="bt_start")
        with d2:
            # Bitiş tarihi, başlangıç tarihinden eski olamaz ve bugünden ileri olamaz
            bt_end = st.date_input("Bitiş", value=today, min_value=bt_start, max_value=today, key="bt_end")

        st.markdown('<div style="font-size:.62rem;color:var(--muted);font-family:\'Space Mono\','
                    'monospace;text-transform:uppercase;letter-spacing:.1em;margin-bottom:.2rem;margin-top:.5rem;">'
                    '1. Şart</div>',unsafe_allow_html=True)
        bind,bparams,bcond,bthr=indicator_form("bt")

        # ── Ek Şart (AND logic) ──────────────────────────────────────────────
        use_cond2 = st.toggle("➕ Ek Şart Ekle (AND)", value=False, key="bt_use_cond2")
        bind2=bparams2=bcond2=bthr2=None
        if use_cond2:
            st.markdown('<div style="font-size:.62rem;color:var(--gld);font-family:\'Space Mono\','
                        'monospace;text-transform:uppercase;letter-spacing:.1em;margin:.3rem 0 .2rem;">'
                        '2. Şart (AND)</div>',unsafe_allow_html=True)
            bind2,bparams2,bcond2,bthr2=indicator_form("bt2")

        c1, c2, c3 = st.columns(3)
        with c1:
            cap=st.number_input("Sermaye ($)",100.0,value=10_000.0,step=500.0,key="bt_cap")
        with c2:
            tp=st.number_input("Kâr Al (%) (0=İptal)",0.0,100.0,0.0,step=0.5,key="bt_tp")
        with c3:
            sl=st.number_input("Zarar Durdur (%) (0=İptal)",0.0,100.0,0.0,step=0.5,key="bt_sl")
        
        run=st.button("▶ TESTİ ÇALIŞTIR",key="run_bt",use_container_width=True)

    # ── RIGHT: Results ────────────────────────────────────────────────────────
    with col_results:
        if run:
            with st.spinner("Veri indiriliyor…"):
                df=fetch_price_data(bsym, period=bt_period, interval=bt_interval)
            if df is None:
                st.error(f"'{display_sym(bsym)}' için veri bulunamadı."); return
            
            # ── Tarih aralığına göre veriyi filtrele ──────────────────────────────
            # DataFrame indexini tz-naive yap (timezone uyumsuzluğu sorunu)
            if df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            
            start_dt = pd.to_datetime(bt_start)
            end_dt = pd.to_datetime(bt_end)
            df = df.loc[start_dt:end_dt]
            if df.empty:
                st.error("Seçilen tarih aralığında veri bulunamadı."); return
            
            with st.spinner("Simülasyon çalışıyor…"):
                res=run_backtest(df,bind,bparams,bcond,bthr,float(cap),
                                 bind2,bparams2,bcond2,bthr2, float(tp), float(sl))
            st.session_state["_bt_res"]=res

        res=st.session_state.get("_bt_res")
        if res is None:
            st.markdown('<div style="color:var(--muted);font-size:.82rem;padding:3rem;'
                        'text-align:center;">← Sol panelden parametreleri ayarlayın ve testi çalıştırın.</div>',
                        unsafe_allow_html=True)
            return

        sign="+" if res["total_return"]>=0 else ""
        m1,m2,m3 = st.columns(3)
        with m1: mc("Toplam K/Z",f"{sign}{res['total_return']:.2f}%","",
                    "mc-green" if res["total_return"]>=0 else "mc-red")
        with m2: mc("Başlangıç / Bitiş",
                    f"${res['initial_capital']:,.0f} → ${res['final_capital']:,.0f}","","mc-blue")
        with m3: mc("Max Drawdown",f"{res['max_drawdown']:.2f}%","","mc-red")

        m4,m5 = st.columns(2)
        with m4:
            mc("Kazanma Oranı",f"{res['win_rate']:.1f}%",f"{res['num_trades']} işlem","mc-gold")
            st.progress(min(res["win_rate"]/100.0, 1.0))
        with m5:
            mc("İşlem Sayısı",str(res["num_trades"]),"")

        # ── LWC Chart ─────────────────────────────────────────────────────────
        # raw entry yerine sadece gerçekleşen trade'leri al
        entry_s=res["df"]["trade_entry"] if "trade_entry" in res["df"].columns else None
        exit_s =res["df"]["trade_exit"]  if "trade_exit"  in res["df"].columns else None
        chart_with_indicator_lwc(res["df"], bsym, bind, bparams, entry_s, exit_s)
        st.plotly_chart(chart_equity(res),use_container_width=True)

        # ── Trade Journal ──────────────────────────────────────────────────────
        st.markdown('<div style="font-size:.62rem;color:var(--acc);font-family:\'Space Mono\','
                    'monospace;text-transform:uppercase;letter-spacing:.12em;margin:.5rem 0 .3rem;">'
                    '📒 İşlem Günlüğü</div>',unsafe_allow_html=True)

        df_j=res["df"]; trades_rows=[]
        in_trade=False; entry_date=None; entry_price=0.0
        for date,row in df_j.iterrows():
            p=float(row["Close"])
            if not in_trade and bool(row.get("entry",False)):
                in_trade=True; entry_date=date; entry_price=p
            elif in_trade and bool(row.get("exit",False)):
                pnl=(p-entry_price)/entry_price*100
                trades_rows.append({
                    "entry_date": entry_date.strftime("%Y-%m-%d") if hasattr(entry_date,"strftime") else str(entry_date),
                    "exit_date":  date.strftime("%Y-%m-%d") if hasattr(date,"strftime") else str(date),
                    "entry_price": entry_price, "exit_price": p, "pnl": pnl
                })
                in_trade=False

        if trades_rows:
            rows_html=""
            for t in trades_rows[-50:][::-1]:  # show last 50 reversed
                pnl_cls="tj-win" if t["pnl"]>=0 else "tj-loss"
                sign2="+" if t["pnl"]>=0 else ""
                rows_html+=(f"<tr>"
                    f"<td class='tj-buy'>{t['entry_date']}</td>"
                    f"<td class='tj-buy'>${t['entry_price']:.4f}</td>"
                    f"<td class='tj-sell'>{t['exit_date']}</td>"
                    f"<td class='tj-sell'>${t['exit_price']:.4f}</td>"
                    f"<td class='{pnl_cls}'>{sign2}{t['pnl']:.2f}%</td>"
                    f"</tr>")
            st.markdown(
                f'<div style="max-height:260px;overflow-y:auto;margin-top:.3rem;">'
                f'<table class="tj-tbl">'
                f'<thead><tr><th>Alış Tarihi</th><th>Alış</th>'
                f'<th>Satış Tarihi</th><th>Satış</th><th>K/Z %</th></tr></thead>'
                f'<tbody>{rows_html}</tbody></table></div>',
                unsafe_allow_html=True)
        else:
            st.markdown('<div style="color:var(--muted);font-size:.76rem;padding:.4rem;">'
                        'Bu parametrelerle işlem gerçekleşmedi.</div>',unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: LIVE SIGNALS
# ─────────────────────────────────────────────────────────────────────────────
def page_live(user):
    sh("⚡","Komuta Merkezi")

    markets=get_markets()
    all_bist=markets.get("🏦 BIST Tüm Hisseler",_BIST_FALLBACK)
    pool=sorted(set(all_bist+STATIC_MARKETS.get("🪙 Kripto (USD)",[])+STATIC_MARKETS.get("🇺🇸 S&P 500",[])))

    # ── YENİ STRATEJİ FORMU ────────────────────────────────────────────────────
    st.markdown(
        '<div style="background:linear-gradient(135deg,rgba(var(--acc-rgb),.07),rgba(var(--acc-rgb),.02));'
        'border:1px solid rgba(var(--acc-rgb),.2);border-radius:12px;padding:.85rem 1.1rem;margin-bottom:.6rem;">'
        '<div style="font-size:.6rem;color:var(--acc);font-family:\'Space Mono\',monospace;'
        'text-transform:uppercase;letter-spacing:.14em;margin-bottom:.55rem;">➕ Yeni Strateji Kur</div>',
        unsafe_allow_html=True)

    sym_c, tf_c = st.columns([2, 1])
    with sym_c:
        st.markdown('<span style="font-size:.6rem;color:var(--muted);font-family:\'Space Mono\',monospace;text-transform:uppercase;">Sembol</span>', unsafe_allow_html=True)
        lsym = sym_selectbox("", pool, key="lsym_sel_v2")
    with tf_c:
        st.markdown('<span style="font-size:.6rem;color:var(--muted);font-family:\'Space Mono\',monospace;text-transform:uppercase;">Zaman Dilimi</span>', unsafe_allow_html=True)
        lv_interval, lv_period = tf_selectbox("lv_tf")

    st.markdown('<div style="font-size:.58rem;color:var(--gld);font-family:\'Space Mono\',monospace;text-transform:uppercase;letter-spacing:.1em;margin:.5rem 0 .25rem;">1. Şart</div>', unsafe_allow_html=True)
    lind,lparams,lcond,lthr=indicator_form("lv")

    use_lv_cond2 = st.toggle("➕ Ek Şart Ekle (AND)", value=False, key="lv_use_cond2")
    lind2=lparams2=lcond2=lthr2=None
    if use_lv_cond2:
        st.markdown('<div style="font-size:.58rem;color:var(--gld);font-family:\'Space Mono\',monospace;text-transform:uppercase;letter-spacing:.1em;margin:.4rem 0 .2rem;">2. Şart (AND)</div>', unsafe_allow_html=True)
        lind2,lparams2,lcond2,lthr2=indicator_form("lv2")

    if st.button("💾 STRATEJİYİ KAYDET", key="save_s", use_container_width=True):
        ok=db_save_strategy(user["id"],lsym,lind,lparams,lcond,lthr)
        if ok: st.success(f"✅ Kaydedildi: **{display_sym(lsym)}** — {lind} {lcond}"); st.rerun()
        else:  st.error("Kayıt başarısız.")

    st.markdown('</div>', unsafe_allow_html=True)

    # ── Bot Status Cards ────────────────────────────────────────────────────────
    sh("🤖","Bot Durum Kartları")
    strats=db_get_strategies(user["id"])
    if not strats:
        st.markdown('<div style="color:var(--muted);font-size:.78rem;padding:.5rem;">Henüz strateji yok.</div>',unsafe_allow_html=True)
    else:
        cols=st.columns(min(3,len(strats)))
        for idx,s in enumerate(strats):
            dec=_decode_params(s); act=s.get("is_active",True)
            with cols[idx % 3]:
                dot=('<span class="ldot" style="display:inline-block;width:7px;height:7px;'
                     'border-radius:50%;background:var(--grn);animation:blink 1.2s infinite;'
                     'margin-right:5px;"></span>AKTİF'
                     if act else '● DURDU')
                dot_clr='var(--grn)' if act else 'var(--muted)'
                st.markdown(
                    f'<div class="bot-card">'
                    f'<div class="bot-card-sym">{display_sym(s["symbol"])}</div>'
                    f'<div class="bot-card-ind">{dec["indicator"]} — {dec["condition"]}</div>'
                    f'<div class="bot-card-cond">'
                    f'{", ".join(f"{k}={v}" for k,v in dec["params"].items())}</div>'
                    f'<div style="font-size:.65rem;color:{dot_clr};margin-top:.4rem;'
                    f'font-family:\'Space Mono\',monospace;">{dot}</div></div>',
                    unsafe_allow_html=True)
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if act:
                        if st.button("⏹ Durdur",key=f"stp_{s['id']}",use_container_width=True):
                            db_toggle(s["id"],False); st.rerun()
                    else:
                        if st.button("▶ Başlat",key=f"str_{s['id']}",use_container_width=True):
                            db_toggle(s["id"],True); st.rerun()

    # ── Manual Check + Terminal ─────────────────────────────────────────────────
    sh("🔬","Anlık Manuel Kontrol")
    if "signal_log" not in st.session_state: st.session_state["signal_log"]=[]
    if st.button("🔄 Şimdi Kontrol Et",key="manual_chk"):
        with st.spinner("Kontrol ediliyor…"):
            df=fetch_price_data(lsym, period=lv_period, interval=lv_interval)
        if df is not None and not df.empty:
            s=compute_ind_series(df,lind,lparams).dropna()
            val=float(s.iloc[-1]) if not s.empty else 0.0
            price=float(df["Close"].iloc[-1])
            sig1=build_entry_signal(df,lind,lparams,lcond,lthr).fillna(False)
            if lind2 and lcond2 is not None:
                sig2=build_entry_signal(df,lind2,lparams2 or {},lcond2,lthr2).fillna(False)
                trig=bool((sig1&sig2).iloc[-1])
            else:
                trig=bool(sig1.iloc[-1])
            ts=datetime.now().strftime("%H:%M:%S")
            buy_date=datetime.now().strftime("%d.%m.%Y %H:%M")
            if trig:
                AUTO_AMOUNT=1000.0
                paper_msg=paper_buy(user,lsym,price,AUTO_AMOUNT)
                qty=AUTO_AMOUNT/price if price>0 else 0.0
                cur_q=fetch_quick_quote(lsym)
                cur_price=cur_q["price"] if cur_q.get("price") else price
                cur_val=qty*cur_price
                send_telegram_alert(lsym,"BUY",price,lind,val,user.get("telegram_chat_id",""))
                st.toast(f"🚨 {lind}={val:.2f} → Otomatik AL",icon="🔔")
                st.session_state["signal_log"].append(
                    f'<span class="t-ts">[{ts}]</span> '
                    f'<span class="t-trig">🚨 SİNYAL {display_sym(lsym)} | {lind}={val:.2f} | '
                    f'Fiyat:{price:.4f} | Alım:{buy_date} | Güncel:${cur_val:,.2f}</span> | {paper_msg}')
            else:
                st.session_state["signal_log"].append(
                    f'<span class="t-ts">[{ts}]</span> '
                    f'<span class="t-none">— {display_sym(lsym)} | {lind}={val:.2f} | şart gerçekleşmedi</span>')
        else:
            st.session_state["signal_log"].append(
                f'<span class="t-ts">[{datetime.now().strftime("%H:%M:%S")}]</span> '
                f'<span class="t-none">⚠ Veri alınamadı: {display_sym(lsym)}</span>')

    # Terminal output
    if st.session_state["signal_log"]:
        lines="<br>".join(st.session_state["signal_log"][::-1][:30])
        st.markdown(f'<div class="terminal">{lines}</div>',unsafe_allow_html=True)
    else:
        st.markdown('<div class="terminal"><span style="color:#1d5c3a;">— Terminal boş. '
                    'Kontrol et butonuna bas.</span></div>',unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# PAGE: SETTINGS
# ─────────────────────────────────────────────────────────────────────────────
def page_settings(user):
    sh("🎨","Tema & Ayarlar")
    if "theme" not in st.session_state: st.session_state["theme"]=DEFAULT_THEME.copy()
    st.markdown("##### 🖌️ Vurgu Rengi")
    presets=[("#00d4ff","0,212,255","🔵 Cyan"),("#00e676","0,230,118","🟢 Yeşil"),
             ("#ffd700","255,215,0","🟡 Altın"),("#ff6b6b","255,107,107","🔴 Kırmızı"),
             ("#b48eff","180,142,255","🟣 Mor"),("#ff9f43","255,159,67","🟠 Turuncu"),
             ("#ff6eb4","255,110,180","🩷 Pembe")]
    pc=st.columns(len(presets))
    for i,(h,r,n) in enumerate(presets):
        with pc[i]:
            if st.button(n,key=f"pr_{i}"):
                st.session_state["theme"]["accent"]=h; st.session_state["theme"]["accent_rgb"]=r
                _prefs_save(user); st.rerun()
    st.markdown("##### 🌑 Arka Plan")
    bg_opts={"Koyu Siyah":("#080c14","#111827","#1e2d45"),"Lacivert":("#060d1a","#0d1728","#192640"),
             "Antrasit":("#0f0f0f","#1a1a1a","#2a2a2a"),"Koyu Gri":("#111218","#1c1c26","#282840")}
    bg_ch=st.radio("Gizli",list(bg_opts.keys()),horizontal=True,label_visibility="collapsed")
    if st.button("✓ Uygula",key="apply_bg"):
        bg,card,brd=bg_opts[bg_ch]
        st.session_state["theme"].update({"bg_primary":bg,"bg_card":card,"border":brd})
        _prefs_save(user); st.rerun()
    st.markdown("##### 🔤 Yazı Boyutu")
    fs=st.slider("Gizli",12,20,int(st.session_state["theme"].get("font_size",15)),label_visibility="collapsed")
    if st.button("✓ Uygula",key="apply_fs"):
        st.session_state["theme"]["font_size"]=str(fs)
        _prefs_save(user); st.rerun()
    st.markdown("##### 📡 Telegram Chat ID")
    tg=st.text_input("Gizli",value=user.get("telegram_chat_id",""),
                     placeholder="@kullaniciadiniz veya 123456789",label_visibility="collapsed")
    if st.button("💾 Kaydet",key="save_tg"):
        user["telegram_chat_id"]=tg; st.session_state["user"]=user
        if SUPABASE:
            try: SUPABASE.table("users").update({"telegram_chat_id":tg}).eq("id",user["id"]).execute()
            except: pass
        st.success("Kaydedildi.")
    if st.button("↺ Temayı Sıfırla",key="rst"):
        st.session_state["theme"]=DEFAULT_THEME.copy()
        _prefs_save(user); st.rerun()


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────
def main():
    if "theme" not in st.session_state:
        st.session_state["theme"]=DEFAULT_THEME.copy()
    inject_css()
    if "user" not in st.session_state:
        page_auth(); return
    user=st.session_state["user"]
    page=sidebar(user)
    if   "Dashboard" in page: page_dashboard(user)
    elif "Backtest"  in page: page_backtest()
    elif "Canlı"     in page: page_live(user)
    elif "Tema"      in page: page_settings(user)
    
if __name__=="__main__":
    main()
