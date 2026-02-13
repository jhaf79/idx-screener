import streamlit as st
import requests
import pandas as pd
import yfinance as yf
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# --- CONFIG (WAJIB ISI) ---
PUSH_TOKEN = "ISI_TOKEN_PUSHBULLET_ANDA"
API_KEY = "ISI_API_KEY_GOAPI_ANDA"

# Refresh otomatis setiap 3 menit
st_autorefresh(interval=180000, key="idx_hunter_counter")

# --- FUNGSI PENDUKUNG ---
@st.cache_data(ttl=3600)
def get_metrics(ticker):
    try:
        df = yf.download(f"{ticker}.JK", period="40d", progress=False)
        if len(df) < 21: return None
        return {
            'high_20d': float(df['High'].iloc[-21:-1].max()),
            'avg_vol_20d': float(df['Volume'].iloc[-21:-1].mean()),
            'prev_close': float(df['Close'].iloc[-2]),
            'prev_change': float(((df['Close'].iloc[-2] - df['Open'].iloc[-2])/df['Open'].iloc[-2])*100)
        }
    except: return None

def get_market_class(mkt_cap):
    mkt_cap_triliun = mkt_cap / 1e12
    if mkt_cap_triliun > 100: return "💎 LAPIS 1"
    if 10 <= mkt_cap_triliun <= 100: return "🥈 LAPIS 2"
    return "🔥 LAPIS 3"

def send_push(title, body):
    requests.post('https://api.pushbullet.com/v2/pushes', 
                  headers={'Access-Token': PUSH_TOKEN}, 
                  json={"type": "note", "title": title, "body": body})

def get_ara_limit(price):
    if 50 <= price <= 200: return 34.0
    if 200 < price <= 5000: return 24.0
    return 19.0

# --- UI STREAMLIT ---
st.set_page_config(page_title="IDX Pro Hunter", layout="wide")
st.title("🏹 IDX Full Market Radar")
st.write(f"Terakhir Scan: {datetime.now().strftime('%H:%M:%S')} WIB")

# --- PROSES SCANNING ---
with st.spinner('Memindai seluruh bursa...'):
    url = f"https://api.goapi.io/v1/stock/idx/prices?api_key={API_KEY}"
    res = requests.get(url)
    
    if res.status_code == 200:
        all_data = res.json()['data']['results']
        df = pd.DataFrame(all_data)
        
        # Filter awal agar tidak terlalu berat (Naik > 4%)
        candidates = df[pd.to_numeric(df['change_percent']) > 4].copy()
        
        signals = []
        for _, row in candidates.iterrows():
            ticker = row['symbol']
            price = float(row['last'])
            chg = float(row['change_percent'])
            vol = float(row['volume'])
            
            m = get_metrics(ticker)
            if not m: continue
            
            # Ambil Market Cap dari yfinance
            info = yf.Ticker(f"{ticker}.JK").info
            mkt_cap = info.get('marketCap', 0)
            kelas = get_market_class(mkt_cap)
            
            # Logika Deteksi
            alert_type = None
            if chg >= get_ara_limit(price): alert_type = "🔥 NEAR ARA"
            elif price > m['high_20d'] and vol > (m['avg_vol_20d'] * 1.5): alert_type = "🚀 BREAKOUT"
            elif chg > 10 and m['prev_change'] > 15: alert_type = "📈 REPEAT ARA"
            
            if alert_type:
                msg = f"[{kelas}] {ticker} @{price} ({chg}%)"
                send_push(alert_type, msg)
                signals.append({"Signal": alert_type, "Ticker": ticker, "Price": price, "Kelas": kelas})

        if signals:
            st.table(pd.DataFrame(signals))
        else:
            st.info("Belum ada pergerakan panas terdeteksi.")