"""
QuantEdge Background Worker — v3.0
Batch yfinance download to avoid per-symbol IP rate limits.
"""

import os
import time
import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("quantedge-worker")

POLL_INTERVAL_SECONDS  = 300
ALERT_COOLDOWN_MINUTES = 30
SUPABASE_URL           = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY           = os.getenv("SUPABASE_KEY", "")
TELEGRAM_BOT_TOKEN     = os.getenv("TELEGRAM_BOT_TOKEN", "")


def get_supabase():
    if not SUPABASE_URL or not SUPABASE_KEY:
        log.warning("SUPABASE_URL / SUPABASE_KEY not set.")
        return None
    from supabase import create_client
    return create_client(SUPABASE_URL, SUPABASE_KEY)


# ── Telegram ─────────────────────────────────────────────────────────────────
def send_telegram_alert(symbol, signal, price, indicator, value, chat_id):
    if not TELEGRAM_BOT_TOKEN or not chat_id:
        log.info(f"[TELEGRAM SKIP] {symbol}")
        return
    label   = symbol.replace(".IS","").replace(".DE","").replace(".L","")
    message = (
        f"🚨 *QuantEdge Signal*\n\n"
        f"📌 `{label}`\n"
        f"🔔 Signal: *{signal}*\n"
        f"💰 Price: `{price:.4f}`\n"
        f"📊 {indicator}: `{value:.2f}`\n"
        f"🕐 `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`"
    )
    try:
        import requests
        resp = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"},
            timeout=8,
        )
        if resp.status_code == 200:
            log.info(f"[TELEGRAM OK] → {chat_id}: {label} {signal}")
        else:
            log.warning(f"[TELEGRAM ERR] {resp.status_code}: {resp.text}")
    except Exception as e:
        log.error(f"[TELEGRAM EXCEPTION] {e}")


# ── Indicators ────────────────────────────────────────────────────────────────
def calc_rsi(series, period=14):
    delta = series.diff()
    ag    = delta.clip(lower=0).ewm(com=period-1, min_periods=period).mean()
    al    = (-delta.clip(upper=0)).ewm(com=period-1, min_periods=period).mean()
    return 100 - (100 / (1 + ag / al))

def calc_sma(series, period): return series.rolling(window=period).mean()
def calc_ema(series, period): return series.ewm(span=period, adjust=False).mean()

def calc_macd(series, fast=12, slow=26):
    return series.ewm(span=fast, adjust=False).mean() - series.ewm(span=slow, adjust=False).mean()

def get_indicator_value_from_df(close: pd.Series, indicator: str, period: int):
    """Compute indicator on a pre-fetched Close series, return latest value."""
    if   indicator == "RSI":   s = calc_rsi(close, period)
    elif indicator == "SMA":   s = calc_sma(close, period)
    elif indicator == "EMA":   s = calc_ema(close, period)
    elif indicator == "MACD":  s = calc_macd(close)
    else:                      s = close
    if s.empty or s.isna().all():
        return None
    return float(s.dropna().iloc[-1])


def check_condition(value, condition, threshold):
    if condition == "<":  return value <  threshold
    if condition == ">":  return value >  threshold
    if condition == "<=": return value <= threshold
    if condition == ">=": return value >= threshold
    return False


# ── Batch price download ──────────────────────────────────────────────────────
def batch_download(symbols: list[str]) -> dict[str, pd.Series]:
    """
    Download 1-month 5-min bars for all symbols in ONE yfinance call.
    Returns dict: symbol → Close Series (or empty Series on failure).

    Using a single yf.download() call instead of per-symbol Ticker.history()
    dramatically reduces the number of outgoing HTTP requests and avoids
    Yahoo Finance rate-limiting / IP bans.
    """
    if not symbols:
        return {}

    ticker_str = " ".join(symbols)
    log.info(f"[BATCH DOWNLOAD] {len(symbols)} symbols: {ticker_str[:120]}{'...' if len(ticker_str)>120 else ''}")

    try:
        # auto_adjust=True so 'Close' is already split-adjusted
        raw = yf.download(
            ticker_str,
            period="1mo",
            interval="5m",
            auto_adjust=True,
            progress=False,
            threads=True,       # parallelise internal HTTP fetches
        )
    except Exception as e:
        log.error(f"[BATCH DOWNLOAD ERROR] {e}")
        return {}

    if raw.empty:
        return {}

    result: dict[str, pd.Series] = {}

    if len(symbols) == 1:
        # Single-ticker download: flat columns (Open, High, Low, Close, Volume)
        sym = symbols[0]
        if "Close" in raw.columns:
            result[sym] = raw["Close"].dropna()
        return result

    # Multi-ticker download: MultiIndex columns (metric, symbol)
    try:
        close_df = raw["Close"]          # DataFrame: index=datetime, columns=symbols
    except KeyError:
        log.warning("[BATCH] No 'Close' column in multi-ticker download.")
        return {}

    for sym in symbols:
        if sym in close_df.columns:
            series = close_df[sym].dropna()
            if not series.empty:
                result[sym] = series
            else:
                log.warning(f"[BATCH] {sym}: empty Close series")
        else:
            log.warning(f"[BATCH] {sym}: not found in download result")

    return result


# ── Main loop ─────────────────────────────────────────────────────────────────
def run_worker():
    log.info("════════════════════════════════════")
    log.info("  QuantEdge Worker  v3.0  starting")
    log.info(f"  Poll interval : {POLL_INTERVAL_SECONDS}s")
    log.info(f"  Alert cooldown: {ALERT_COOLDOWN_MINUTES}m")
    log.info("════════════════════════════════════")

    supabase = get_supabase()
    last_alerted: dict = {}   # strategy_id → datetime of last alert

    while True:
        cycle_start = datetime.now()
        log.info(f"─── Scan cycle @ {cycle_start.strftime('%H:%M:%S')} ───")

        if supabase is None:
            log.warning("No Supabase — sleeping.")
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        # 1. Fetch active strategies
        try:
            res        = supabase.table("strategies").select(
                "id,user_id,symbol,indicator,condition,threshold,period"
            ).eq("is_active", True).execute()
            strategies = res.data or []
        except Exception as e:
            log.error(f"[DB] {e}")
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        log.info(f"Active strategies: {len(strategies)}")
        if not strategies:
            time.sleep(POLL_INTERVAL_SECONDS)
            continue

        # 2. Build user → chat_id map
        user_ids    = list({s["user_id"] for s in strategies})
        chat_id_map = {}
        try:
            u_res = supabase.table("users").select("id,telegram_chat_id").in_("id", user_ids).execute()
            for u in (u_res.data or []):
                chat_id_map[u["id"]] = u.get("telegram_chat_id","")
        except Exception as e:
            log.warning(f"[DB] chat_id fetch failed: {e}")

        # 3. Collect unique symbols and batch-download
        unique_symbols = list({s["symbol"] for s in strategies})
        close_map      = batch_download(unique_symbols)  # symbol → Close series

        # 4. Evaluate each strategy against downloaded data
        for s in strategies:
            sid       = s["id"]
            symbol    = s["symbol"]
            indicator = s["indicator"]
            condition = s["condition"]
            threshold = float(s["threshold"])
            period    = int(s.get("period", 14))
            user_id   = s["user_id"]
            chat_id   = chat_id_map.get(user_id, "")

            # Cooldown check
            if sid in last_alerted:
                if datetime.now() - last_alerted[sid] < timedelta(minutes=ALERT_COOLDOWN_MINUTES):
                    log.debug(f"  [{symbol}] cooldown active")
                    continue

            close = close_map.get(symbol)
            if close is None or close.empty:
                log.warning(f"  [{symbol}] no data")
                continue

            price   = float(close.iloc[-1])
            ind_val = get_indicator_value_from_df(close, indicator, period)
            if ind_val is None:
                continue

            triggered = check_condition(ind_val, condition, threshold)
            log.info(f"  [{symbol}] {indicator}({period})={ind_val:.2f} {condition} {threshold} → {'🔔 TRIGGERED' if triggered else '○'}")

            if triggered:
                last_alerted[sid] = datetime.now()
                send_telegram_alert(symbol, "BUY", price, indicator, ind_val, chat_id)
                # Optional: log to DB
                # supabase.table("signal_log").insert({
                #     "strategy_id": sid, "user_id": user_id, "symbol": symbol,
                #     "indicator": indicator, "ind_value": ind_val, "price": price,
                #     "triggered_at": datetime.utcnow().isoformat(),
                # }).execute()

        elapsed = (datetime.now() - cycle_start).total_seconds()
        sleep_s = max(0, POLL_INTERVAL_SECONDS - elapsed)
        log.info(f"Cycle done in {elapsed:.1f}s — sleeping {sleep_s:.0f}s")
        time.sleep(sleep_s)


if __name__ == "__main__":
    try:
        run_worker()
    except KeyboardInterrupt:
        log.info("Worker stopped (Ctrl-C).")
