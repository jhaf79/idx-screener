import streamlit as st
import yfinance as yf
import pandas as pd
from streamlit_autorefresh import st_autorefresh
from datetime import datetime
import requests

# --- 1. KONFIGURASI ---
st.set_page_config(page_title="IDX Momentum Radar", layout="wide")
PUSH_TOKEN = "o.xCp2U6AnZALtYIpfF5lTMNSccKgcUoi3"
st_autorefresh(interval=30000, key="idx_final_radar")

# --- 2. DAFTAR SAHAM (Watchlist Anda + Gabungan Terfilter) ---
RAW_WATCHLIST = [
    'ADMR.JK', 'ADRO.JK', 'AKRA.JK', 'AMMN.JK', 'AMRT.JK', 'ANKM.JK', 'ANTM.JK', 
    'ASII.JK', 'AUTO.JK', 'AWAN.JK', 'BAIK.JK', 'BBCA.JK', 'BBNI.JK', 'BBRI.JK', 
    'BBTN.JK', 'BBYB.JK', 'BCIC.JK', 'BEBS.JK', 'BELI.JK', 'BELL.JK', 'BEST.JK', 
    'BFIN.JK', 'BIPI.JK', 'BIRD.JK', 'BKSL.JK', 'BMRI.JK', 'BRIS.JK', 'BRMS.JK', 
    'BRPT.JK', 'BSDE.JK', 'BUKA.JK', 'BULL.JK', 'BUMI.JK', 'BUVA.JK', 'CARE.JK', 
    'CARS.JK', 'CHIP.JK', 'CPIN.JK', 'CUAN.JK', 'DAAZ.JK', 'DEWA.JK', 'DOID.JK', 
    'DOOH.JK', 'ELSA.JK', 'ELTY.JK', 'ENRG.JK', 'ESSA.JK', 'FILM.JK', 'FIRE.JK', 
    'FITT.JK', 'FORU.JK', 'GEMS.JK', 'GGRM.JK', 'GOTO.JK', 'HEAL.JK', 'HOKI.JK', 
    'HRUM.JK', 'HUMI.JK', 'ICBP.JK', 'IFSH.JK', 'INCO.JK', 'INDF.JK', 'INDY.JK', 
    'INDS.JK', 'INKP.JK', 'ISAT.JK', 'ITMA.JK', 'ITMG.JK', 'JIHD.JK', 'KAYU.JK', 
    'KEEN.JK', 'KIJA.JK', 'KLBF.JK', 'KPIG.JK', 'LPKR.JK', 'LPPF.JK', 'MAIN.JK', 
    'MAPA.JK', 'MAPI.JK', 'MBMA.JK', 'MDKA.JK', 'MDSS.JK', 'MEDC.JK', 'MIKA.JK', 
    'MINA.JK', 'MLPL.JK', 'MPPA.JK', 'MSIN.JK', 'MTEL.JK', 'MYOR.JK', 'NANO.JK', 
    'NATO.JK', 'NCKL.JK', 'NZIA.JK', 'OPMS.JK', 'PADI.JK', 'PANI.JK', 'PANR.JK', 
    'PEGE.JK', 'PGAS.JK', 'PGRS.JK', 'PNBN.JK', 'PNLF.JK', 'PTBA.JK', 'PTRO.JK', 
    'PTPP.JK', 'RAJA.JK', 'RLCO.JK', 'RMKE.JK', 'ROCK.JK', 'SAGE.JK', 'SBMA.JK', 
    'SCMA.JK', 'SGER.JK', 'SIDO.JK', 'SMGR.JK', 'SMRA.JK', 'SOCI.JK', 'SOUL.JK', 
    'SRTG.JK', 'SSIA.JK', 'STAA.JK', 'STRK.JK', 'SUPA.JK', 'TGUK.JK', 'TINS.JK', 
    'TLKM.JK', 'TOWR.JK', 'TPIA.JK', 'TRIN.JK', 'TRIS.JK', 'TRUK.JK', 'TYRE.JK', 
    'UNIC.JK', 'UNSP.JK', 'UNTR.JK', 'UNVR.JK', 'VKTR.JK', 'WIDI.JK', 'WIFI.JK', 
    'WIIM.JK', 'WIKA.JK', 'WTON.JK', 'YPAS.JK', 'ZATA.JK'
]
WATCHLIST = sorted(list(set(RAW_WATCHLIST)))

# --- 3. FUNGSI ---
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

# --- 4. TAMPILAN HEADER ---
st.title("🏹 IDX Super Radar (30s)")
st.caption(f"Update Terakhir: {datetime.now().strftime('%H:%M:%S')} WIB")

# --- 5. DATA PROCESSING ---
@st.cache_data(ttl=25)
def fetch_data(tickers):
    try: return yf.download(tickers, period="10d", interval="1d", group_by='ticker', progress=False)
    except: return None

raw_data = fetch_data(WATCHLIST)

if raw_data is not None and not raw_data.empty:
    signals = []
    now = datetime.now()
    # Jam bursa: Senin-Jumat, 09:00-16:00 WIB
    is_open = (9 <= now.hour < 16) and (now.weekday() < 5)
    
    for ticker in WATCHLIST:
        try:
            df_s = raw_data[ticker]
            if len(df_s) < 3: continue

            last_price = float(df_s['Close'].iloc[-1])
            prev_close = float(df_s['Close'].iloc[-2])
            change = ((last_price - prev_close) / prev_close) * 100
            
            # Data Volume
            last_vol = df_s['Volume'].iloc[-1]
            avg_vol = df_s['Volume'].iloc[-6:-1].mean()
            
            # --- FILTER: ANTI SAHAM TIDUR ---
            if last_vol == 0: continue

            # Volume Spike (1.5x Rata-rata)
            is_spike = last_vol > (avg_vol * 1.5) if avg_vol > 0 else False
            vol_label = "⚡" if is_spike else ""

            limit_pct = get_limit(last_price)
            status = "🔎 Monitor"
            alert_needed = False
            
            # Logika Signal
            if change >= limit_pct: status = "🔥 ARA"; alert_needed = True
            elif change >= 10: status = "📈 STRONG"; alert_needed = True
            elif 3 <= change < 10: status = "🚀 MOVE"; alert_needed = True
            elif change <= -limit_pct: status = "💀 ARB"; alert_needed = True
            elif change <= -10: status = "📉 DROP"; alert_needed = True

            # Kirim Notifikasi
            if alert_needed and is_open:
                spike_txt = " +SPIKE" if is_spike else ""
                send_push(f"{status}{spike_txt}: {ticker.replace('.JK','')}", f"{int(last_price)} ({change:.2f}%)")

            signals.append({
                "Ticker": ticker.replace('.JK', ''),
                "Price": int(last_price),
                "Chg%": round(change, 2),
                "Spike": vol_label,
                "Signal": status,
                "Vol": int(last_vol),
                "is_spike": is_spike
            })
        except: continue

    if signals:
        df_display = pd.DataFrame(signals)
        tab1, tab2 = st.tabs(["⚡ HIGH VOLUME SPIKE", "📋 ALL ACTIVE"])
        
        with tab1:
            # Hanya tampilkan yang Spike ⚡
            df_spike = df_display[df_display['is_spike'] == True].sort_values(by='Chg%', ascending=False)
            if not df_spike.empty:
                st.dataframe(df_spike.drop(columns=['is_spike']), use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada lonjakan volume terdeteksi.")
        
        with tab2:
            # Semua yang tidak tidur, urut dari kenaikan tertinggi
            st.dataframe(df_display.drop(columns=['is_spike']).sort_values(by='Chg%', ascending=False), 
                         use_container_width=True, hide_index=True)
else:
    st.error("Gagal memuat data dari Yahoo Finance.")

# --- 6. TOMBOL TES PUSHBULLET (DI BAWAH) ---
st.divider()
if st.button("🔔 TES NOTIFIKASI KE HP"):
    send_push("✅ TEST RADAR", "Notifikasi berhasil terhubung ke radar Anda!")
    st.success("Cek HP Anda sekarang!")
