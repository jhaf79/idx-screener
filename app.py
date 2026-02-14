import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import requests

# --- 1. SETTING HALAMAN ---
st.set_page_config(page_title="IDX Pro Radar", layout="wide", page_icon="🏹")

# PUSH_TOKEN Langsung
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
    'BUVA.JK', 'DEWA.JK', 'IFSH.JK', 'INDY.JK', 'BKSL.JK', 'NCKL.JK'
]

st.title("🏹 IDX Real-time Radar: Momentum Hunter")
st.write(f"🕒 Update: {datetime.now().strftime('%H:%M:%S')} WIB")

# --- 4. PENGAMBILAN DATA ---
@st.cache_data(ttl=55)
def fetch_data(tickers):
    try:
        # Ambil 10 hari terakhir agar bisa hitung rata-rata volume
        return yf.download(tickers, period="10d", interval="1d", group_by='ticker', progress=False)
    except:
        return None

raw_data = fetch_data(WATCHLIST)

if raw_data is not None and not raw_data.empty:
    signals = []
    # Notif aktif Senin-Jumat jam 09:00 - 16:00
    is_open = (9 <= datetime.now().hour < 16) and (datetime.now().weekday() < 5)
    
    for ticker in WATCHLIST:
        try:
            df_s = raw_data[ticker]
            if len(df_s) < 3: continue

            last_price = float(df_s['Close'].iloc[-1])
            prev_close = float(df_s['Close'].iloc[-2])
            change = ((last_price - prev_close) / prev_close) * 100
            
            # Deteksi Volume (Bandingkan volume hari ini dengan rata-rata 5 hari)
            last_vol = df_s['Volume'].iloc[-1]
            avg_vol = df_s['Volume'].iloc[-6:-1].mean()
            vol_spike = last_vol > (avg_vol * 1.5) # Volume naik 50% dari biasanya

            status = "🔎 Monitoring"
            alert_needed = False
            
            limit_pct = get_limit(last_price)
            
            # --- LOGIKA SINYAL (HIERARKI) ---
            if change >= limit_pct:
                status = "🔥 NEAR ARA"
                alert_needed = True
            elif change >= 15:
                status = "📈 STRONG UP"
                alert_needed = True
            elif 3 <= change <= 7 and vol_spike:
                status = "🚀 POTENTIAL MOVE (Awal Naik)"
                alert_needed = True
            elif change <= -limit_pct:
                status = "💀 NEAR ARB (LONGSOR)"
                alert_needed = True
            elif change <= -10:
                status = "📉 SHARP DROP"
                alert_needed = True

            if alert_needed and is_open:
                send_push(f"IDX ALERT: {ticker}", f"Prc: {int(last_price)} ({change:.2f}%) - {status}")

            signals.append({
                "Ticker": ticker.replace('.JK', ''),
                "Harga": int(last_price),
                "Chg%": round(change, 2),
                "Vol Spike": "YES" if vol_spike else "NO",
                "Sinyal": status
            })
        except:
            continue

    if signals:
        df_display = pd.DataFrame(signals).sort_values(by='Chg%', ascending=False)
        
        # Pewarnaan Tabel
        def color_status(val):
            if "ARA" in val or "STRONG" in val: color = '#2ecc71'
            elif "POTENTIAL" in val: color = '#f1c40f' # Kuning untuk awal naik
            elif "ARB" in val or "DROP" in val: color = '#e74c3c'
            else: color = 'white'
            return f'color: {color}; font-weight: bold'

        st.table(df_display.style.applymap(color_status, subset=['Sinyal']))
else:
    st.error("Data tidak termuat. Pastikan jam bursa atau cek koneksi server.")
