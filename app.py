import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import requests

# --- 1. SETTING HALAMAN ---
st.set_page_config(page_title="IDX Momentum", layout="wide")

PUSH_TOKEN = "o.xCp2U6AnZALtYIpfF5lTMNSccKgcUoi3"
st_autorefresh(interval=60000, key="idx_final_notif")

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

st.title("🏹 IDX Momentum Radar")
st.caption(f"Update: {datetime.now().strftime('%H:%M:%S')} WIB")

# --- 4. DATA PROCESSING ---
@st.cache_data(ttl=55)
def fetch_data(tickers):
    try: return yf.download(tickers, period="5d", interval="1d", group_by='ticker', progress=False)
    except: return None

raw_data = fetch_data(WATCHLIST)

if raw_data is not None and not raw_data.empty:
    signals = []
    now = datetime.now()
    is_open = (9 <= now.hour < 16) and (now.weekday() < 5)
    
    for ticker in WATCHLIST:
        try:
            df_s = raw_data[ticker]
            if len(df_s) < 2: continue

            last_price = float(df_s['Close'].iloc[-1])
            prev_close = float(df_s['Close'].iloc[-2])
            change = ((last_price - prev_close) / prev_close) * 100
            
            status = "🔎 Monitor"
            alert_needed = False
            limit_pct = get_limit(last_price)
            
            # --- LOGIKA STATUS TANPA JEDA ---
            if change >= limit_pct:
                status = "🔥 ARA"
                alert_needed = True
            elif change >= 10:
                status = "📈 STRONG"
                alert_needed = True
            elif 3 <= change < 10:
                status = "🚀 MOVE"
                alert_needed = True
            elif change <= -limit_pct:
                status = "💀 ARB"
                alert_needed = True
            elif change <= -10:
                status = "📉 DROP"
                alert_needed = True

            # NOTIFIKASI SEBARIS/RINGKAS
            if alert_needed and is_open:
                send_push(f"{status}: {ticker.replace('.JK','')}", f"{int(last_price)} ({change:.2f}%)")

            signals.append({
                "Ticker": ticker.replace('.JK', ''),
                "Price": int(last_price),
                "Chg%": round(change, 2),
                "Signal": status
            })
        except: continue

    if signals:
        df_display = pd.DataFrame(signals).sort_values(by='Chg%', ascending=False)
        
        # TAMPILAN SEBARIS (Dataframe lebih rapi di HP daripada Table)
        st.dataframe(
            df_display,
            column_config={
                "Ticker": st.column_config.TextColumn("Ticker"),
                "Price": st.column_config.NumberColumn("Price", format="Rp %d"),
                "Chg%": st.column_config.NumberColumn("Chg%", format="%.2f%%"),
                "Signal": st.column_config.TextColumn("Signal")
            },
            hide_index=True,
            use_container_width=True
        )
else:
    st.error("Gagal memuat data.")
