import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import time

# --- 1. SETTING HALAMAN ---
st.set_page_config(page_title="IDX Pro Radar", layout="wide", page_icon="🏹")

# Auto-refresh setiap 60 detik (Lebih aman untuk Yahoo)
st_autorefresh(interval=60000, key="idx_final_refresh")

# --- 2. DAFTAR SAHAM (Watchlist Utama) ---
WATCHLIST = [
    'BUMI.JK', 'BRMS.JK', 'INDS.JK', 'MBMA.JK', 'BELL.JK', 'KPIG.JK', 
    'ANTM.JK', 'BIPI.JK', 'UNSP.JK', 'ZATA.JK', 'TRIN.JK', 'OPMS.JK', 
    'AMMN.JK', 'ELTY.JK', 'TPIA.JK', 'BBCA.JK', 'UNTR.JK', 'KLBF.JK'
]

# --- 3. FUNGSI LOGIKA ---
def get_ara_limit(price):
    if 50 <= price <= 200: return 34.0
    if 200 < price <= 5000: return 24.0
    return 19.0

# --- 4. HEADER UI ---
st.title("🏹 IDX Real-time Radar")
st.write(f"🕒 Terakhir Update: {datetime.now().strftime('%H:%M:%S')} WIB")

# --- 5. PENGAMBILAN DATA MASSAL ---
@st.cache_data(ttl=55) # Cache sedikit di bawah interval refresh
def fetch_data(tickers):
    try:
        # Mengunduh data 5 hari terakhir untuk perbandingan harga
        data = yf.download(tickers, period="5d", interval="1d", group_by='ticker', progress=False)
        return data
    except Exception as e:
        return None

# --- 6. PROSES & TAMPILAN ---
raw_data = fetch_data(WATCHLIST)

if raw_data is not None and not raw_data.empty:
    signals = []
    
    for ticker in WATCHLIST:
        try:
            # Ambil data spesifik saham
            df_s = raw_data[ticker]
            if len(df_s) < 2: continue

            last_price = float(df_s['Close'].iloc[-1])
            prev_close = float(df_s['Close'].iloc[-2])
            change = ((last_price - prev_close) / prev_close) * 100
            vol = int(df_s['Volume'].iloc[-1])
            
            # Deteksi Sinyal
            status = "🔎 Monitoring"
            ara_trigger = get_ara_limit(last_price)
            
            if change >= ara_trigger: status = "🔥 NEAR ARA"
            elif change >= 15: status = "📈 STRONG UP"
            elif change <= -10: status = "⚠️ WARNING"

            signals.append({
                "Ticker": ticker.replace('.JK', ''),
                "Harga": int(last_price),
                "Chg%": round(change, 2),
                "Volume": f"{vol:,}",
                "Sinyal": status
            })
        except:
            continue

    # Tampilkan Tabel
    if signals:
        res_df = pd.DataFrame(signals)
        
        # Pewarnaan Sinyal
        def color_map(val):
            bg = 'transparent'
            if val == "🔥 NEAR ARA": bg = '#8b0000'
            elif val == "📈 STRONG UP": bg = '#006400'
            elif val == "⚠️ WARNING": bg = '#4a4a00'
            return f'background-color: {bg}; color: white; font-weight: bold'

        st.dataframe(
            res_df.style.applymap(color_map, subset=['Sinyal']),
            use_container_width=True,
            hide_index=True
        )
    else:
        st.warning("Data berhasil diunduh tapi tidak ada sinyal yang cocok.")
else:
    st.error("Server Yahoo sedang sibuk atau koneksi terputus.")
    st.info("🔄 Mencoba menghubungkan kembali dalam 60 detik...")

