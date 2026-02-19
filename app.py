import requests
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
from datetime import datetime
import streamlit as st
import numpy as np
import time

# ==========================================
# CONFIG & TELEGRAM
# ==========================================
try:
    BOT_TOKEN = st.secrets["BOT_TOKEN"]
    CHAT_ID = st.secrets["CHAT_ID"]
except:
    st.error("Gagal memuat Secrets. Pastikan BOT_TOKEN & CHAT_ID sudah diisi.")

def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "HTML"}
    try: requests.post(url, data=payload)
    except: pass

def send_chart(image_path):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendPhoto"
    try:
        with open(image_path, "rb") as img:
            requests.post(url, data={"chat_id": CHAT_ID}, files={"photo": img})
    except: pass

# ==========================================
# FUNCTIONS
# ==========================================

def get_ara_limit(price):
    if price <= 200: return 34.0
    elif price <= 5000: return 24.0
    else: return 19.0

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def generate_chart(symbol, df):
    plt.figure(figsize=(8,4))
    plt.plot(df['Close'], label="Price", color='green')
    plt.plot(df['Close'].rolling(20).mean(), label="MA20", color='red')
    plt.title(f"Momentum: {symbol}")
    plt.legend()
    file_name = f"{symbol}_agg.png"
    plt.savefig(file_name)
    plt.close()
    return file_name

# ==========================================
# AGGRESSIVE SCANNER ENGINE
# ==========================================

def run_aggressive_scanner(symbols_list):
    results = []
    st.write(f"⚡ Memindai {len(symbols_list)} saham (Mode Agresif)...")
    
    # Download masal
    all_data = yf.download(
        tickers=symbols_list,
        period="3mo",
        interval="1d",
        group_by="column",
        threads=True,
        progress=False
    )

    for symbol in symbols_list:
        try:
            df = pd.DataFrame({
                'High': all_data['High'][symbol],
                'Low': all_data['Low'][symbol],
                'Close': all_data['Close'][symbol],
                'Volume': all_data['Volume'][symbol]
            }).dropna()

            if len(df) < 15: continue

            last = df['Close'].iloc[-1]
            prev = df['Close'].iloc[-2]
            
            # --- FILTER AGGRESIF ---
            # 1. Likuiditas: Min 500 Juta
            turnover = last * df['Volume'].iloc[-1]
            if turnover < 500_000_000: continue 

            # 2. Volume Spike: Min 2.0x (Lebih longgar)
            vol_spike = df['Volume'].iloc[-1] / df['Volume'].iloc[-6:-1].mean()
            if vol_spike < 2.0: continue

            # 3. Price Change & ARA Limit
            change = ((last - prev) / prev) * 100
            limit_ara = get_ara_limit(prev)
            
            # 4. Breakout 5 Hari (Short-term momentum)
            is_breakout = last >= df['High'].iloc[-6:-1].max()
            
            # Syarat: Kenaikan > 4% DAN (Breakout ATAU Mendekati ARA)
            if change >= 4.0 and (is_breakout or change >= (limit_ara - 5)):
                
                rsi = calculate_rsi(df['Close']).iloc[-1]
                
                results.append({
                    "symbol": symbol.replace(".JK",""),
                    "price": last,
                    "change": change,
                    "vol": vol_spike,
                    "turnover": f"{turnover/1e6:.0f}M",
                    "rsi": rsi,
                    "df_full": df
                })
        except:
            continue

    return sorted(results, key=lambda x: x["change"], reverse=True)[:10]

# ==========================================
# STREAMLIT UI
# ==========================================

st.set_page_config(page_title="Aggressive Scanner", layout="wide")
st.title("⚡ IDX Aggressive Momentum Scanner")

# Masukkan daftar simbol Anda di sini
my_symbols = [

    "AADI.JK", "AALI.JK", "ABBA.JK", "ABDA.JK", "ABMM.JK", "ACES.JK", "ACRO.JK", "ACST.JK",

    "ADCP.JK", "ADES.JK", "ADHI.JK", "ADMF.JK", "ADMG.JK", "ADMR.JK", "ADRO.JK", "AEGS.JK",

    "AGAR.JK", "AGII.JK", "AGRO.JK", "AGRS.JK", "AHAP.JK", "AIMS.JK", "AISA.JK", "AKKU.JK",

    "AKPI.JK", "AKRA.JK", "AKSI.JK", "ALDO.JK", "ALII.JK", "ALKA.JK", "ALMI.JK", "ALTO.JK",

    "AMAG.JK", "AMAN.JK", "AMAR.JK", "AMFG.JK", "AMIN.JK", "AMMN.JK", "AMMS.JK", "AMOR.JK",

    "AMRT.JK", "ANDI.JK", "ANJT.JK", "ANTM.JK", "APEX.JK", "APIC.JK", "APII.JK", "APLI.JK",

    "APLN.JK", "ARCI.JK", "AREA.JK", "ARGO.JK", "ARII.JK", "ARKA.JK", "ARKO.JK", "ARMY.JK",

    "ARNA.JK", "ARTA.JK", "ARTI.JK", "ARTO.JK", "ASBI.JK", "ASDM.JK", "ASGR.JK", "ASHA.JK",

    "ASII.JK", "ASJT.JK", "ASLC.JK", "ASLI.JK", "ASMI.JK", "ASPI.JK", "ASPR.JK", "ASRI.JK",

    "ASRM.JK", "ASSA.JK", "ATAP.JK", "ATIC.JK", "ATLA.JK", "AUTO.JK", "AVIA.JK", "AWAN.JK",

    "AXIO.JK", "AYAM.JK", "AYLS.JK", "BABP.JK", "BABY.JK", "BACA.JK", "BAIK.JK", "BAJA.JK",

    "BALI.JK", "BANK.JK", "BAPA.JK", "BAPI.JK", "BATA.JK", "BATR.JK", "BAUT.JK", "BAYU.JK",

    "BBCA.JK", "BBHI.JK", "BBKP.JK", "BBLD.JK", "BBMD.JK", "BBNI.JK", "BBRI.JK", "BBRM.JK",

    "BBSI.JK", "BBSS.JK", "BBTN.JK", "BBYB.JK", "BCAP.JK", "BCIC.JK", "BCIP.JK", "BDKR.JK",

    "BDMN.JK", "BEBS.JK", "BEEF.JK", "BEER.JK", "BEKS.JK", "BELI.JK", "BELL.JK", "BESS.JK",

    "BEST.JK", "BFIN.JK", "BGTG.JK", "BHAT.JK", "BHIT.JK", "BIKA.JK", "BIKE.JK", "BIMA.JK",

    "BINA.JK", "BINO.JK", "BIPI.JK", "BIPP.JK", "BIRD.JK", "BISI.JK", "BJBR.JK", "BJTM.JK",

    "BKDP.JK", "BKSL.JK", "BKSW.JK", "BLES.JK", "BLOG.JK", "BLTA.JK", "BLTZ.JK", "BLUE.JK",

    "BMAS.JK", "BMBL.JK", "BMHS.JK", "BMRI.JK", "BMSR.JK", "BMTR.JK", "BNBA.JK", "BNBR.JK",

    "BNGA.JK", "BNII.JK", "BNLI.JK", "BOAT.JK", "BOBA.JK", "BOGA.JK", "BOLA.JK", "BOLT.JK",

    "BOSS.JK", "BPFI.JK", "BPII.JK", "BPTR.JK", "BRAM.JK", "BREN.JK", "BRIS.JK", "BRMS.JK",

    "BRNA.JK", "BRPT.JK", "BRRC.JK", "BSBK.JK", "BSDE.JK", "BSIM.JK", "BSML.JK", "BSSR.JK",

    "BSWD.JK", "BTEK.JK", "BTEL.JK", "BTON.JK", "BTPN.JK", "BTPS.JK", "BUAH.JK", "BUDI.JK",

    "BUKA.JK", "BUKK.JK", "BULL.JK", "BUMI.JK", "BUVA.JK", "BVIC.JK", "BWPT.JK", "BYAN.JK",

    "CAKK.JK", "CAMP.JK", "CANI.JK", "CARE.JK", "CARS.JK", "CASA.JK", "CASH.JK", "CASS.JK",

    "CBDK.JK", "CBMF.JK", "CBPE.JK", "CBRE.JK", "CBUT.JK", "CCSI.JK", "CDIA.JK", "CEKA.JK",

    "CENT.JK", "CFIN.JK", "CGAS.JK", "CHEK.JK", "CHEM.JK", "CHIP.JK", "CINT.JK", "CITA.JK",

    "CITY.JK", "CLAY.JK", "CLEO.JK", "CLPI.JK", "CMNP.JK", "CMNT.JK", "CMPP.JK", "CMRY.JK",

    "CNKO.JK", "CNMA.JK", "CNTB.JK", "CNTX.JK", "COAL.JK", "COCO.JK", "COIN.JK", "COWL.JK",

    "CPIN.JK", "CPRI.JK", "CPRO.JK", "CRAB.JK", "CRSN.JK", "CSAP.JK", "CSIS.JK", "CSMI.JK",

    "CSRA.JK", "CTBN.JK", "CTRA.JK", "CTTH.JK", "CUAN.JK", "CYBR.JK", "DAAZ.JK", "DADA.JK",

    "DART.JK", "DATA.JK", "DAYA.JK", "DCII.JK", "DEAL.JK", "DEFI.JK", "DEPO.JK", "DEWA.JK",

    "DEWI.JK", "DFAM.JK", "DGIK.JK", "DGNS.JK", "DGWG.JK", "DIGI.JK", "DILD.JK", "DIVA.JK",

    "DKFT.JK", "DKHH.JK", "DLTA.JK", "DMAS.JK", "DMMX.JK", "DMND.JK", "DNAR.JK", "DNET.JK",

    "DOID.JK", "DOOH.JK", "DOSS.JK", "DPNS.JK", "DPUM.JK", "DRMA.JK", "DSFI.JK", "DSNG.JK",

    "DSSA.JK", "DUCK.JK", "DUTI.JK", "DVLA.JK", "DWGL.JK", "DYAN.JK", "EAST.JK", "ECII.JK",

    "EDGE.JK", "EKAD.JK", "ELIT.JK", "ELPI.JK", "ELSA.JK", "ELTY.JK", "EMAS.JK", "EMDE.JK",

    "EMTK.JK", "ENAK.JK", "ENRG.JK", "ENVY.JK", "ENZO.JK", "EPAC.JK", "EPMT.JK", "ERAA.JK",

    "ERAL.JK", "ERTX.JK", "ESIP.JK", "ESSA.JK", "ESTA.JK", "ESTI.JK", "ETWA.JK", "EURO.JK",

    "EXCL.JK", "FAPA.JK", "FAST.JK", "FASW.JK", "FILM.JK", "FIMP.JK", "FIRE.JK", "FISH.JK",

    "FITT.JK", "FLMC.JK", "FMII.JK", "FOLK.JK", "FOOD.JK", "FORE.JK", "FORU.JK", "FPNI.JK",

    "ZONE.JK", "FUJI.JK", "FUTR.JK", "FWCT.JK", "GAMA.JK", "GDST.JK", "GDYR.JK", "GEMA.JK",

    "GEMS.JK", "GGRM.JK", "GGRP.JK", "GHON.JK", "GIAA.JK", "GJTL.JK", "GLOB.JK", "GLVA.JK",

    "GMFI.JK", "GMTD.JK", "GOLD.JK", "GOLF.JK", "GOLL.JK", "GOOD.JK", "GOTO.JK", "ZYRX.JK",

    "GPRA.JK", "GPSO.JK", "GRIA.JK", "GRPH.JK", "GRPM.JK", "GSMF.JK", "GTBO.JK", "GTRA.JK",

    "GTSI.JK", "GULA.JK", "GUNA.JK", "GWSA.JK", "GZCO.JK", "HADE.JK", "HAIS.JK", "HAJJ.JK",

    "HALO.JK", "HATM.JK", "HBAT.JK", "HDFA.JK", "HDIT.JK", "HEAL.JK", "HELI.JK", "HERO.JK",

    "HEXA.JK", "HGII.JK", "HILL.JK", "HITS.JK", "HKMU.JK", "HMSP.JK", "HOKI.JK", "HOME.JK",

    "HOMI.JK", "HOPE.JK", "HOTL.JK", "HRME.JK", "HRTA.JK", "HRUM.JK", "HUMI.JK", "HYGN.JK",

    "IATA.JK", "IBFN.JK", "IBOS.JK", "IBST.JK", "ICBP.JK", "ICON.JK", "IDEA.JK", "IDPR.JK",

    "IFII.JK", "IFSH.JK", "IGAR.JK", "IIKP.JK", "IKAI.JK", "IKAN.JK", "IKBI.JK", "IKPM.JK",

    "IMAS.JK", "IMJS.JK", "IMPC.JK", "INAF.JK", "INAI.JK", "INCF.JK", "INCI.JK", "INCO.JK",

    "INDF.JK", "INDO.JK", "INDR.JK", "INDS.JK", "INDX.JK", "INDY.JK", "INET.JK", "INKP.JK",

    "INOV.JK", "INPC.JK", "INPP.JK", "INPS.JK", "INRU.JK", "INTA.JK", "INTD.JK", "INTP.JK",

    "IOTF.JK", "IPAC.JK", "IPCC.JK", "IPCM.JK", "IPOL.JK", "IPPE.JK", "IPTV.JK", "IRRA.JK",

    "IRSX.JK", "ISAP.JK", "ISAT.JK", "ISEA.JK", "ISSP.JK", "ITIC.JK", "ITMA.JK", "ITMG.JK",

    "JARR.JK", "JAST.JK", "JATI.JK", "JAWA.JK", "JAYA.JK", "JECC.JK", "JGLE.JK", "JIHD.JK",

    "JKON.JK", "JMAS.JK", "JPFA.JK", "JRPT.JK", "JSKY.JK", "JSMR.JK", "JSPT.JK", "JTPE.JK",

    "KAEF.JK", "KAQI.JK", "KARW.JK", "KAYU.JK", "KBAG.JK", "KBLI.JK", "KBLM.JK", "KBLV.JK",

    "KBRI.JK", "KDSI.JK", "KDTN.JK", "KEEN.JK", "KEJU.JK", "KETR.JK", "KIAS.JK", "KICI.JK",

    "KIJA.JK", "KING.JK", "KINO.JK", "KIOS.JK", "KJEN.JK", "KKES.JK", "KKGI.JK", "KLAS.JK",

    "KLBF.JK", "KLIN.JK", "KMDS.JK", "KMTR.JK", "KOBX.JK", "KOCI.JK", "KOIN.JK", "KOKA.JK",

    "KONI.JK", "KOPI.JK", "KOTA.JK", "KPIG.JK", "KRAS.JK", "KREN.JK", "KRYA.JK", "KSIX.JK",

    "KUAS.JK", "LABA.JK", "LABS.JK", "LAJU.JK", "LAND.JK", "LAPD.JK", "LCGP.JK", "LCKM.JK",

    "LEAD.JK", "LFLO.JK", "LIFE.JK", "LINK.JK", "LION.JK", "LIVE.JK", "LMAS.JK", "LMAX.JK",

    "LMPI.JK", "LMSH.JK", "LOPI.JK", "LPCK.JK", "LPGI.JK", "LPIN.JK", "LPKR.JK", "LPLI.JK",

    "LPPF.JK", "LPPS.JK", "LRNA.JK", "LSIP.JK", "LTLS.JK", "LUCK.JK", "LUCY.JK", "MABA.JK",

    "MAGP.JK", "MAHA.JK", "MAIN.JK", "MANG.JK", "MAPA.JK", "MAPB.JK", "MAPI.JK", "MARI.JK",

    "MARK.JK", "MASB.JK", "MAXI.JK", "MAYA.JK", "MBAP.JK", "MBMA.JK", "MBSS.JK", "MBTO.JK",

    "MCAS.JK", "MCOL.JK", "MCOR.JK", "MDIA.JK", "MDIY.JK", "MDKA.JK", "MDKI.JK", "MDLA.JK",

    "MDLN.JK", "MDRN.JK", "MEDC.JK", "MEDS.JK", "MEGA.JK", "MEJA.JK", "MENN.JK", "MERI.JK",

    "MERK.JK", "META.JK", "MFMI.JK", "MGLV.JK", "MGNA.JK", "MGRO.JK", "MHKI.JK", "MICE.JK",

    "MIDI.JK", "MIKA.JK", "MINA.JK", "MINE.JK", "MIRA.JK", "MITI.JK", "MKAP.JK", "MKNT.JK",

    "MKPI.JK", "MKTR.JK", "MLBI.JK", "MLIA.JK", "MLPL.JK", "MLPT.JK", "MMIX.JK", "MMLP.JK",

    "MNCN.JK", "MOLI.JK", "MORA.JK", "MPIX.JK", "MPMX.JK", "MPOW.JK", "MPPA.JK", "MPRO.JK",

    "MPXL.JK", "MRAT.JK", "MREI.JK", "MSIE.JK", "MSIN.JK", "MSJA.JK", "MSKY.JK", "MSTI.JK",

    "MTDL.JK", "MTEL.JK", "MTFN.JK", "MTLA.JK", "MTMH.JK", "MTPS.JK", "MTRA.JK", "MTSM.JK",

    "MTWI.JK", "MUTU.JK", "MYOH.JK", "MYOR.JK", "MYTX.JK", "NAIK.JK", "NANO.JK", "NASA.JK",

    "NASI.JK", "NATO.JK", "NAYZ.JK", "NCKL.JK", "NELY.JK", "NEST.JK", "NETV.JK", "NFCX.JK",

    "NICE.JK", "NICK.JK", "NICL.JK", "NIKL.JK", "NINE.JK", "NIRO.JK", "NISP.JK", "NOBU.JK",

    "NPGF.JK", "NRCA.JK", "NSSS.JK", "NTBK.JK", "NUSA.JK", "NZIA.JK", "OASA.JK", "OBAT.JK",

    "OBMD.JK", "OCAP.JK", "OILS.JK", "OKAS.JK", "OLIV.JK", "OMED.JK", "OMRE.JK", "OPMS.JK",

    "PACK.JK", "PADA.JK", "PADI.JK", "PALM.JK", "PAMG.JK", "PANI.JK", "PANR.JK", "PANS.JK",

    "PART.JK", "PBID.JK", "PBRX.JK", "PBSA.JK", "PCAR.JK", "PDES.JK", "PDPP.JK", "PEGE.JK",

    "PEHA.JK", "PEVE.JK", "PGAS.JK", "PGEO.JK", "PGJO.JK", "PGLI.JK", "PGUN.JK", "PICO.JK",

    "PIPA.JK", "PJAA.JK", "PJHB.JK", "PKPK.JK", "PLAN.JK", "PLAS.JK", "PLIN.JK", "PMJS.JK",

    "PMMP.JK", "PMUI.JK", "PNBN.JK", "PNBS.JK", "PNGO.JK", "PNIN.JK", "PNLF.JK", "PNSE.JK",

    "POLA.JK", "POLI.JK", "POLL.JK", "POLU.JK", "POLY.JK", "POOL.JK", "PORT.JK", "POSA.JK",

    "POWR.JK", "PPGL.JK", "PPRE.JK", "PPRI.JK", "PPRO.JK", "PRAY.JK", "PRDA.JK", "PRIM.JK",

    "PSAB.JK", "PSAT.JK", "PSDN.JK", "PSGO.JK", "PSKT.JK", "PSSI.JK", "PTBA.JK", "PTDU.JK",

    "PTIS.JK", "PTMP.JK", "PTMR.JK", "PTPP.JK", "PTPS.JK", "PTPW.JK", "PTRO.JK", "PTSN.JK",

    "PTSP.JK", "PUDP.JK", "PURA.JK", "PURE.JK", "PURI.JK", "PWON.JK", "PYFA.JK", "PZZA.JK",

    "RAAM.JK", "RAFI.JK", "RAJA.JK", "RALS.JK", "RANC.JK", "RATU.JK", "RBMS.JK", "RCCC.JK",

    "RDTX.JK", "REAL.JK", "RELF.JK", "RELI.JK", "RGAS.JK", "RICY.JK", "RIGS.JK", "RIMO.JK",

    "RISE.JK", "RLCO.JK", "RMKE.JK", "RMKO.JK", "ROCK.JK", "RODA.JK", "RONY.JK", "ROTI.JK",

    "RSCH.JK", "RSGK.JK", "RUIS.JK", "RUNS.JK", "SAFE.JK", "SAGE.JK", "SAME.JK", "SAMF.JK",

    "SAPX.JK", "SATU.JK", "SBAT.JK", "SBMA.JK", "SCCO.JK", "SCMA.JK", "SCNP.JK", "SCPI.JK",

    "SDMU.JK", "SDPC.JK", "SDRA.JK", "SEMA.JK", "SFAN.JK", "SGER.JK", "SGRO.JK", "SHID.JK",

    "SHIP.JK", "SICO.JK", "SIDO.JK", "SILO.JK", "SIMA.JK", "SIMP.JK", "SINI.JK", "SIPD.JK",

    "SKBM.JK", "SKLT.JK", "SKRN.JK", "SKYB.JK", "SLIS.JK", "SMAR.JK", "SMBR.JK", "SMCB.JK",

    "SMDM.JK", "SMDR.JK", "SMGA.JK", "SMGR.JK", "SMIL.JK", "SMKL.JK", "SMKM.JK", "SMLE.JK",

    "SMMA.JK", "SMMT.JK", "SMRA.JK", "SMRU.JK", "SMSM.JK", "SNLK.JK", "SOCI.JK", "SOFA.JK",

    "SOHO.JK", "SOLA.JK", "SONA.JK", "SOSS.JK", "SOTS.JK", "SOUL.JK", "SPMA.JK", "SPRE.JK",

    "SPTO.JK", "SQMI.JK", "SRAJ.JK", "SRIL.JK", "SRSN.JK", "SRTG.JK", "SSIA.JK", "SSMS.JK",

    "SSTM.JK", "STAA.JK", "STAR.JK", "STRK.JK", "STTP.JK", "SUGI.JK", "SULI.JK", "SUNI.JK",

    "SUPA.JK", "SUPR.JK", "SURE.JK", "SURI.JK", "SWAT.JK", "SWID.JK", "TALF.JK", "TAMA.JK",

    "TAMU.JK", "TAPG.JK", "TARA.JK", "TAXI.JK", "TAYS.JK", "TBIG.JK", "TBLA.JK", "TBMS.JK",

    "TCID.JK", "TCPI.JK", "TDPM.JK", "TEBE.JK", "TECH.JK", "TELE.JK", "TFAS.JK", "TFCO.JK",

    "TGKA.JK", "TGRA.JK", "TGUK.JK", "TIFA.JK", "TINS.JK", "TIRA.JK", "TIRT.JK", "TKIM.JK",

    "TLDN.JK", "TLKM.JK", "TMAS.JK", "TMPO.JK", "TNCA.JK", "TOBA.JK", "TOOL.JK", "TOPS.JK",

    "TOSK.JK", "TOTL.JK", "TOTO.JK", "TOWR.JK", "TOYS.JK", "TPMA.JK", "TRAM.JK", "TRGU.JK",

    "TRIL.JK", "TRIM.JK", "TRIN.JK", "TRIO.JK", "TRIS.JK", "TRJA.JK", "TRON.JK", "TRST.JK",

    "TRUE.JK", "TRUK.JK", "TRUS.JK", "TSPC.JK", "TUGU.JK", "TYRE.JK", "UANG.JK", "UCID.JK",

    "UDNG.JK", "UFOE.JK", "ULTJ.JK", "UNIC.JK", "UNIQ.JK", "UNIT.JK", "UNSP.JK", "UNTD.JK",

    "UNTR.JK", "UNVR.JK", "URBN.JK", "UVCR.JK", "VAST.JK", "VERN.JK", "VICI.JK", "VICO.JK",

    "VINS.JK", "VISI.JK", "VIVA.JK", "VKTR.JK", "VOKS.JK", "VRNA.JK", "VTNY.JK", "WAPO.JK",

    "WEGE.JK", "WEHA.JK", "WGSH.JK", "WICO.JK", "WIDI.JK", "WIFI.JK", "WIIM.JK", "WIKA.JK",

    "WINE.JK", "WINR.JK", "WINS.JK", "WIRG.JK", "WMPP.JK", "WMUU.JK", "WOMF.JK", "WOOD.JK",

    "WOWS.JK", "WSBP.JK", "WSKT.JK", "WTON.JK", "YELO.JK", "YOII.JK", "YPAS.JK", "YULE.JK",

    "YUPI.JK", "ZATA.JK", "ZBRA.JK", "ZINC.JK"

]

if st.button("🚀 Start Aggressive Scan"):
    res = run_aggressive_scanner(my_symbols)
    
    if res:
        st.success(f"Ditemukan {len(res)} saham momentum!")
        df_display = pd.DataFrame(res).drop(columns=['df_full'])
        st.table(df_display)
        
        # Kirim Alert
        waktu = datetime.now().strftime('%H:%M:%S')
        msg = f"⚡ <b>AGGRESSIVE MOMENTUM</b>\n⏰ {waktu}\n\n"
        for r in res:
            msg += f"<b>{r['symbol']}</b> | {r['change']:+.2f}%\n"
            msg += f"Vol: {r['vol']:.1f}x | Val: {r['turnover']}\n\n"
        
        send_telegram(msg)
        for r in res:
            img = generate_chart(r["symbol"], r["df_full"])
            send_chart(img)
    else:
        st.info("Market sedang sepi. Tidak ada saham momentum agresif.")

