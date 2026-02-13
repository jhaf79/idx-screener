import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import requests

# --- 1. SETTING HALAMAN ---
st.set_page_config(page_title="IDX Pro Radar", layout="wide", page_icon="🏹")

# PUSH_TOKEN Langsung (Ganti jika perlu)
PUSH_TOKEN = "o.xCp2U6AnZALtYIpfF5lTMNSccKgcUoi3"

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

def get_limit(price):
    """Batas Auto Rejection IDX"""
    if 50 <= price <= 200: return 34.0
    if 200 < price <= 5000: return 24.0
    return 19.0

# --- 3. DAFTAR SAHAM (Watchlist) ---
WATCHLIST = [
    'ADRO.JK', 'BRMS.JK', 'UNIC.JK', 'BBRI.JK', 'PTRO.JK', 'ASII.JK', 
    'ANTM.JK', 'PTBA.JK', 'MEDC.JK', 'HRUM.JK', 'BBNI.JK', 'BMRI.JK', 
    'AMMN.JK', 'BUMI.JK', 'TPIA.JK', 'BBCA.JK', 'UNTR.JK', 'KLBF.JK',
    'OPMS.JK', 'MBMA.JK', 'KPIG.JK', 'INDS.JK', 'BELL.JK', 'BIPI.JK',
    'BULL.JK', 'MDKA.JK', 'ELTY.JK', 'ZATA.JK', 'TRIN.JK', 'UNSP.JK',
    'ROCK.JK', 'JIHD.JK', 'FITT.JK', 'BEST.JK', 'MSIN.JK', 'SOCI.JK',
    'BUVA.JK', 'DEWA.JK', 'IFSH.JK', 'INDY.JK', 'BKSL.JK', 'NCKL.JK'
]

st.title("🏹 IDX Real-time Radar: ARA & LONGSOR")
st.write(f"🕒 Terakhir Update: {datetime.now().strftime('%H:%M:%S')} WIB")

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
    # Notif aktif jam 09:00 - 16:00
    is_open = 9 <= datetime.now().hour < 16 
    
    for ticker in WATCHLIST:
        try:
            df_s = raw_data[ticker]
            if len(df_s) < 2: continue

            last_price = float(df_s['Close'].iloc[-1])
            prev_close = float(df_s['Close'].iloc[-2])
            change = ((last_price - prev_close) / prev_close) * 100
            
            status = "🔎 Monitoring"
            alert_needed = False
            
            # Batas ARA/ARB
            limit_pct = get_limit(last_price)
            
            # Logika Sinyal
            if change >= limit_pct:
                status = "🔥 NEAR ARA"
                alert_needed = True
            elif change >= 15:
                status = "📈 STRONG UP"
                alert_needed = True
            elif change <= -limit_pct:
                status = "💀 NEAR ARB (LONGSOR)"
                alert_needed = True
            elif change <= -10:
                status = "📉 SHARP DROP"
                alert_needed = True

            # KIRIM NOTIFIKASI
            if alert_needed and is_open:
                send_push(f"IDX ALERT: {ticker}", f"Harga: {int(last_price)} ({change:.2f}%) - {status}")

            signals.append({
                "Ticker": ticker.replace('.JK', ''),
                "Harga": int(last_price),
                "Chg%": round(change, 2),
                "Sinyal": status
            })
        except:
            continue

    if signals:
        # Urutkan dari perubahan tertinggi (top gainer di atas, top loser di bawah)
        df_display = pd.DataFrame(signals).sort_values(by='Chg%', ascending=False)
        
        def color_signal(val):
            if "ARA" in val or "UP" in val: color = '#2ecc71' # Hijau
            elif "ARB" in val or "DROP" in val: color = '#e74c3c' # Merah
            else: color = 'white'
            return f'color: {color}; font-weight: bold'

        st.table(df_display.style.applymap(color_signal, subset=['Sinyal']))
else:
    st.error("Gagal mengambil data. Coba reboot app di dashboard Streamlit.")
