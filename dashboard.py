import streamlit as st
import borsapy as bp
import requests
from google import genai
import pandas as pd
import plotly.graph_objects as go
import xml.etree.ElementTree as ET
from datetime import datetime

# ==========================================
# 1. SAYFA VE TASARIM AYARLARI (DARK MODE)
# ==========================================
st.set_page_config(page_title="Bilanço Robotu | VIP Terminal", page_icon="🤖", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background-color: #000000; color: #FFFFFF; }
    [data-testid="stSidebar"] { background-color: #0A0A0A; border-right: 1px solid #1c1c1c; }
    .stTab, .stMetric, .stMarkdown, .stSubheader, .stTitle, p, h1, h2, h3, li { color: #FFFFFF !important; }
    .stMetricDelta > div { color: #00FF00 !important; }
    button[kind="primary"] { background-color: #1DA1F2 !important; border: none !important; border-radius: 8px !important; }
    strong { color: #1DA1F2 !important; } 
    
    .sidebar-title { text-align: center; font-size: 26px; font-weight: 900; color: #1DA1F2; margin-bottom: 5px; letter-spacing: 1px; }
    .sidebar-subtitle { text-align: center; font-size: 14px; color: #888; margin-bottom: 25px; }
    .x-button { background-color: #000000; color: #1DA1F2; border: 1px solid #1DA1F2; padding: 10px; border-radius: 8px; text-align: center; font-weight: bold; transition: all 0.3s ease; }
    .x-button:hover { background-color: #1DA1F2; color: #ffffff; }
    
    /* En Üstteki Devasa Şirket ve Dönem Başlığı İçin */
    .terminal-header { text-align: center; color: #1DA1F2; font-size: 32px; font-weight: 900; border-bottom: 2px solid #1DA1F2; padding-bottom: 15px; margin-top: 10px; margin-bottom: 20px; }
    </style>
    """,
    unsafe_allow_html=True
)

API_SIFRESI = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_SIFRESI)

# ==========================================
# AKILLI ÇİFT KADEMELİ MOTORLAR
# ==========================================
def yerel_bilanco_cek(sembol):
    url = "https://www.isyatirim.com.tr/_layouts/15/IsYatirim.Website/Common/Data.aspx/MaliTablo"
    donemler = [
        ("2025", "12", "2024", "12"), ("2025", "9", "2024", "9"),
        ("2025", "6", "2024", "6"), ("2025", "3", "2024", "3"),
        ("2024", "12", "2023", "12")
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
        'Accept': 'application/json, text/javascript, */*; q=0.01'
    }

    for tablo_tipi in ["XI_29", "UFRS"]:
        for y1, p1, y2, p2 in donemler:
            params = {"companyCode": sembol, "exchange": "TRY", "financialGroup": tablo_tipi, "year1": y1, "period1": p1, "year2": y2, "period2": p2}
            try:
                cevap = requests.get(url, params=params, headers=headers, timeout=3)
                if cevap.status_code == 200:
                    veri = cevap.json().get('value', [])
                    if veri:
                        df = pd.DataFrame(veri)[['itemDescTr', 'value1', 'value2']]
                        ceyrek_adi = f"Q{int(p1)//3}"
                        gecmis_ceyrek_adi = f"Q{int(p2)//3}"
                        df.columns = ['Finansal Kalem', f'{y1} {ceyrek_adi}', f'{y2} {gecmis_ceyrek_adi}']
                        df = df[df[f'{y1} {ceyrek_adi}'].notna()].reset_index(drop=True)
                        return df, f"{y1} {ceyrek_adi}", "🇹🇷 İş Yatırım (Yerel Sunucu)"
            except:
                continue
                
    return pd.DataFrame(), None, None

def son_kap_haberleri(sembol):
    url = f"https://news.google.com/rss/search?q={sembol}+hisse+KAP+haberleri&hl=tr&gl=TR&ceid=TR:tr"
    try:
        cevap = requests.get(url, timeout=4)
        root = ET.fromstring(cevap.text)
        haberler = []
        for item in root.findall('.//item')[:5]:
            title = item.find('title').text
            temiz_baslik = title.rsplit(' - ', 1)[0] if ' - ' in title else title
            haberler.append(f"📌 {temiz_baslik}")
        if haberler: return "\n".join(haberler)
    except: pass
    return "Şirketle ilgili son 24 saate ait önemli bir haber akışı bulunamadı."

def yedekli_fiyat_cek(hisse):
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
# 2. YAN MENÜ (PREMIUM SIDEBAR TASARIMI)
# ==========================================
with st.sidebar:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-title'>🤖 BİLANÇO ROBOTU</div>", unsafe_allow_html=True)
    st.markdown("<div class='sidebar-subtitle'>Designed by <b>ALbANiAn_Trader</b> ✅</div>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    st.markdown("### 🎯 Radar Sistemi")
    hisse_kodu = st.text_input("🔍 Hisse Kodu:", placeholder="Örn: ASELS, THYAO").upper()
    analiz_butonu = st.button("🚀 Analizi Başlat", type="primary", use_container_width=True)
    
    st.markdown("---")
    st.markdown("### 🌐 Bağlantılar")
    
    st.markdown(
        """
        <a href="https://x.com/albanian_trader" target="_blank" style="text-decoration: none;">
            <div class="x-button">
                𝕏 @albanian_trader
            </div>
        </a>
        """, unsafe_allow_html=True
    )