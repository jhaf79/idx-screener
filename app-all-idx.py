import streamlit as st
import requests
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# --- 1. SETTING HALAMAN ---
st.set_page_config(page_title="IDX Global Radar", layout="wide")

# INPUT API KEY ANDA DI SINI
API_KEY = "e23149f0-8a2f-55c7-25bd-52abff88"
PUSH_TOKEN = "o.xCp2U6AnZALtYIpfF5lTMNSccKgcUoi3"

st_autorefresh(interval=60000, key="idx_full_scan")

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

st.title("🏹 IDX Full Market Momentum")
st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} WIB")

# --- 3. AMBIL DATA SELURUH SAHAM ---
@st.cache_data(ttl=50)
def fetch_all():
    try:
        url = f"https://api.goapi.io/v1/stock/idx/prices?api_key={API_KEY}"
        res = requests.get(url, timeout=10)
        if res.status_code == 200:
            return res.json()['data']['results']
        else:
            return f"Error API: {res.status_code}"
    except Exception as e:
        return f"Error Koneksi: {str(e)}"

data_raw = fetch_all()

# Cek jika data_raw adalah string (berarti error)
if isinstance(data_raw, str):
    st.error(data_raw)
    st.info("💡 Pastikan API Key di baris 11 sudah benar dan akun GoAPI Anda aktif.")
elif data_raw:
    df = pd.DataFrame(data_raw)
    
    # Cleaning Data
    df['last'] = pd.to_numeric(df['last'], errors='coerce')
    df['change_percent'] = pd.to_numeric(df['change_percent'], errors='coerce')
    df['volume'] = pd.to_numeric(df['volume'], errors='coerce')
    
    # FILTER: Harga > 50 & Ada Transaksi (Bukan Saham Tidur)
    df = df[(df['last'] > 50) & (df['volume'] > 0)].dropna()

    signals = []
    now = datetime.now()
    is_open = (9 <= now.hour < 16) and (now.weekday() < 5)

    for _, row in df.iterrows():
        ticker = row['symbol']
        price = int(row['last'])
        chg = row['change_percent']
        vol = int(row['volume'])
        
        # Penentuan Status
        limit = get_limit(price)
        status = "🔎 Monitor"
        alert = False
        
        if chg >= limit:
            status = "🔥 ARA"
            alert = True
        elif chg >= 10:
            status = "📈 STRONG"
            alert = True
        elif 3 <= chg < 10:
            status = "🚀 MOVE"
            # Hanya alert MOVE jika volume lumayan (diatas 20rb lot / 2jt lembar)
            if vol > 2000000: alert = True
        elif chg <= -limit:
            status = "💀 ARB"
            alert = True
        elif chg <= -10:
            status = "📉 DROP"
            alert = True

        if alert and is_open:
            send_push(f"{status}: {ticker}", f"{price} ({chg:.2f}%) Vol: {vol:,}")

        signals.append({
            "Ticker": ticker,
            "Price": price,
            "Chg%": round(chg, 2),
            "Volume": vol,
            "Signal": status
        })

    if signals:
        df_final = pd.DataFrame(signals)
        
        # Tab Tampilan
        t1, t2 = st.tabs(["🚀 HIGH MOMENTUM (UP)", "📉 DROPPING (DOWN)"])
        
        with t1:
            # Tampilkan yang naik, urutkan dari Volume terbesar (Spike)
            df_up = df_final[df_final['Chg%'] >= 3].sort_values(by='Volume', ascending=False)
            st.dataframe(df_up, use_container_width=True, hide_index=True)
            
        with t2:
            df_down = df_final[df_final['Chg%'] <= -3].sort_values(by='Chg%', ascending=True)
            st.dataframe(df_down, use_container_width=True, hide_index=True)

else:
    st.warning("Data kosong. Mungkin market sedang libur atau API limit.")

