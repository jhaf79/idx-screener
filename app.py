import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="IDX Super Radar", layout="wide", page_icon="🏹")

# Auto-refresh setiap 30 detik
st_autorefresh(interval=30000, key="idx_refresh_stable")

# --- 2. DATABASE SAHAM ---
# Gunakan daftar yang lebih ringkas dulu untuk memastikan koneksi stabil
WATCHLIST = [
    'ADRO.JK', 'BRMS.JK', 'GOTO.JK', 'BBRI.JK', 'TLKM.JK', 'ASII.JK', 
    'ANTM.JK', 'PTBA.JK', 'MEDC.JK', 'HRUM.JK', 'BBNI.JK', 'BMRI.JK', 
    'AMMN.JK', 'BUMI.JK', 'TPIA.JK', 'BBCA.JK', 'UNTR.JK', 'KLBF.JK'
]

# --- 3. FUNGSI LOGIKA ---
def get_ara_limit(price):
    if 50 <= price <= 200: return 34.0
    if 200 < price <= 5000: return 24.0
    return 19.0

# --- 4. TAMPILAN UI ---
st.title("🏹 IDX Real-time Radar (Stable Mode)")
st.write(f"Terakhir Update: {datetime.now().strftime('%H:%M:%S')} WIB")

col1, col2, col3 = st.columns(3)
col1.metric("Status", "Running")
col2.metric("Interval", "30s")
col3.metric("Source", "Yahoo Finance")

st.divider()

# --- 5. PROSES PENGAMBILAN DATA ---
signals = []

with st.spinner('Menghubungkan ke server Yahoo...'):
    for ticker in WATCHLIST:
        try:
            # Mengambil data harian (1d) untuk mendapatkan harga Close kemarin & hari ini
            stock = yf.Ticker(ticker)
            df = stock.history(period="2d") # Ambil 2 hari terakhir
            
            if len(df) < 2:
                continue

            last_price = df['Close'].iloc[-1]
            prev_close = df['Close'].iloc[-2]
            daily_change = ((last_price - prev_close) / prev_close) * 100
            volume = df['Volume'].iloc[-1]
            
            # Ambil Metrik Historis (High 20 Hari)
            # Menggunakan cache agar tidak membebani server
            @st.cache_data(ttl=3600)
            def get_high_20d(t):
                h = yf.download(t, period="30d", progress=False)
                return h['High'].iloc[-21:-1].max()
            
            h20 = get_high_20d(ticker)
            
            # Penentuan Sinyal
            status = "🔎 Monitoring"
            if daily_change >= get_ara_limit(last_price):
                status = "🔥 NEAR ARA"
            elif last_price > h20:
                status = "🚀 BREAKOUT"
            
            signals.append({
                "Ticker": ticker.replace('.JK', ''),
                "Harga": int(last_price),
                "Change (%)": round(daily_change, 2),
                "Volume": int(volume),
                "Sinyal": status
            })
        except Exception as e:
            # Jika satu saham gagal, lewati dan lanjut ke saham berikutnya
            continue

# --- 6. TAMPILKAN HASIL ---
if signals:
    res_df = pd.DataFrame(signals)
    
    # Styling Tabel
    def make_pretty(val):
        color = 'white'
        if val == "🔥 NEAR ARA": color = '#ff4b4b'
        elif val == "🚀 BREAKOUT": color = '#29b09d'
        return f'background-color: {color}; color: black; font-weight: bold'

    st.dataframe(
        res_df.style.applymap(make_pretty, subset=['Sinyal']),
        use_container_width=True,
        hide_index=True
    )
else:
    st.error("Gagal mengambil data dari Yahoo Finance.")
    st.info("Tips: Coba refresh halaman manual atau tunggu 1 menit. Yahoo terkadang membatasi akses jika terlalu sering.")
