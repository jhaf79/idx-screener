import streamlit as st
import requests
import pandas as pd
import yfinance as yf
from streamlit_autorefresh import st_autorefresh
from datetime import datetime

# --- 1. CONFIG (Wajib di baris pertama) ---
st.set_page_config(page_title="IDX Pro Hunter", layout="wide", page_icon="🏹")

# Ambil Secrets dari Streamlit Cloud
try:
    PUSH_TOKEN = st.secrets["PUSH_TOKEN"]
    API_KEY = st.secrets["API_KEY"]
except:
    st.error("Secrets belum dikonfigurasi! Masukkan PUSH_TOKEN dan API_KEY di Settings > Secrets.")
    st.stop()

# Refresh otomatis setiap 3 menit
count = st_autorefresh(interval=180000, key="idx_hunter_counter")

# --- 2. FUNGSI PENDUKUNG ---
@st.cache_data(ttl=3600)
def get_metrics(ticker):
    try:
        df_h = yf.download(f"{ticker}.JK", period="40d", progress=False)
        if len(df_h) < 21: return None
        return {
            'high_20d': float(df_h['High'].iloc[-21:-1].max()),
            'avg_vol_20d': float(df_h['Volume'].iloc[-21:-1].mean()),
            'prev_close': float(df_h['Close'].iloc[-2]),
            'prev_change': float(((df_h['Close'].iloc[-2] - df_h['Open'].iloc[-2])/df_h['Open'].iloc[-2])*100)
        }
    except: return None

def get_market_class(mkt_cap):
    if not mkt_cap: return "🔥 LAPIS 3"
    mkt_cap_triliun = mkt_cap / 1e12
    if mkt_cap_triliun > 100: return "💎 LAPIS 1"
    if 10 <= mkt_cap_triliun <= 100: return "🥈 LAPIS 2"
    return "🔥 LAPIS 3"

def send_push(title, body):
    try:
        requests.post('https://api.pushbullet.com/v2/pushes', 
                      headers={'Access-Token': PUSH_TOKEN}, 
                      json={"type": "note", "title": title, "body": body})
    except: pass

def get_ara_limit(price):
    if 50 <= price <= 200: return 34.0
    if 200 < price <= 5000: return 24.0
    return 19.0

# --- 3. PROSES DATA ---
def run_scanner():
    # Daftar saham yang paling likuid saja agar tidak kena blokir Yahoo
    # Anda bisa menambah daftar ini sampai 50-100 saham
    tickers = ['ADRO.JK', 'BRMS.JK', 'GOTO.JK', 'BBRI.JK', 'TLKM.JK', 
               'ASII.JK', 'ANTM.JK', 'PTBA.JK', 'MEDC.JK', 'HRUM.JK']
    
    data_list = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            hist = s.history(period="2d")
            if len(hist) < 2: continue
            
            last_price = hist['Close'].iloc[-1]
            prev_price = hist['Close'].iloc[-2]
            change = ((last_price - prev_price) / prev_price) * 100
            vol = hist['Volume'].iloc[-1]
            
            data_list.append({
                'symbol': t.replace('.JK', ''),
                'last': last_price,
                'change_percent': change,
                'volume': vol
            })
        except:
            continue
    return pd.DataFrame(data_list)

# --- 4. TAMPILAN UI ---
st.title("🏹 IDX Full Market Radar")
st.caption(f"Update Terakhir: {datetime.now().strftime('%H:%M:%S')} WIB | Refresh Ke-{count}")

df_market = run_scanner()

if df_market is not None:
    # Dashboard Metrics
    col1, col2, col3 = st.columns(3)
    is_open = 9 <= datetime.now().hour < 16
    col1.metric("Status Market", "OPEN" if is_open else "CLOSED", delta=None)
    col2.metric("Total Saham", len(df_market))
    col3.metric("Auto-Refresh", "3 Menit")
    
    st.divider()

    # Filter Kandidat (Testing: > -100 agar muncul semua saat market tutup)
    # Kembalikan ke > 4 untuk penggunaan asli di jam bursa
    candidates = df_market[pd.to_numeric(df_market['change_percent']) > -100].copy()
    
    # Batasi proses agar tidak lemot jika market tutup
    if not is_open:
        st.info("Market Tutup: Menampilkan simulasi 15 saham teratas.")
        candidates = candidates.head(15)

    signals = []
    
    with st.status("Menganalisis pergerakan harga...", expanded=True) as status:
        for _, row in candidates.iterrows():
            ticker = row['symbol']
            price = float(row['last'])
            chg = float(row['change_percent'])
            vol = float(row['volume'])
            
            m = get_metrics(ticker)
            if not m: continue
            
            # Info Lapis (Market Cap)
            try:
                info = yf.Ticker(f"{ticker}.JK").info
                m_cap = info.get('marketCap', 0)
                kelas = get_market_class(m_cap)
            except:
                kelas = "🔥 LAPIS 3"

            # Logika Sinyal
            alert_type = None
            if chg >= get_ara_limit(price): alert_type = "🔥 NEAR ARA"
            elif price > m['high_20d'] and vol > (m['avg_vol_20d'] * 1.5): alert_type = "🚀 BREAKOUT"
            elif chg > 10 and m['prev_change'] > 15: alert_type = "📈 REPEAT ARA"
            
            if alert_type:
                signals.append({
                    "Waktu": datetime.now().strftime('%H:%M'),
                    "Ticker": ticker,
                    "Sinyal": alert_type,
                    "Harga": f"Rp {price:,.0f}",
                    "Change": f"{chg}%",
                    "Kelas": kelas
                })
                # Kirim Notif jika jam bursa
                if is_open:
                    send_push(alert_type, f"{ticker} @{price} ({chg}%) - {kelas}")
            else:
                signals.append({
                    "Waktu": datetime.now().strftime('%H:%M'),
                    "Ticker": ticker,
                    "Sinyal": "🔎 Monitoring",
                    "Harga": f"Rp {price:,.0f}",
                    "Change": f"{chg}%",
                    "Kelas": kelas
                })
        status.update(label="Analisis Selesai!", state="complete", expanded=False)

    # Tampilkan Tabel
    if signals:
        st.subheader("Radar Results")
        res_df = pd.DataFrame(signals)
        
        # Pewarnaan Tabel
        def color_signal(val):
            if "ARA" in val: color = '#ff4b4b'
            elif "BREAKOUT" in val: color = '#29b09d'
            else: color = '#7f7f7f'
            return f'color: {color}; font-weight: bold'

        st.table(res_df.style.applymap(color_signal, subset=['Sinyal']))

