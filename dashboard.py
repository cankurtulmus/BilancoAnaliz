import streamlit as st
import borsapy as bp
import requests
from google import genai
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 1. SAYFA VE TASARIM AYARLARI (DARK MODE)
# ==========================================
st.set_page_config(page_title="Bilanço Robotu | Analiz Pro", page_icon="🤖", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #0e0e0e; border-right: 1px solid #333; }
    .stTab, .stMetric, .stMarkdown, .stSubheader, .stTitle, p, h1, h2, h3, li { color: #FFFFFF !important; }
    .stMetricDelta > div { color: #00FF00 !important; }
    button[kind="primary"] { background-color: #1DA1F2 !important; border: none !important; }
    </style>
    """,
    unsafe_allow_html=True
)

API_SIFRESI = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_SIFRESI)

# ==========================================
# AKILLI MELEZ (HYBRID) VERİ ÇEKME MODÜLLERİ
# ==========================================
def yerel_bilanco_cek(sembol):
    """Önce İş Yatırım'ı dener."""
    url = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo"
    donemler = [
        ("2025", "12", "2024", "12"), ("2025", "9", "2024", "9"),
        ("2025", "6", "2024", "6"), ("2025", "3", "2024", "3"),
        ("2024", "12", "2023", "12")
    ]
    
    for tablo_tipi in ["XI_29", "UFRS"]:
        for y1, p1, y2, p2 in donemler:
            params = {
                "companyCode": sembol, "exchange": "TRY", "financialGroup": tablo_tipi,
                "year1": y1, "period1": p1, "year2": y2, "period2": p2
            }
            try:
                # Bot olmadığımızı kanıtlamak için daha gelişmiş bir başlık ekliyoruz
                headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                cevap = requests.get(url, params=params, headers=headers, timeout=5)
                veri = cevap.json().get('value', [])
                if veri:
                    df = pd.DataFrame(veri)[['itemDescTr', 'value1', 'value2']]
                    ceyrek_adi = f"Q{int(p1)//3}"
                    gecmis_ceyrek_adi = f"Q{int(p2)//3}"
                    df.columns = ['Finansal Kalem', f'{y1} {ceyrek_adi}', f'{y2} {gecmis_ceyrek_adi}']
                    df = df[df[f'{y1} {ceyrek_adi}'].notna()].reset_index(drop=True)
                    return df, f"{y1} {ceyrek_adi}", "İş Yatırım (Yerel)"
            except:
                continue
    return pd.DataFrame(), None, None

def yedekli_fiyat_cek(hisse):
    """Fiyatı zorla bulur."""
    try:
        fiyat = hisse.fast_info.get('last_price')
        if fiyat: return fiyat
    except: pass
    try:
        gecmis = hisse.history(period="5d")
        if not gecmis.empty: return gecmis['Close'].iloc[-1]
    except: pass
    return "N/A"

def guvenli_format(deger):
    if isinstance(deger, (int, float)): return f"{deger:.2f}"
    return "-"

# ==========================================
# 2. YAN MENÜ (REKLAM, LOGO VE İMZA)
# ==========================================
with st.sidebar:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.markdown("### 🤖 BİLANÇO ROBOTU")
    
    st.markdown("<p style='text-align: center; font-size: 0.8em;'>Designed by ALbANiAn_Trader ✅</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.title("Arama Motoru")
    hisse_kodu = st.text_input("🔍 Hisse Kodu (Örn: RTALB, THYAO):").upper()
    analiz_butonu = st.button("📊 Analizi Başlat", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.subheader("📢 Beni Takip Et")
    st.markdown(
        """
        <a href="https://x.com/albanian_trader" target="_blank">
            <button style="background-color: #000000; color: white; border: 1px solid #555; padding: 10px; border-radius: 10px; cursor: pointer; width: 100%; font-weight: bold;">
                𝕏 @albanian_trader
            </button>
        </a>
        """, unsafe_allow_html=True
    )

# ==========================================
# 3. ANA EKRAN VE ANALİZ MANTIĞI
# ==========================================
st.title("📈 Bilanço Robotu: Akıllı Finansal Terminal")

if analiz_butonu and hisse_kodu:
    with st.spinner(f"⏳ {hisse_kodu} verileri taranıyor (Melez Motor Devrede)..."):
        try:
            hisse = bp.Ticker(hisse_kodu)
            info = hisse.info
            
            # --- MOTOR 1: İŞ YATIRIM DENEMESİ ---
            guncel_bilanco, bulunan_donem, kaynak = yerel_bilanco_cek(hisse_kodu)
            
            # --- MOTOR 2: GLOBAL YEDEK (İŞ YATIRIM ÇÖKERSE DEVREYE GİRER) ---
            if guncel_bilanco.empty:
                try:
                    df_global = hisse.quarterly_income_stmt
                    if not df_global.empty and len(df_global.columns) >= 2:
                        df_global = df_global.iloc[:, :2].reset_index()
                        col1 = str(df_global.columns[1])[:10]
                        col2 = str(df_global.columns[2])[:10]
                        df_global.columns = ["Finansal Kalem", f"Güncel ({col1})", f"Geçmiş ({col2})"]
                        guncel_bilanco = df_global
                        bulunan_donem = f"Global Son Çeyrek"
                        kaynak = "Borsa Global API"
                except:
                    pass

            # --- ZORLU FİYAT/ÇARPAN VERİLERİ ---
            son_fiyat = yedekli_fiyat_cek(hisse)
            piyasa_degeri = info.get('marketCap') or hisse.fast_info.get('market_cap', "N/A")
            fk_orani = info.get('trailingPE', "N/A")
            pddd_orani = info.get('priceToBook', "N/A")

            # --- ÜST BİLGİ KARTLARI ---
            st.markdown("### 📌 Güncel Piyasa Çarpanları")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Son Fiyat", f"{son_fiyat:.2f} ₺" if isinstance(son_fiyat, (int, float)) else "N/A")
            if isinstance(piyasa_degeri, (int, float)):
                c2.metric("Piyasa Değeri", f"{(piyasa_degeri / 1_000_000_000):.2f} Mrd ₺")
            else:
                c2.metric("Piyasa Değeri", "-")
            c3.metric("F/K Oranı", guvenli_format(fk_orani))
            c4.metric("PD/DD Oranı", guvenli_format(pddd_orani))

            # --- SEKMELER ---
            tab1, tab2, tab3 = st.tabs(["🧠 AI Bilanço Raporu", "📊 Mali Tablolar", "📉 Fiyat Grafiği"])

            with tab1:
                if not guncel_bilanco.empty:
                    st.subheader(f"🤖 Yapay Zeka Raporu: {hisse_kodu}")
                    st.caption(f"Veri Kaynağı: {kaynak} | Dönem: {bulunan_donem}")
                    istek = f"""
                    Sen profesyonel bir borsa analistisin. Sana {hisse_kodu} hissesinin ({kaynak}) kaynaklı ({bulunan_donem}) karşılaştırmalı finansal tablosunu veriyorum.
                    1. Gelir/Satışlardaki durumu yorumla.
                    2. Kârlılık veya Zarar durumunu açıkla.
                    3. 2 tane "Güçlü Yön" ve 2 tane "Risk" çıkar.
                    
                    Finansal Veri:
                    {guncel_bilanco.to_markdown()}
                    """
                    cevap = client.models.generate_content(model='gemini-2.5-flash', contents=istek)
                    st.markdown(cevap.text)
                else:
                    st.error("Bu şirkete ait herhangi bir finansal veri (ne yerel ne global) bulunamadı.")

            with tab2:
                if not guncel_bilanco.empty:
                    st.success(f"Bilanço verisi başarıyla **{kaynak}** üzerinden çekildi.")
                    st.dataframe(guncel_bilanco, use_container_width=True, height=600)
                else:
                    st.warning("Gösterilecek tablo bulunamadı.")

            with tab3:
                gecmis = hisse.history(period="6ay")
                if not gecmis.empty:
                    fig = go.Figure(data=[go.Candlestick(x=gecmis.index, open=gecmis['Open'], high=gecmis['High'], low=gecmis['Low'], close=gecmis['Close'])])
                    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Grafik verisi bulunamadı.")

        except Exception as e:
            st.error(f"Sistemsel bir hata oluştu. Hata Detayı: {e}")
else:
    st.info("👈 Analize başlamak için sol menüden hisse kodunu girin.")