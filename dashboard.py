import streamlit as st
import borsapy as bp
from google import genai
import pandas as pd
import plotly.graph_objects as go

# ==========================================
# 1. SAYFA VE YAPAY ZEKA AYARLARI
# ==========================================
st.set_page_config(page_title="AI Borsa Asistanı", page_icon="🚀", layout="wide")

# Şifreyi artık Streamlit'in güvenli kasasından (secrets) alıyoruz
API_SIFRESI = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=API_SIFRESI)

def guvenli_al(kaynak, anahtar):
    try:
        return kaynak[anahtar]
    except:
        return "N/A"

# ==========================================
# 2. YAN MENÜ (SIDEBAR) TASARIMI
# ==========================================
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/3135/3135706.png", width=100)
    st.title("🤖 Asistan Menüsü")
    st.markdown("---")
    hisse_kodu = st.text_input("🔍 Hisse Kodu (Örn: KARSN):", placeholder="Hisse kodu girin...").upper()
    analiz_butonu = st.button("📊 Kapsamlı Analiz Başlat", type="primary", use_container_width=True)
    st.markdown("---")
    st.caption("💡 *İpucu: Bu sayfayı PDF olarak kaydetmek için klavyenizden Ctrl+P yapabilirsiniz.*")

# ==========================================
# 3. ANA EKRAN TASARIMI
# ==========================================
st.title("📈 Yapay Zeka Destekli Finans Terminali")

if analiz_butonu and hisse_kodu:
    with st.spinner(f"⏳ {hisse_kodu} için hem YILLIK hem ÇEYREKLİK finansal analiz yapılıyor. Lütfen bekleyin..."):
        try:
            # --- Veri Çekme ---
            hisse = bp.Ticker(hisse_kodu)
            info = hisse.info
            fast_info = hisse.fast_info
            
            # Temel Veriler
            son_fiyat = guvenli_al(fast_info, 'last_price')
            onceki_kapanis = guvenli_al(fast_info, 'previous_close')
            piyasa_degeri = guvenli_al(fast_info, 'market_cap')
            fk_orani = guvenli_al(info, 'trailingPE')
            pddd_orani = guvenli_al(info, 'priceToBook')
            
            # Günlük Değişim
            try:
                degisim_tl = son_fiyat - onceki_kapanis
                degisim_yuzde = (degisim_tl / onceki_kapanis) * 100
                degisim_metni = f"{degisim_tl:.2f} TL ({degisim_yuzde:.2f}%)"
            except:
                degisim_metni = "N/A"

            # --- FİNANSAL TABLOLAR (YILLIK VE ÇEYREKLİK) ---
            try:
                # Yıllık Tablolar (En güncel 2 yıl - Q4 verilerini kapsar)
                yillik_gelir = hisse.income_stmt.iloc[:, :2]
                yillik_bilanco = hisse.balance_sheet.iloc[:, :2]
                yillik_nakit = hisse.cashflow.iloc[:, :2]
                
                # Çeyreklik Tablolar (En güncel 2 çeyrek)
                ceyrek_gelir = hisse.quarterly_income_stmt.iloc[:, :2]
                ceyrek_bilanco = hisse.quarterly_balance_sheet.iloc[:, :2]
                ceyrek_nakit = hisse.quarterly_cashflow.iloc[:, :2]
            except Exception as e:
                st.error("Finansal tablolar çekilirken bir sorun oluştu.")
                yillik_gelir = yillik_bilanco = yillik_nakit = pd.DataFrame()
                ceyrek_gelir = ceyrek_bilanco = ceyrek_nakit = pd.DataFrame()

            # --- ÜST BİLGİ KARTLARI ---
            st.markdown("### 📌 Temel Göstergeler")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(label="Son Fiyat", value=f"{son_fiyat} ₺", delta=degisim_metni)
            with col2:
                pd_milyar = float(piyasa_degeri) / 1_000_000_000 if piyasa_degeri != "N/A" else "N/A"
                st.metric(label="Piyasa Değeri", value=f"{pd_milyar:.2f} Mr ₺" if pd_milyar != "N/A" else "N/A")
            with col3:
                st.metric(label="F/K Oranı", value=f"{fk_orani:.2f}" if type(fk_orani) in [float, int] else fk_orani)
            with col4:
                st.metric(label="PD/DD Oranı", value=f"{pddd_orani:.2f}" if type(pddd_orani) in [float, int] else pddd_orani)

            st.markdown("---")

            # --- YENİ SEKMELER TASARIMI ---
            tab1, tab2, tab3, tab4 = st.tabs(["🤖 Çift Yönlü YZ Raporu", "📅 Yıllık Tablolar (Q4)", "⏱️ Çeyreklik Tablolar", "📉 İnteraktif Grafik"])

            with tab1:
                st.subheader(f"🧠 Gemini Yıllık & Çeyreklik Analiz Raporu: {hisse_kodu}")
                
                istek = f"""
                Sen uzman bir finansal analistsin. Sana '{hisse_kodu}' hissesinin hem YILLIK (Yıl Sonu/Q4 kapsayan) hem de ÇEYREKLİK güncel finansal tablolarını veriyorum.
                
                Senden istediğim:
                1. Önce YILLIK bazda şirketin genel büyümesini, net karını ve borçluluğunu yorumla.
                2. Sonra ÇEYREKLİK bazda son 3 aylık performanstaki ivmeyi (momentum) yorumla.
                3. Şirketin Nakit Akışı durumunu değerlendir.
                4. Sonuç olarak yatırımcıya "Güçlü Yönler" ve "Dikkat Edilmesi Gereken Riskler" sun.

                Lütfen emojiler kullan, profesyonel bir dil seç ve rakamları yuvarlayarak anlaşılır kıl.

                YILLIK GELİR TABLOSU:
                {yillik_gelir.to_markdown() if not yillik_gelir.empty else "Bilinmiyor"}
                YILLIK BİLANÇO:
                {yillik_bilanco.to_markdown() if not yillik_bilanco.empty else "Bilinmiyor"}
                
                ÇEYREKLİK GELİR TABLOSU:
                {ceyrek_gelir.to_markdown() if not ceyrek_gelir.empty else "Bilinmiyor"}
                ÇEYREKLİK BİLANÇO:
                {ceyrek_bilanco.to_markdown() if not ceyrek_bilanco.empty else "Bilinmiyor"}
                """
                
                cevap = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=istek,
                )
                
                st.info("Aşağıdaki rapor, şirketin hem Yıllık (Q4/Yılsonu) hem de Çeyreklik tabloları harmanlanarak yapay zeka tarafından oluşturulmuştur.")
                st.markdown(cevap.text)

            with tab2:
                st.subheader("📁 Yıllık (Yıl Sonu / 12 Aylık) Finansal Tablolar")
                st.caption("Şirketin son açıklanan yıl sonu (Q4 dahil) kapanış verileridir.")
                exp1 = st.expander("💸 Yıllık Gelir Tablosu", expanded=True)
                exp1.dataframe(yillik_gelir, use_container_width=True)
                exp2 = st.expander("⚖️ Yıllık Bilanço")
                exp2.dataframe(yillik_bilanco, use_container_width=True)
                exp3 = st.expander("🌊 Yıllık Nakit Akış Tablosu")
                exp3.dataframe(yillik_nakit, use_container_width=True)

            with tab3:
                st.subheader("📁 Çeyreklik (3 Aylık) Finansal Tablolar")
                st.caption("Şirketin sadece ilgili 3 aylık dönem içindeki (örneğin Q3) performansını gösterir.")
                exp4 = st.expander("💸 Çeyreklik Gelir Tablosu", expanded=True)
                exp4.dataframe(ceyrek_gelir, use_container_width=True)
                exp5 = st.expander("⚖️ Çeyreklik Bilanço")
                exp5.dataframe(ceyrek_bilanco, use_container_width=True)
                exp6 = st.expander("🌊 Çeyreklik Nakit Akış Tablosu")
                exp6.dataframe(ceyrek_nakit, use_container_width=True)

            with tab4:
                st.subheader(f"📅 {hisse_kodu} Son 6 Aylık Fiyat Hareketi")
                gecmis_veri = hisse.history(period="6ay")
                if not gecmis_veri.empty:
                    fig = go.Figure(data=[go.Candlestick(x=gecmis_veri.index,
                                    open=gecmis_veri['Open'],
                                    high=gecmis_veri['High'],
                                    low=gecmis_veri['Low'],
                                    close=gecmis_veri['Close'])])
                    fig.update_layout(
                        margin=dict(l=20, r=20, t=20, b=20),
                        height=500,
                        template="plotly_dark",
                        xaxis_rangeslider_visible=False
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning("Grafik verisi çekilemedi.")

        except Exception as e:
            st.error(f"Sistem Hatası: Lütfen kodu doğru girdiğinizden emin olun. Detay: {e}")
elif analiz_butonu and not hisse_kodu:
    st.warning("Lütfen sol taraftaki menüden bir hisse kodu girin.")
else:
    st.info("👈 Analize başlamak için sol taraftaki menüden bir hisse kodu girin ve butona basın.")