import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# --- 1. SETTING HALAMAN ---
st.set_page_config(page_title="IDX Global Scanner", layout="wide")

# API KEY & TOKEN (Pastikan API_KEY GoAPI Anda aktif)
API_KEY = "437d40e0-6135-5e0b-ff16-ff17b2ae" # Ganti dengan API Key GoAPI Anda
PUSH_TOKEN = "o.xCp2U6AnZALtYIpfF5lTMNSccKgcUoi3"

st_autorefresh(interval=60000, key="idx_full_market")

# --- 2. FUNGSI ---
def send_push(title, body):
    try:
        requests.post('https://api.pushbullet.com/v2/pushes', 
                      headers={'Access-Token': PUSH_TOKEN}, 
                      json={"type": "note", "title": title, "body": body})
    except: pass

def get_limit(price):
    if 50 <= price <= 200: return 34.0
    if 200 < price <= 5000: return 24.0
    return 19.0

st.title("🏹 IDX Full Market Scanner")
st.caption(f"🌍 Memantau Seluruh Saham IDX | Update: {datetime.now().strftime('%H:%M:%S')} WIB")

# --- 3. PROSES DATA SELURUH MARKET ---
@st.cache_data(ttl=50)
def fetch_all_idx():
    try:
        # Menarik seluruh harga saham IDX dalam 1 kali request
        url = f"https://api.goapi.io/v1/stock/idx/prices?api_key={API_KEY}"
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()['data']['results']
        return None
    except: return None

data_raw = fetch_all_idx()

if data_raw:
    df = pd.DataFrame(data_raw)
    
    # Konversi tipe data ke angka
    df['last'] = pd.to_numeric(df['last'], errors='coerce')
    df['change_percent'] = pd.to_numeric(df['change_percent'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    
    # --- FILTER KRITERIA ---
    # 1. Harga > 50 (Bukan gocap)
    # 2. Volume > 0 (Tidak tidur)
    df_active = df[(df['last'] > 50) & (df['volume'] > 0)].copy()
    
    signals = []
    now = datetime.now()
    is_open = (9 <= now.hour < 16) and (now.weekday() < 5)

    for _, row in df_active.iterrows():
        ticker = row['symbol']
        price = row['last']
        chg = row['change_percent']
        vol = row['volume']
        
        status = "🔎 Monitor"
        alert_needed = False
        limit_pct = get_limit(price)
        
        # Logika Sinyal
        if chg >= limit_pct:
            status = "🔥 ARA"
            alert_needed = True
        elif chg >= 10:
            status = "📈 STRONG"
            alert_needed = True
        elif 3 <= chg < 10:
            status = "🚀 MOVE"
            # Kita hanya alert saham MOVE jika volumenya cukup besar (misal > 50rb lot)
            if vol > 50000: alert_needed = True

        if alert_needed and is_open:
            send_push(f"{status}: {ticker}", f"Rp {int(price)} ({chg:.2f}%) | Vol: {int(vol)}")

        signals.append({
            "Ticker": ticker,
            "Price": int(price),
            "Chg%": round(chg, 2),
            "Volume": int(vol),
            "Signal": status
        })

    if signals:
        df_final = pd.DataFrame(signals)
        
        # TAMPILAN TAB
        tab1, tab2 = st.tabs(["🚀 MOMENTUM (3% UP)", "📉 DROPPING (>10% DOWN)"])
        
        with tab1:
            # Saham yang naik di atas 3%, diurutkan dari volume terbesar
            df_up = df_final[df_final['Chg%'] >= 3].sort_values(by='Volume', ascending=False)
            st.dataframe(df_up, use_container_width=True, hide_index=True)
            
        with tab2:
            # Saham yang turun di bawah -10%
            df_down = df_final[df_final['Chg%'] <= -10].sort_values(by='Chg%', ascending=True)
            st.dataframe(df_down, use_container_width=True, hide_index=True)
else:

    st.error("Gagal menarik data dari API GoAPI. Cek API Key Anda.")
