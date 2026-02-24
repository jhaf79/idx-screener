import streamlit as st
import yfinance as yf
import pandas as pd
import warnings
from datetime import datetime

warnings.filterwarnings('ignore')

st.set_page_config(
    page_title="IDX Screener Pro",
    layout="wide"
)

st.title("📈 IDX SCREENER PRO")

# ================= WATCHLIST =================

WATCHLIST = [
    "BBCA.JK","BBRI.JK","BMRI.JK","TLKM.JK","ASII.JK",
    "BRPT.JK","AMMN.JK","BREN.JK","GOTO.JK","CPIN.JK",
    "ICBP.JK","ADRO.JK","ANTM.JK","MDKA.JK","UNTR.JK",
    "PGAS.JK","INDF.JK","KLBF.JK","SMGR.JK","UNVR.JK",
    "ARTO.JK","DCII.JK","CUAN.JK","BYAN.JK","TPIA.JK"
]

# ================= DOWNLOAD =================

@st.cache_data(ttl=300)
def get_data():

    df = yf.download(

        WATCHLIST,

        period="100d",

        group_by='ticker',

        threads=True,

        progress=False

    )

    return df


# ================= FORMAT =================

def format_table(data):

    df = pd.DataFrame(

        data,

        columns=["Ticker","Price","Score","Value"]

    )

    df = df.sort_values(

        "Score",

        ascending=False

    )

    return df


# ================= ANALYSIS =================

def analyze_all(df_all):

    bsjp, dt, sc = [], [], []

    for ticker in WATCHLIST:

        try:

            data = df_all[ticker].dropna()

            if len(data) < 25:
                continue

            last = data.iloc[-1]
            prev = data.iloc[-2]

            c = last['Close']
            o = last['Open']
            h = last['High']
            l = last['Low']
            vol = last['Volume']

            value = (c*vol)/1000000000

            ma5 = data['Close'].rolling(5).mean().iloc[-1]
            ma20 = data['Close'].rolling(20).mean().iloc[-1]

            volma = data['Volume'].rolling(20).mean().iloc[-1]


            # BSJP

            score=0

            if c>o: score+=20
            if c>=h*0.99: score+=50
            if vol>volma*1.5: score+=30

            if score>=80:

                bsjp.append([ticker,c,score,value])


            # DAYTRADE

            score=0

            change=(c-prev['Close'])/prev['Close']

            if ma5>ma20: score+=30
            if change>0.03: score+=30
            if vol>volma*2: score+=40

            if score>=70:

                dt.append([ticker,c,score,value])


            # SCALPER

            score=0

            range=(h-l)/l

            if range>0.05: score+=40
            if vol>volma*3: score+=60

            if score>=100:

                sc.append([ticker,c,score,value])


        except:
            pass


    return bsjp, dt, sc


# ================= BUTTON =================

if st.button("SCAN SEKARANG"):

    with st.spinner("Scanning IDX..."):

        data=get_data()

        bsjp,dt,sc=analyze_all(data)


        st.subheader("BSJP")

        st.dataframe(format_table(bsjp))


        st.subheader("DAYTRADE")

        st.dataframe(format_table(dt))


        st.subheader("SCALPER")

        st.dataframe(format_table(sc))


st.caption(f"Update : {datetime.now()}")
