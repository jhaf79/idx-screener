import requests
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
import streamlit as st
import numpy as np
import time

# ==========================================
# KONFIGURASI TELEGRAM
# ==========================================
# Pastikan st.secrets sudah diset di Streamlit Cloud atau .streamlit/secrets.toml
try:
    BOT_TOKEN = st.secrets["BOT_TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
except:
    st.error("Gagal memuat API Token Telegram. Pastikan st.secrets sudah dikonfigurasi.")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        st.error(f"Gagal kirim Telegram: {e}")

def send_chart(image_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, "rb") as img:
            requests.post(url, data={"chat_id": CHAT_ID}, files={"photo": img})
    except:
        pass

# ==========================================
# DAFTAR SYMBOLS (Sesuai List Anda)
# ==========================================
# (Hanya contoh pendek, silakan paste kembali 800+ list Anda di sini)
symbols = [
    "AADI.JK", "AALI.JK", "ABMM.JK", "ACES.JK", "ADRO.JK", "AMMN.JK", "ANTM.JK", 
    "ASII.JK", "BBCA.JK", "BBNI.JK", "BBRI.JK", "BBTN.JK", "BMRI.JK", "BRIS.JK", 
    "BRMS.JK", "BUMI.JK", "CPIN.JK", "GOTO.JK", "INCO.JK", "ITMG.JK", "KLBF.JK", 
    "MEDC.JK", "MDKA.JK", "PTBA.JK", "TLKM.JK", "UNTR.JK", "UNVR.JK"
    # ... Masukkan semua simbol Anda di sini
]

# ==========================================
# FUNGSI TEKNIS & PERHITUNGAN
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

def generate_chart(symbol, df):
    plt.figure(figsize=(8,4))
    plt.plot(df['Close'], label="Close Price", color='blue')
    plt.plot(df['Close'].rolling(20).mean(), label="MA20", color='orange')
    plt.title(f"Chart: {symbol}")
    plt.grid(True, alpha=0.3)
    plt.legend()
    file_name = f"{symbol}.png"
    plt.savefig(file_name)
    plt.close()
    return file_name

# ==========================================
# CORE SCANNER ENGINE
# ==========================================

def run_scanner():
    results = []
    st.write(f"🔍 Memindai {len(symbols)} saham... (Gunakan tombol 'Stop' di browser untuk berhenti)")
    
    # Download data masal (Vectorized)
    # Gunakan period 60 hari saja agar lebih cepat
    all_data = yf.download(
        tickers=symbols,
        period="3mo",
        interval="1d",
        group_by="column",
        threads=True,
        progress=False
    )

    for symbol in symbols:
        try:
            # Ambil data per saham dari hasil download masal
            df = pd.DataFrame({
                'Open': all_data['Open'][symbol],
                'High': all_data['High'][symbol],
                'Low': all_data['Low'][symbol],
                'Close': all_data['Close'][symbol],
                'Volume': all_data['Volume'][symbol]
            }).dropna()

            if len(df) < 20: continue

            last = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            
            # 1. Filter Likuiditas (Min Transaksi 1 Miliar Rupiah)
            turnover = last * df['Volume'].iloc[-1]
            if turnover < 1_000_000_000: continue 

            # 2. Perhitungan Statistik
            change = ((last - prev) / prev) * 100
            vol_spike = df['Volume'].iloc[-1] / df['Volume'].iloc[-6:-1].mean()
            rsi = calculate_rsi(df['Close']).iloc[-1]
            
            ema20 = df['Close'].ewm(span=20).mean().iloc[-1]
            ema50 = df['Close'].ewm(span=50).mean().iloc[-1]

            atr = calculate_atr(df).iloc[-1]
            atr_prev = calculate_atr(df).iloc[-5:-1].mean()

            # 3. Logika Institutional (Breakout & Power)
            is_breakout = last > df['High'].iloc[-10:-1].max()
            is_uptrend = ema20 > ema50 and last > ema20
            is_vol_expand = atr > (atr_prev * 1.1)
            
            limit_ara = get_ara_limit(prev)
            
            # Kriteria: Mendekati ARA / ARA + Volume meledak + Breakout + Uptrend
            if (change >= (limit_ara - 4)) and vol_spike >= 2.5 and is_breakout and is_uptrend:
                
                # Scoring (Semakin tinggi semakin kuat)
                prob_score = (change * 0.4) + (vol_spike * 0.4) + (100 if is_vol_expand else 0)

                results.append({
                    "symbol": symbol.replace(".JK",""),
                    "price": last,
                    "change": change,
                    "vol": vol_spike,
                    "turnover": f"{turnover/1e9:.1f}B",
                    "prob": prob_score,
                    "df_full": df # Simpan untuk chart
                })
        except:
            continue

    # Urutkan berdasarkan skor tertinggi
    return sorted(results, key=lambda x: x["prob"], reverse=True)[:5]

def alert(results):
    waktu = datetime.now().strftime('%H:%M:%S')
    msg = f"🏆 <b>INSTITUTIONAL ALERT</b>\n⏰ {waktu}\n\n"

    for r in results:
        msg += f"<b>{r['symbol']}</b> (Score: {r['prob']:.0f})\n"
        msg += f"Harga: Rp {int(r['price']):,}\n"
        msg += f"Naik: {r['change']:+.2f}% | Vol: {r['vol']:.1f}x\n"
        msg += f"Value: {r['turnover']}\n\n"

    send_telegram(msg)

    # Kirim chart tiap saham
    for r in results:
        img_path = generate_chart(r["symbol"], r["df_full"])
        send_chart(img_path)

# ==========================================
# STREAMLIT UI
# ==========================================

st.set_page_config(page_title="Institutional Scanner", layout="wide")
st.title("🚀 IDX Institutional Scanner v2.0")

# Sidebar settings
interval = st.sidebar.selectbox("Auto Scan Interval (Menit)", [0, 5, 10, 15], index=0)
min_spike = st.sidebar.slider("Min Volume Spike (x)", 1.0, 10.0, 3.0)

if st.button("Manual Scan Now"):
    res = run_scanner()
    if res:
        st.success(f"Ditemukan {len(res)} saham potensial!")
        # Tampilkan tabel tanpa kolom dataframe full
        display_df = pd.DataFrame(res).drop(columns=['df_full'])
        st.dataframe(display_df, use_container_width=True)
        alert(res)
    else:
        st.info("Tidak ada saham yang memenuhi kriteria saat ini.")

# Auto Mode Logic
if interval > 0:
    st.info(f"Mode Auto Aktif: Scanning setiap {interval} menit. Jangan tutup tab ini.")
    res = run_scanner()
    if res:
        alert(res)
        st.write(f"Alert terkirim pada {datetime.now().strftime('%H:%M:%S')}")
    
    time.sleep(interval * 60)
    st.rerun()
