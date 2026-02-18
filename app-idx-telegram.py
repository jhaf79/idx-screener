import requests
import pandas as pd
import yfinance as yf
from datetime import datetime
import time

# ======================================
# KONFIGURASI TELEGRAM
# ======================================
CHAT_ID = "8522780166"
BOT_TOKEN = "8251324177:AAHOOY4BECy0WDH3GjW4GjRURaMoKPzuAKo"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"❌ Gagal kirim Telegram: {e}")

# ======================================
# 1️⃣ AMBIL DAFTAR SAHAM DARI IDX
# ======================================
print("📊 Mengambil daftar saham IDX...")
url = "https://www.idx.co.id/umbraco/Surface/ListedCompany/GetCompanyProfiles?emitenType=s"

# KRUSIAL: Tambahkan Headers agar tidak dianggap bot
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Referer": "https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/"
}

symbols = []
try:
    r = requests.get(url, headers=headers, timeout=15)
    if r.status_code == 200:
        data = r.json()
        if "data" in data:
            for item in data["data"]:
                code = item["KodeEmiten"]
                symbols.append(code + ".JK")
            print(f"✅ Berhasil mengambil {len(symbols)} emiten.")
        else:
            print("⚠️ Struktur JSON IDX berubah.")
    else:
        print(f"❌ Error HTTP {r.status_code}: Server IDX menolak akses.")
except Exception as e:
    print(f"❌ Gagal koneksi ke IDX: {e}")

# ======================================
# 2️⃣ SCREENING HARGA DARI YAHOO FINANCE
# ======================================
if not symbols:
    print("🛑 Tidak ada simbol untuk diproses. Berhenti.")
    exit()

print("🔍 Memeriksa harga saham (ini mungkin memakan waktu)...")
results = []

# Batasi jumlah simbol untuk testing jika perlu, misal: symbols[:50]
for symbol in symbols:
    try:
        # Mengambil data 7 hari untuk memastikan dapat 5 candle bursa yang valid
        df = yf.download(symbol, period="7d", interval="1d", progress=False)
        
        if df.empty or len(df) < 2:
            continue

        # Ambil harga penutupan terakhir dan sebelumnya
        last_close = float(df["Close"].iloc[-1])
        prev_close = float(df["Close"].iloc[-2])
        first_close = float(df["Close"].iloc[0]) # Harga 7 hari lalu/awal periode
        
        change = ((last_close - prev_close) / prev_close) * 100
        five_days_change = ((last_close - first_close) / first_close) * 100

        # Filter harga sesuai kriteria Anda
        if 100 <= last_close <= 1000:
            # Cek kriteria ARA atau Multibagger
            if change >= 20 or five_days_change >= 50:
                results.append({
                    "symbol": symbol.replace(".JK", ""),
                    "price": last_close,
                    "change": change,
                    "5d_change": five_days_change
                })
                print(f"⭐ Match: {symbol} ({change:.2f}%)")

    except Exception as e:
        # Skip jika ada error pada simbol tertentu (misal saham delisted)
        continue

# ======================================
# 3️⃣ KIRIM KE TELEGRAM
# ======================================
if results:
    # Urutkan berdasarkan kenaikan harian tertinggi
    df_results = pd.DataFrame(results).sort_values(by="change", ascending=False).head(15)
    
    msg = "🔥 <b>15 SAHAM POTENSI ARA / MULTIBAGGER</b>\n"
    msg += f"🕗 {datetime.now().strftime('%d-%m-%Y %H:%M')}\n"
    msg += "───────────────────\n\n"

    for _, row in df_results.iterrows():
        msg += f"📈 <b>{row['symbol']}</b>\n"
        msg += f"Harga: Rp{int(row['price']):,}\n"
        msg += f"Harian: {row['change']:.2f}%\n"
        msg += f"5 Hari: {row['5d_change']:.2f}%\n\n"

    send_telegram(msg)
    print("✅ Laporan terkirim ke Telegram!")
else:
    send_telegram("⚠️ Tidak ditemukan saham yang memenuhi kriteria ARA/Multibagger hari ini.")
    print("⚠️ Tidak ada hasil.")
