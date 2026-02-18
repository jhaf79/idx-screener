import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import io

# ======================================
# KONFIGURASI TELEGRAM
# ======================================
CHAT_ID = "8522780166"
BOT_TOKEN = "8251324177:AAHOOY4BECy0WDH3GjW4GjRURaMoKPzuAKo"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"❌ Gagal kirim Telegram: {e}")

# ======================================
# 1️⃣ AMBIL DAFTAR SAHAM (MULTI-BACKUP)
# ======================================
print("📊 Mengambil daftar saham...")

symbols = []
# Sumber Alternatif 1: GitHub Gist (List Emiten IDX 2024/2025)
alt_url = "https://raw.githubusercontent.com/m-fathir/daftar-saham-idx/main/emiten.csv"

try:
    r = requests.get(alt_url, timeout=10)
    if r.status_code == 200:
        df_list = pd.read_csv(io.StringIO(r.text))
        # Mengambil kolom pertama yang biasanya berisi Kode Emiten
        raw_codes = df_list.iloc[:, 0].tolist()
        symbols = [str(c).strip() + ".JK" for c in raw_codes if len(str(c).strip()) <= 4]
        print(f"✅ Berhasil memuat {len(symbols)} saham dari repo.")
except:
    print("⚠️ Repo tidak dapat diakses.")

# JIKA REPO GAGAL, GUNAKAN DAFTAR MANUAL (EMERGENCY LIST)
if not symbols:
    print("📢 Menggunakan daftar saham populer (Emergency List)...")
    emergency_list = [
        "BBCA", "BBRI", "BMRI", "BBNI", "TLKM", "ASII", "GOTO", "BUMI", "BRMS", 
        "BRPT", "TPIA", "AMMN", "CUAN", "BREN", "PTBA", "ADRO", "UNTR", "PGAS",
        "ANTM", "INCO", "MDKA", "MEDC", "CPIN", "ICBP", "UNVR", "KLBF", "SMGR"
    ]
    symbols = [s + ".JK" for s in emergency_list]

# ======================================
# 2️⃣ SCREENING HARGA & VOLUME
# ======================================
print(f"🔍 Mulai screening {len(symbols)} saham...")
results = []

for symbol in symbols:
    try:
        # Ambil data 10 hari untuk keamanan perhitungan
        df = yf.download(symbol, period="10d", interval="1d", progress=False)
        
        if df.empty or len(df) < 5:
            continue

        # Perbaikan FUTUREWARNING: Gunakan .item()
        last_close = df["Close"].iloc[-1].item()
        prev_close = df["Close"].iloc[-2].item()
        start_close = df["Close"].iloc[-5].item() # Harga 5 hari bursa lalu
        
        # Data Volume
        current_vol = df["Volume"].iloc[-1].item()
        avg_vol = df["Volume"].iloc[-6:-1].mean().item()

        # Perhitungan
        daily_change = ((last_close - prev_close) / prev_close) * 100
        five_day_change = ((last_close - start_close) / start_close) * 100
        vol_spike = current_vol / avg_vol if avg_vol > 0 else 0

        # --- KRITERIA SCREENING ---
        # 1. Harga antara 100 - 1500
        # 2. Daily Naik > 10% ATAU 5-Hari Naik > 30%
        if 100 <= last_close <= 1500:
            if daily_change >= 10 or five_day_change >= 30:
                results.append({
                    "symbol": symbol.replace(".JK", ""),
                    "price": last_close,
                    "change": daily_change,
                    "5d_change": five_day_change,
                    "vol_spike": vol_spike
                })
                print(f"⭐ Match: {symbol} | +{daily_change:.2f}%")

    except Exception:
        continue

# ======================================
# 3️⃣ URUTKAN & KIRIM KE TELEGRAM
# ======================================
if results:
    # Urutkan dari kenaikan tertinggi
    df_res = pd.DataFrame(results).sort_values(by="change", ascending=False).head(15)
    
    waktu = datetime.now().strftime('%d/%m/%Y %H:%M')
    msg = f"🚀 <b>IDX TOP RADAR</b>\n📅 {waktu}\n"
    msg += "───────────────────\n\n"

    for _, row in df_res.iterrows():
        # Emoji api jika ada lonjakan volume > 2x lipat
        emoji = "🔥" if row['vol_spike'] > 2 else "📈"
        msg += f"{emoji} <b>{row['symbol']}</b>\n"
        msg += f"Harga: Rp{int(row['price']):,}\n"
        msg += f"Harian: {row['change']:.2f}%\n"
        msg += f"5 Hari: {row['5d_change']:.2f}%\n"
        msg += f"Vol Spike: {row['vol_spike']:.1f}x\n\n"

    send_telegram(msg)
    print("✅ Berhasil dikirim!")
else:
    send_telegram("⚠️ Tidak ada saham yang masuk kriteria radar hari ini.")
    print("⚠️ Tidak ada hasil.")
