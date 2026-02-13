import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import requests

# --- 1. SETTING HALAMAN ---
st.set_page_config(page_title="IDX Pro Radar", layout="wide", page_icon="🏹")

# Ambil Secrets untuk Pushbullet
try:
    PUSH_TOKEN = "o.xCp2U6AnZALtYIpfF5lTMNSccKgcUoi3"
except:
    st.error("PUSH_TOKEN tidak ditemukan di Secrets!")
    st.stop()

# Refresh setiap 60 detik
st_autorefresh(interval=60000, key="idx_final_notif")

# --- 2. FUNGSI NOTIFIKASI & LOGIKA ---
def send_push(title, body):
    try:
        requests.post('https://api.pushbullet.com/v2/pushes', 
                      headers={'Access-Token': PUSH_TOKEN}, 
                      json={"type": "note", "title": title, "body": body})
    except:
        pass

def get_ara_limit(price):
    if 50 <= price <= 200: return 34.0
    if 200 < price <= 5000: return 24.0
    return 19.0

# --- 3. DAFTAR SAHAM ---
WATCHLIST = [
    'ADRO.JK', 'BRMS.JK', 'UNIC.JK', 'BBRI.JK', 'PTRO.JK', 'ASII.JK', 
    'ANTM.JK', 'PTBA.JK', 'MEDC.JK', 'HRUM.JK', 'BBNI.JK', 'BMRI.JK', 
    'AMMN.JK', 'BUMI.JK', 'TPIA.JK', 'BBCA.JK', 'UNTR.JK', 'KLBF.JK',
    'OPMS.JK', 'MBMA.JK', 'KPIG.JK', 'INDS.JK', 'BELL.JK', 'BIPI.JK',
    'BULL.JK', 'MDKA.JK', 'ELTY.JK', 'ZATA.JK', 'TRIN.JK', 'UNSP.JK',
    'ROCK.JK', 'JIHD.JK', 'FITT.JK', 'BEST.JK', 'MSIN.JK', 'SOCI.JK',
    'BUVA.JK', 'DEWA.JK', 'IFSH.JK', 'INDY.JK', 'BKSL.JK', 'IHSG.JK'
]

st.title("🏹 IDX Real-time Radar + Notif HP")
st.write(f"🕒 Update: {datetime.now().strftime('%H:%M:%S')} WIB")

# --- 4. PENGAMBILAN DATA ---
@st.cache_data(ttl=55)
def fetch_data(tickers):
    try:
        return yf.download(tickers, period="5d", interval="1d", group_by='ticker', progress=False)
    except:
        return None

raw_data = fetch_data(WATCHLIST)

if raw_data is not None and not raw_data.empty:
    signals = []
    is_open = 9 <= datetime.now().hour < 16 # Cek jam bursa
    
    for ticker in WATCHLIST:
        try:
            df_s = raw_data[ticker]
            if len(df_s) < 2: continue

            last_price = float(df_s['Close'].iloc[-1])
            prev_close = float(df_s['Close'].iloc[-2])
            change = ((last_price - prev_close) / prev_close) * 100
            vol = int(df_s['Volume'].iloc[-1])
            
            status = "🔎 Monitoring"
            alert_needed = False
            
            # Logika Sinyal
            if change >= get_ara_limit(last_price):
                status = "🔥 NEAR ARA"
                alert_needed = True
            elif change >= 15:
                status = "📈 STRONG UP"
                alert_needed = True

            # KIRIM NOTIFIKASI (Hanya jika jam bursa & ada sinyal)
            if alert_needed and is_open:
                send_push(f"IDX ALERT: {ticker}", f"Harga: {last_price} ({change:.2f}%) - {status}")

            signals.append({
                "Ticker": ticker.replace('.JK', ''),
                "Harga": int(last_price),
                "Chg%": round(change, 2),
                "Sinyal": status
            })
        except:
            continue

    if signals:
        st.table(pd.DataFrame(signals))
else:
    st.error("Gagal mengambil data. Coba reboot app di dashboard Streamlit.")





