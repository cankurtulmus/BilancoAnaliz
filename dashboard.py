import streamlit as st
import borsapy as bp
import requests
from google import genai
import pandas as pd
import plotly.graph_objects as go
import xml.etree.ElementTree as ET

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
    strong { color: #1DA1F2 !important; } 
    </style>
    """,
    unsafe_allow_html=True
)

API_SIFRESI = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_SIFRESI)

# ==========================================
# AKILLI ÇİFT KADEMELİ (YEREL -> GLOBAL) MOTORLAR
# ==========================================
def yerel_bilanco_cek(sembol):
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
                headers = {'User-Agent': 'Mozilla/5.0'}
                cevap = requests.get(url, params=params, headers=headers, timeout=4)
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
        for item in root.findall('.//item')[:5]: # Haber sayısını 5'e çıkardık
            title = item.find('title').text
            temiz_baslik = title.rsplit(' - ', 1)[0] if ' - ' in title else title
            haberler.append(f"📌 {temiz_baslik}")
        if haberler:
            return "\n".join(haberler)
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
# 2. YAN MENÜ (REKLAM VE ARAMA)
# ==========================================
with st.sidebar:
    try:
        st.image("logo.png", use_container_width=True)
    except:
        st.markdown("### 🤖 BİLANÇO ROBOTU")
    
    st.markdown("<p style='text-align: center; font-size: 0.8em;'>Designed by ALbANiAn_Trader ✅</p>", unsafe_allow_html=True)
    st.markdown("---")
    
    st.title("Radar")
    hisse_kodu = st.text_input("🔍 Hisse Kodu (Örn: ASELS, THYAO):").upper()
    analiz_butonu = st.button("📊 Kapsamlı Rapor Hazırla", type="primary", use_container_width=True)
    
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
    st.caption("⚙️ Sistem: Profesyonel Kurumsal Rapor Modu Aktif")

# ==========================================
# 3. ANA EKRAN VE ANALİZ MANTIĞI
# ==========================================
st.title("📈 Bilanço Robotu: Akıllı Finansal Terminal")

if analiz_butonu and hisse_kodu:
    with st.spinner(f"⏳ {hisse_kodu} için kapsamlı aracı kurum raporu formatında analiz hazırlanıyor. Bu biraz sürebilir..."):
        try:
            hisse = bp.Ticker(hisse_kodu)
            info = hisse.info
            
            # --- VERİ ÇEKME İŞLEMLERİ ---
            guncel_bilanco, bulunan_donem, kaynak = yerel_bilanco_cek(hisse_kodu)
            
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
                        kaynak = "🌍 Borsa Global API (Yedek Sunucu)"
                except: pass

            haberler_metni = son_kap_haberleri(hisse_kodu)

            # KAYNAK BİLGİSİ
            if "Yerel" in str(kaynak):
                st.success(f"📡 **Veri Kaynağı:** {kaynak} | 📅 **Dönem:** {bulunan_donem} (En Taze Veri)")
            elif "Global" in str(kaynak):
                st.warning(f"📡 **Veri Kaynağı:** {kaynak} | 📅 **Dönem:** {bulunan_donem} (Yerel sunucu yanıt vermedi, globalden çekildi)")
            else:
                st.error("📡 Hiçbir sunucudan (Yerel veya Global) veri alınamadı!")

            son_fiyat = yedekli_fiyat_cek(hisse)
            piyasa_degeri = info.get('marketCap') or hisse.fast_info.get('market_cap', "N/A")
            fk_orani = info.get('trailingPE', "N/A")
            pddd_orani = info.get('priceToBook', "N/A")

            pd_hesapli = f"{(piyasa_degeri / 1_000_000_000):.2f} Mrd ₺" if isinstance(piyasa_degeri, (int, float)) else "N/A"

            # --- ÜST BİLGİ KARTLARI ---
            st.markdown("### 📌 Temel Göstergeler")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Son Fiyat", f"{son_fiyat:.2f} ₺" if isinstance(son_fiyat, (int, float)) else "N/A")
            c2.metric("Piyasa Değeri", pd_hesapli)
            c3.metric("F/K Oranı", guvenli_format(fk_orani))
            c4.metric("PD/DD Oranı", guvenli_format(pddd_orani))

            st.divider()

            # --- SEKMELER ---
            tab1, tab2, tab3 = st.tabs(["📑 Kapsamlı Analiz Raporu", "📰 KAP & Haber Akışı", "📉 Mali Tablolar & Grafik"])

            with tab1:
                if not guncel_bilanco.empty:
                    st.subheader(f"📑 {hisse_kodu} Kapsamlı Bilanço Analiz Raporu")
                    st.caption(f"Yapay Zeka Destekli Kurumsal Değerlendirme | Dönem: {bulunan_donem}")
                    
                    # --- İŞTE YENİ, DEVASA VE KURUMSAL PROMPT ---
                    istek = f"""
                    Sen, üst düzey bir aracı kurumda çalışan (örneğin İş Yatırım veya GCM Yatırım) Kıdemli Hisse Senedi Analistisin.
                    Aşağıda sana {hisse_kodu} hissesine ait en güncel ({bulunan_donem}) karşılaştırmalı finansal tabloyu, güncel piyasa çarpanlarını ve son dakika KAP haberlerini veriyorum.
                    
                    Senden istediğim şey kısa bir özet değil; son derece detaylı, ağırbaşlı, rakamlarla konuşan ve profesyonel bir "Kapsamlı Bilanço Analiz Raporu" yazmandır.
                    
                    Raporun KESİNLİKLE aşağıdaki başlıklara ve yapıya sahip olmalıdır:

                    **1. GELİR TABLOSU VE KÂRLILIK ANALİZİ**
                    (Satış gelirlerindeki büyüme oranını, brüt/net kâr marjlarındaki değişimi tabloya bakarak detaylıca yorumla. Reel bir büyüme olup olmadığını değerlendir.)

                    **2. BİLANÇO VE FİNANSAL YAPI DEĞERLENDİRMESİ**
                    (Tablodaki kalemlerden yola çıkarak şirketin varlık büyümesi, özkaynak yapısı ve eğer veri varsa borçluluk durumu hakkında analitik yorumlar yap.)

                    **3. STRATEJİK GELİŞMELER VE HABER AKIŞI**
                    (Aşağıda verdiğim güncel haber başlıklarını analiz et. Şirketin aldığı ihaleler, yeni yatırımlar, sipariş defteri veya stratejik hamleleri varsa bunları detaylandırarak şirketin geleceğine etkisini açıkla.)

                    **4. DEĞERLEME VE PİYASA ÇARPANLARI**
                    (F/K Oranı: {guvenli_format(fk_orani)}, PD/DD Oranı: {guvenli_format(pddd_orani)}, Piyasa Değeri: {pd_hesapli}. Bu çarpanları değerlendir. Şirket pahalı mı, ucuz mu, yoksa büyüme beklentileri mi fiyatlanıyor? Detaylıca yorumla.)

                    **5. GENEL DEĞERLENDİRME VE BEKLENTİLER**
                    Bu bölümü iki alt başlığa ayırarak profesyonelce tamamla:
                    * **Güçlü Yönler:** (Tablodan ve haberlerden çıkardığın en az 3 çok güçlü argüman)
                    * **Dikkat Noktaları / Riskler:** (Yatırımcının dikkat etmesi gereken makro veya mikro en az 2 risk faktörü)

                    Kurallar:
                    - Rapor dili son derece resmi, objektif ve finansal terimlere hakim olmalıdır.
                    - Asla hayali rakamlar uydurma, sadece aşağıdaki verileri kullan.
                    
                    Finansal Tablo Verileri:
                    {guncel_bilanco.to_markdown()}
                    
                    Son Haberler ve KAP Başlıkları:
                    {haberler_metni}
                    """
                    cevap = client.models.generate_content(model='gemini-2.5-flash', contents=istek)
                    st.markdown(cevap.text)

            with tab2:
                st.subheader("📰 Son Dakika Haber Radar Sistemi")
                st.caption(f"Google Haberler altyapısı kullanılarak {hisse_kodu} için KAP ve borsa haberleri taranmıştır.")
                
                if "bulunamadı" not in haberler_metni:
                    st.success("Analize dahil edilen son dakika haberleri:")
                    st.markdown(haberler_metni)
                else:
                    st.warning(haberler_metni)

            with tab3:
                st.subheader("📊 Mali Tablolar ve Fiyat Gelişimi")
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.write("**Detaylı Mali Tablo**")
                    if not guncel_bilanco.empty:
                        st.dataframe(guncel_bilanco, use_container_width=True, height=400)
                    else:
                        st.warning("Tablo verisi yok.")
                        
                with col_b:
                    st.write("**Son 6 Aylık Fiyat Hareketi**")
                    gecmis = hisse.history(period="6ay")
                    if not gecmis.empty:
                        fig = go.Figure(data=[go.Candlestick(x=gecmis.index, open=gecmis['Open'], high=gecmis['High'], low=gecmis['Low'], close=gecmis['Close'])])
                        fig.update_layout(template="plotly_dark", xaxis_rangeslider_visible=False, margin=dict(l=0, r=0, t=0, b=0))
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.warning("Grafik verisi bulunamadı.")

        except Exception as e:
            st.error(f"Sistemsel bir hata oluştu. Hata Detayı: {e}")
else:
    st.info("👈 Kapsamlı kurumsal analize başlamak için sol menüden hisse kodunu girin.")