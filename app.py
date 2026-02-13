import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# --- CONFIG ---
st.set_page_config(page_title="IDX Real-time Radar", layout="wide", page_icon="🏹")

# Auto-refresh setiap 30 detik (Batas aman agar tidak kena blokir Yahoo)
st_autorefresh(interval=30000, key="realtime_refresh")

# --- DATABASE SAHAM (Daftar saham aktif/ramai) ---
# Anda bisa menambah daftar ini hingga 50-100 saham
WATCHLIST = [
    'ADRO.JK', 'BRMS.JK', 'GOTO.JK', 'BBRI.JK', 'TLKM.JK', 'ASII.JK', 
    'ANTM.JK', 'PTBA.JK', 'MEDC.JK', 'HRUM.JK', 'BBNI.JK', 'BMRI.JK', 
    'AMMN.JK', 'BUMI.JK', 'TPIA.JK', 'BBCA.JK', 'UNTR.JK', 'KLBF.JK'
]

# --- FUNGSI DETEKSI ---
def get_ara_limit(price):
    if 50 <= price <= 200: return 34.0
    if 200 < price <= 5000: return 24.0
    return 19.0

# --- UI HEADER ---
st.title("🏹 IDX Real-time Radar (Yahoo Mode)")
st.caption(f"Status: Aktif | Update Terakhir: {datetime.now().strftime('%H:%M:%S')} WIB")

# Dashboard sederhana
col1, col2 = st.columns(2)
col1.metric("Update Interval", "30 Detik")
col2.metric("Sumber Data", "Yahoo Finance (Free)")

st.divider()

# --- PROSES DATA ---
signals = []

with st.spinner('Menarik data harga terbaru...'):
    # Menarik data seluruh watchlist sekaligus (lebih cepat)
    data = yf.download(WATCHLIST, period="5d", interval="1m", group_by='ticker', progress=False)

    for ticker in WATCHLIST:
        try:
            # Ambil data harga menit terakhir
            df_stock = data[ticker]
            if df_stock.empty: continue
            
            last_price = float(df_stock['Close'].iloc[-1])
            prev_close = float(df_stock['Close'].iloc[-2]) # Harga menit sebelumnya
            
            # Hitung kenaikan harian (estimasi dari close hari sebelumnya)
            # Untuk akurasi 100%, idealnya bandingkan dengan close kemarin
            daily_change = ((last_price - prev_close) / prev_close) * 100
            volume = int(df_stock['Volume'].iloc[-1])
            
            # Ambil metrik 20 hari untuk Breakout
            # (Gunakan cache agar tidak lambat)
            @st.cache_data(ttl=3600)
            def get_hist(t):
                h = yf.download(t, period="25d", progress=False)
                return h['High'].iloc[-21:-1].max(), h['Volume'].iloc[-21:-1].mean()
            
            high_20d, avg_vol = get_hist(ticker)
            
            # LOGIKA SINYAL
            status = "🔎 Monitoring"
            if daily_change >= get_ara_limit(last_price): 
                status = "🔥 NEAR ARA"
            elif last_price > high_20d and volume > (avg_vol * 0.5): # Volume disesuaikan per menit
                status = "🚀 BREAKOUT"
            
            signals.append({
                "Ticker": ticker.replace('.JK', ''),
                "Harga": f"Rp {last_price:,.0f}",
                "Change": f"{daily_change:.2f}%",
                "Volume": f"{volume:,}",
                "Sinyal": status
            })
        except:
            continue

# --- TAMPILKAN TABEL ---
if signals:
    res_df = pd.DataFrame(signals)
    
    # Fungsi warna
    def color_status(val):
        if "ARA" in val: color = '#ff4b4b'
        elif "BREAKOUT" in val: color = '#29b09d'
        else: color = 'white'
        return f'background-color: {color}; color: black; font-weight: bold' if "Monitoring" not in val else ''

    st.dataframe(res_df.style.applymap(color_status, subset=['Sinyal']), use_container_width=True)
else:
    st.warning("Gagal memuat data. Pastikan koneksi internet stabil.")
