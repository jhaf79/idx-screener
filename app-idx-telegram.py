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
# 1️⃣ AMBIL DAFTAR SAHAM (METODE CADANGAN)
# ======================================
print("📊 Mengambil daftar saham dari sumber alternatif...")

symbols = []
try:
    # Mengambil data dari GitHub yang menyediakan list emiten IDX (lebih stabil untuk server/codespaces)
    # Anda juga bisa menggunakan file lokal jika punya daftar CSV-nya
    url_alt = "https://raw.githubusercontent.com/heruproyogo/idx-list/main/idx-stocks.csv"
    r = requests.get(url_alt, timeout=15)
    
    if r.status_code == 200:
        import io
        df_emiten = pd.read_csv(io.StringIO(r.text))
        # Pastikan kolom sesuai dengan header di CSV tersebut (misal: 'Symbol' atau 'Code')
        for code in df_emiten.iloc[:, 0]: # Mengambil kolom pertama
            symbols.append(str(code).strip() + ".JK")
        print(f"✅ Berhasil mendapatkan {len(symbols)} emiten via Alternatif.")
    else:
        # Jika gagal lagi, gunakan Hardcoded list sebagai usaha terakhir (Emergency list)
        print("⚠️ Gagal akses alternatif, menggunakan daftar manual terbatas...")
        symbols = ["BBCA.JK", "BBRI.JK", "TLKM.JK", "ASII.JK", "GOTO.JK", "BUMI.JK", "BRMS.JK", "CUAN.JK", "AMMN.JK"]

except Exception as e:
    print(f"❌ Error Alternatif: {e}")
    
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
