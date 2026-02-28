import streamlit as st
import borsapy as bp
from google import genai
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 1. SAYFA VE TASARIM AYARLARI (DARK MODE)
# ==========================================
st.set_page_config(page_title="Bilanço Robotu | Analiz Pro", page_icon="🚀", layout="wide")

st.markdown(
    """
    <style>
    .stApp {
        background-color: #000000;
        color: #FFFFFF;
    }
    [data-testid="stSidebar"] {
        background-color: #0e0e0e;
        border-right: 1px solid #333;
    }
    .stTab, .stMetric, .stMarkdown, .stSubheader, .stTitle, p, h1, h2, h3, li {
        color: #FFFFFF !important;
    }
    .stMetricDelta > div {
        color: #00FF00 !important;
    }
    button[kind="primary"] {
        background-color: #1DA1F2 !important;
        border: none !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

API_SIFRESI = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_SIFRESI)

# ==========================================
# AKILLI VERİ ÇEKME MODÜLLERİ (N/A ÇÖZÜCÜ)
# ==========================================
def yedekli_fiyat_cek(hisse):
    """Fiyatı bulana kadar tüm kapıları zorlar."""
    try:
        # 1. Deneme: Anlık veri
        fiyat = hisse.fast_info.get('last_price')
        if fiyat: return fiyat
    except:
        pass
    
    try:
        # 2. Deneme: Standart Info
        fiyat = hisse.info.get('currentPrice')
        if fiyat: return fiyat
    except:
        pass
        
    try:
        # 3. Deneme: Grafik geçmişinden son kapanışı zorla alma
        gecmis = hisse.history(period="5d")
        if not gecmis.empty:
            return gecmis['Close'].iloc[-1]
    except:
        pass
        
    return "N/A"

def guvenli_format(deger):
    """Rakam gelmezse çökmesini engeller."""
    if isinstance(deger, (int, float)):
        return f"{deger:.2f}"
    return "-"

# ==========================================
# 2. YAN MENÜ (REKLAM VE İMZA)
# ==========================================
with st.sidebar:
    try:
        st.image("logo.png", use_container_width=True) # Logon varsa buraya koy
    except:
        st.markdown("### ***ALbANiAn_Trader*** ✅")
    
    st.markdown("<p style='text-align: center; font-size: 0.8em;'>Designed by ALbANiAn_Trader</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.title("🤖 Robot Menüsü")
    hisse_kodu = st.text_input("🔍 Hisse Kodu:", placeholder="Örn: RTALB, ASELS").upper()
    analiz_butonu = st.button("📊 Analizi Başlat", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.subheader("📢 Takip Et")
    st.markdown(
        f"""
        <a href="https://x.com/albanian_trader" target="_blank">
            <button style="
                background-color: #000000; 
                color: white; 
                border: 1px solid #555; 
                padding: 10px; 
                border-radius: 10px; 
                cursor: pointer; 
                width: 100%;
                font-weight: bold;
            ">
                𝕏 @albanian_trader'ı Takip Et
            </button>
        </a>
        """,
        unsafe_allow_html=True
    )

# ==========================================
# 3. ANA EKRAN VE ANALİZ MANTIĞI
# ==========================================
st.title("📈 Bilanço Robotu: Akıllı Finansal Terminal")

if analiz_butonu and hisse_kodu:
    with st.spinner(f"⏳ {hisse_kodu} verileri çekiliyor (Yedekli Sistem Aktif)..."):
        try:
            hisse = bp.Ticker(hisse_kodu)
            info = hisse.info
            
            # --- ZORLU VERİLERİ ÇEKME ---
            son_fiyat = yedekli_fiyat_cek(hisse)
            piyasa_degeri = info.get('marketCap') or hisse.fast_info.get('market_cap', "N/A")
            fk_orani = info.get('trailingPE', "N/A")
            pddd_orani = info.get('priceToBook', "N/A")

            # --- ÜST BİLGİ KARTLARI ---
            st.markdown("### 📌 Güncel Durum")
            c1, c2, c3, c4 = st.columns(4)
            
            c1.metric("Son Fiyat", f"{son_fiyat:.2f} ₺" if isinstance(son_fiyat, (int, float)) else "N/A")
            
            if isinstance(piyasa_degeri, (int, float)):
                c2.metric("Piyasa Değeri", f"{(piyasa_degeri / 1_000_000_000):.2f} Mrd ₺")
            else:
                c2.metric("Piyasa Değeri", "-")
                
            c3.metric("F/K Oranı", guvenli_format(fk_orani))
            c4.metric("PD/DD Oranı", guvenli_format(pddd_orani))

            # --- FİNANSAL TABLOLAR ---
            ceyrek_gelir = hisse.quarterly_income_stmt.iloc[:, :2]

            tab1, tab2, tab3 = st.tabs(["🧠 AI Bilanço Raporu", "📊 Mali Tablolar", "📉 Grafik"])

            with tab1:
                st.subheader("Gemini 2.5 Pro Analiz Raporu")
                istek = f"""
                Sen kıdemli bir borsa analistisin. {hisse_kodu} hissesi için verileri analiz et.
                Aşağıdaki çeyreklik gelir tablosuna bakarak gelir ve kârlılık büyümesini yorumla.
                Eğer veri eksikse veya şirket zarar etmişse (F/K yoksa) bunu yatırımcıya net bir dille risk olarak belirt.
                
                Veriler:
                {ceyrek_gelir.to_markdown()}
                """
                cevap = client.models.generate_content(model='gemini-2.5-flash', contents=istek)
                st.markdown(cevap.text)

            with tab2:
                if not ceyrek_gelir.empty:
                    st.dataframe(ceyrek_gelir, use_container_width=True)
                else:
                    st.warning("Bu hisse için güncel çeyreklik gelir tablosu global API'ye henüz yansımamış.")

            with tab3:
                gecmis = hisse.history(period="6ay")
                if not gecmis.empty:
                    fig = go.Figure(data=[go.Candlestick(x=gecmis.index, open=gecmis['Open'], high=gecmis['High'], low=gecmis['Low'], close=gecmis['Close'])])
                    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Grafik verisi bulunamadı.")

        except Exception as e:
            st.error(f"Sistemsel bir hata oluştu. Hisse kodunu doğru girdiğinizden emin olun. Hata Detayı: {e}")
else:
    st.info("👈 Analize başlamak için sol menüden hisse kodunu girin.")