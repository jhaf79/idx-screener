import requests
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
import streamlit as st
import numpy as np
import time

# ==========================================
# TELEGRAM CONFIG
# ==========================================
BOT_TOKEN = st.secrets["BOT_TOKEN"]
CHAT_ID = st.secrets["CHAT_ID"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=payload)

def send_chart(image_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    with open(image_path, "rb") as img:
        requests.post(url, data={"chat_id": CHAT_ID}, files={"photo": img})

# ==========================================
# SYMBOLS (PAKAI LIST ANDA FULL)
# ==========================================
symbols = ["BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","ASII.JK","ADRO.JK","GOTO.JK","AMMN.JK"]

# ==========================================
# FUNCTIONS
# ==========================================

def get_ara_limit(price):
    if price <= 200: return 34.0
    elif price <= 5000: return 24.0
    else: return 19.0

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    true_range = ranges.max(axis=1)
    return true_range.rolling(period).mean()

def market_cap_class(symbol):
    try:
        info = yf.Ticker(symbol).info
        cap = info.get("marketCap", 0)
        if cap > 100_000_000_000_000:
            return "BIG CAP"
        elif cap > 10_000_000_000_000:
            return "MID CAP"
        else:
            return "SMALL CAP"
    except:
        return "UNKNOWN"

def generate_chart(symbol, df):
    plt.figure(figsize=(8,4))
    plt.plot(df['Close'], label="Close")
    plt.plot(df['Close'].rolling(20).mean(), label="MA20")
    plt.title(symbol.replace(".JK",""))
    plt.legend()
    file_name = f"{symbol}.png"
    plt.savefig(file_name)
    plt.close()
    return file_name

# ==========================================
# STREAMLIT UI
# ==========================================

st.title("🏆 INSTITUTIONAL SCANNER v2.0")

interval = st.selectbox("Auto Scan Interval (menit)", [0, 5, 10, 15])

if "alert_cache" not in st.session_state:
    st.session_state.alert_cache = {}

def run_scanner():

    results = []

    all_data = yf.download(
        tickers=symbols,
        period="6mo",
        interval="1d",
        group_by="ticker",
        threads=True,
        progress=False
    )

    for symbol in symbols:

        try:
            df = all_data.get(symbol)
            if df is None or len(df) < 60:
                continue

            df = df.dropna()

            last = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]

            change = ((last - prev) / prev) * 100

            vol = df['Volume'].iloc[-1]
            avg_vol = df['Volume'].iloc[-6:-1].mean()
            vol_spike = vol / avg_vol if avg_vol > 0 else 0

            rsi = calculate_rsi(df['Close']).iloc[-1]

            ema20 = df['Close'].ewm(span=20).mean().iloc[-1]
            ema50 = df['Close'].ewm(span=50).mean().iloc[-1]

            atr = calculate_atr(df).iloc[-1]
            atr_prev = calculate_atr(df).iloc[-5:-1].mean()

            breakout = last > df['High'].iloc[-6:-1].max()
            trend_ok = ema20 > ema50 and last > ema20
            volatility_expand = atr > atr_prev

            limit_ara = get_ara_limit(prev)
            pre_ara = change >= (limit_ara - 5) and vol_spike >= 4

            if (pre_ara or change >= limit_ara) and breakout and trend_ok and volatility_expand:

                prob_score = (
                    change * 0.4 +
                    vol_spike * 0.3 +
                    rsi * 0.1 +
                    (atr / last) * 100
                )

                cap_type = market_cap_class(symbol)

                results.append({
                    "symbol": symbol.replace(".JK",""),
                    "price": last,
                    "change": change,
                    "vol": vol_spike,
                    "rsi": rsi,
                    "prob": prob_score,
                    "cap": cap_type
                })

        except:
            continue

    return sorted(results, key=lambda x: x["prob"], reverse=True)[:5]

def alert(results):

    waktu = datetime.now().strftime('%H:%M:%S')

    msg = f"🏆 <b>INSTITUTIONAL ALERT v2.0</b>\n⏰ {waktu}\n\n"

    for r in results:
        msg += f"<b>{r['symbol']}</b> ({r['cap']})\n"
        msg += f"Rp {int(r['price']):,}\n"
        msg += f"{r['change']:+.2f}% | Vol {r['vol']:.1f}x\n"
        msg += f"RSI {r['rsi']:.1f} | Score {r['prob']:.1f}\n\n"

    send_telegram(msg)

    # kirim chart
    for r in results:
        df = yf.download(r["symbol"]+".JK", period="3mo")
        img = generate_chart(r["symbol"]+".JK", df)
        send_chart(img)

# ==========================================
# MAIN LOOP
# ==========================================

if st.button("🚀 Run Scanner Now"):
    res = run_scanner()
    if res:
        alert(res)
        st.dataframe(pd.DataFrame(res))
    else:
        st.info("Tidak ada kandidat hari ini.")

# AUTO MODE
if interval > 0:
    while True:
        res = run_scanner()
        if res:
            alert(res)
        time.sleep(interval * 60)
