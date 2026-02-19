import requests
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
import streamlit as st
import numpy as np
import time

# ==========================================
# CONFIG & TELEGRAM
# ==========================================
try:
    BOT_TOKEN = st.secrets["BOT_TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
except:
    st.error("Gagal memuat Secrets. Pastikan BOT_TOKEN & CHAT_ID sudah diisi.")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try: requests.post(url, data=payload)
    except: pass

def send_chart(image_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, "rb") as img:
            requests.post(url, data={"chat_id": CHAT_ID}, files={"photo": img})
    except: pass

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

def generate_chart(symbol, df):
    plt.figure(figsize=(8,4))
    plt.plot(df['Close'], label="Price", color='green')
    plt.plot(df['Close'].rolling(20).mean(), label="MA20", color='red')
    plt.title(f"Momentum: {symbol}")
    plt.legend()
    file_name = f"{symbol}_agg.png"
    plt.savefig(file_name)
    plt.close()
    return file_name

# ==========================================
# AGGRESSIVE SCANNER ENGINE
# ==========================================

def run_aggressive_scanner(symbols_list):
    results = []
    st.write(f"⚡ Memindai {len(symbols_list)} saham (Mode Agresif)...")
    
    # Download masal
    all_data = yf.download(
        tickers=symbols_list,
        period="3mo",
        interval="1d",
        group_by="column",
        threads=True,
        progress=False
    )

    for symbol in symbols_list:
        try:
            df = pd.DataFrame({
                'High': all_data['High'][symbol],
                'Low': all_data['Low'][symbol],
                'Close': all_data['Close'][symbol],
                'Volume': all_data['Volume'][symbol]
            }).dropna()

            if len(df) < 15: continue

            last = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            
            # --- FILTER AGGRESIF ---
            # 1. Likuiditas: Min 500 Juta
            turnover = last * df['Volume'].iloc[-1]
            if turnover < 500_000_000: continue 

            # 2. Volume Spike: Min 2.0x (Lebih longgar)
            vol_spike = df['Volume'].iloc[-1] / df['Volume'].iloc[-6:-1].mean()
            if vol_spike < 2.0: continue

            # 3. Price Change & ARA Limit
            change = ((last - prev) / prev) * 100
            limit_ara = get_ara_limit(prev)
            
            # 4. Breakout 5 Hari (Short-term momentum)
            is_breakout = last >= df['High'].iloc[-6:-1].max()
            
            # Syarat: Kenaikan > 4% DAN (Breakout ATAU Mendekati ARA)
            if change >= 4.0 and (is_breakout or change >= (limit_ara - 5)):
                
                rsi = calculate_rsi(df['Close']).iloc[-1]
                
                results.append({
                    "symbol": symbol.replace(".JK",""),
                    "price": last,
                    "change": change,
                    "vol": vol_spike,
                    "turnover": f"{turnover/1e6:.0f}M",
                    "rsi": rsi,
                    "df_full": df
                })
        except:
            continue

    return sorted(results, key=lambda x: x["change"], reverse=True)[:10]

# ==========================================
# STREAMLIT UI
# ==========================================

st.set_page_config(page_title="Aggressive Scanner", layout="wide")
st.title("⚡ IDX Aggressive Momentum Scanner")

# Masukkan daftar simbol Anda di sini
my_symbols = ["AADI.JK", "AALI.JK", "ABMM.JK", "ADRO.JK", "ANTM.JK", "ASII.JK", "BBCA.JK", "BBRI.JK", "BRMS.JK", "BUMI.JK", "GOTO.JK", "MEDC.JK", "TLKM.JK"] 

if st.button("🚀 Start Aggressive Scan"):
    res = run_aggressive_scanner(my_symbols)
    
    if res:
        st.success(f"Ditemukan {len(res)} saham momentum!")
        df_display = pd.DataFrame(res).drop(columns=['df_full'])
        st.table(df_display)
        
        # Kirim Alert
        waktu = datetime.now().strftime('%H:%M:%S')
        msg = f"⚡ <b>AGGRESSIVE MOMENTUM</b>\n⏰ {waktu}\n\n"
        for r in res:
            msg += f"<b>{r['symbol']}</b> | {r['change']:+.2f}%\n"
            msg += f"Vol: {r['vol']:.1f}x | Val: {r['turnover']}\n\n"
        
        send_telegram(msg)
        for r in res:
            img = generate_chart(r["symbol"], r["df_full"])
            send_chart(img)
    else:
        st.info("Market sedang sepi. Tidak ada saham momentum agresif.")
