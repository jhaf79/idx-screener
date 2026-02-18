import requests
import pandas as pd
import yfinance as yf
from datetime import datetime

# ======================================
# KONFIGURASI TELEGRAM
# ======================================
CHAT_ID = "8522780166"
BOT_TOKEN = "8251324177:AAHOOY4BECy0WDH3GjW4GjRURaMoKPzuAKo"

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    requests.post(url, data=payload)

# ======================================
# 1️⃣ AMBIL DAFTAR SAHAM DARI IDX
# ======================================
print("📊 Mengambil daftar saham IDX...")
url = "https://www.idx.co.id/umbraco/Surface/ListedCompany/GetCompanyProfiles?emitenType=s"
r = requests.get(url)
data = r.json()

symbols = []
for item in data["data"]:
    code = item["KodeEmiten"]
    symbols.append(code + ".JK")

# ======================================
# 2️⃣ SCREENING HARGA DARI YAHOO FINANCE
# ======================================
print("🔍 Memeriksa harga saham...")
results = []

for symbol in symbols:
    try:
        df = yf.download(symbol, period="5d", interval="1d", progress=False)
        if df.empty:
            continue

        last_close = df["Close"].iloc[-1]
        prev_close = df["Close"].iloc[-2]
        change = ((last_close - prev_close) / prev_close) * 100

        # Filter harga antara 100–1000
        if 100 <= last_close <= 1000:
            # Cek potensi ARA (>20%) atau multibagger (>50% dalam 5 hari)
            five_days_change = ((df["Close"].iloc[-1] - df["Close"].iloc[0]) / df["Close"].iloc[0]) * 100
            if change >= 20 or five_days_change >= 50:
                results.append({
                    "symbol": symbol.replace(".JK", ""),
                    "price": round(last_close, 2),
                    "change": round(change, 2),
                    "5d_change": round(five_days_change, 2)
                })

    except Exception as e:
        print(f"❌ Error {symbol}: {e}")

# ======================================
# 3️⃣ KIRIM KE TELEGRAM
# ======================================
if results:
    df = pd.DataFrame(results).sort_values(by="change", ascending=False).head(15)
    msg = "🔥 <b>15 SAHAM POTENSI ARA / MULTIBAGGER</b>\n"
    msg += f"🕗 {datetime.now().strftime('%d-%m-%Y %H:%M')}\n\n"

    for _, row in df.iterrows():
        msg += f"📈 <b>{row['symbol']}</b>\nHarga: Rp{row['price']:,}\nHarian: {row['change']}%\n5 Hari: {row['5d_change']}%\n\n"

    send_telegram(msg)
    print("✅ Terkirim ke Telegram!")
else:
    send_telegram("⚠️ Tidak ditemukan saham potensi ARA / multibagger hari ini.")
    print("⚠️ Tidak ditemukan saham potensi ARA / multibagger hari ini.")
