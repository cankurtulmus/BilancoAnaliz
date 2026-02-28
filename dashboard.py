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

def guvenli_al(kaynak, anahtar):
    try:
        return kaynak.get(anahtar, "N/A")
    except:
        return "N/A"

# Sayısal değerleri güvenli formatlama fonksiyonu (HATAYI ÇÖZEN KISIM)
def guvenli_format(deger):
    if isinstance(deger, (int, float)):
        return f"{deger:.2f}"
    return "N/A"

# ==========================================
# 2. YAN MENÜ (REKLAM VE İMZA)
# ==========================================
with st.sidebar:
    try:
        st.image("image_804263.png", use_container_width=True)
    except:
        st.markdown("### ***ALbANiAn_Trader*** ✅")
    
    st.markdown("<p style='text-align: center; font-size: 0.8em;'>Designed by ALbANiAn_Trader</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.title("🤖 Robot Menüsü")
    hisse_kodu = st.text_input("🔍 Hisse Kodu:", placeholder="Örn: ASELS").upper()
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
    st.markdown("---")
    st.caption("🚀 Bilanço Robotu v2.1")

# ==========================================
# 3. ANA EKRAN VE ANALİZ MANTIĞI
# ==========================================
st.title("📈 Bilanço Robotu: Akıllı Finansal Terminal")

if analiz_butonu and hisse_kodu:
    with st.spinner(f"⏳ {hisse_kodu} verileri KAP ve Borsa sistemlerinden çekiliyor..."):
        try:
            hisse = bp.Ticker(hisse_kodu)
            info = hisse.info
            fast_info = hisse.fast_info
            
            # Temel Göstergeler
            son_fiyat = guvenli_al(fast_info, 'last_price')
            piyasa_degeri = guvenli_al(fast_info, 'market_cap')
            fk_orani = guvenli_al(info, 'trailingPE')
            pddd_orani = guvenli_al(info, 'priceToBook')

            # Üst Bilgi Kartları (GÜNCELLENDİ)
            st.markdown("### 📌 Güncel Durum")
            c1, c2, c3, c4 = st.columns(4)
            
            c1.metric("Son Fiyat", f"{son_fiyat} ₺" if son_fiyat != "N/A" else "N/A")
            
            if isinstance(piyasa_degeri, (int, float)):
                c2.metric("Piyasa Değeri", f"{(piyasa_degeri / 1_000_000_000):.2f} Mrd ₺")
            else:
                c2.metric("Piyasa Değeri", "N/A")
                
            c3.metric("F/K Oranı", guvenli_format(fk_orani))
            c4.metric("PD/DD Oranı", guvenli_format(pddd_orani))

            # Finansal Tablolar
            yillik_gelir = hisse.income_stmt.iloc[:, :2]
            ceyrek_gelir = hisse.quarterly_income_stmt.iloc[:, :2]

            tab1, tab2, tab3 = st.tabs(["🧠 AI Bilanço Raporu", "📊 Mali Tablolar", "📉 Grafik"])

            with tab1:
                st.subheader("Gemini 2.5 Pro Analiz Raporu")
                istek = f"""
                Sen kıdemli bir borsa analistisin. {hisse_kodu} hissesi için yıllık ve çeyreklik verileri analiz et.
                ASELSAN gibi dev şirketlerin bakiye siparişleri ve büyüme ivmelerini göz önüne alarak yorum yap.
                Raporu şu başlıklarla hazırla:
                1. Gelir ve Karlılık Analizi
                2. Borçluluk ve Finansal Sağlık
                3. Yatırımcı İçin Güçlü Yönler ve Riskler
                
                Veriler:
                {ceyrek_gelir.to_markdown()}
                """
                cevap = client.models.generate_content(model='gemini-2.5-flash', contents=istek)
                st.markdown(cevap.text)

            with tab2:
                st.dataframe(ceyrek_gelir, use_container_width=True)

            with tab3:
                gecmis = hisse.history(period="6ay")
                if not gecmis.empty:
                    fig = go.Figure(data=[go.Candlestick(x=gecmis.index, open=gecmis['Open'], high=gecmis['High'], low=gecmis['Low'], close=gecmis['Close'])])
                    fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Grafik verisi bulunamadı.")

        except Exception as e:
            st.error(f"Veri çekilirken bir hata oluştu: {e}")
else:
    st.info("👈 Analize başlamak için sol menüden hisse kodunu girin.")