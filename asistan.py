import borsapy as bp
from google import genai
import pandas as pd

# ==========================================
# 1. YAPAY ZEKA BAĞLANTI AYARLARI
# ==========================================
# Şifreyi güvenli dosyadan çekiyoruz
API_SIFRESI = st.secrets["GEMINI_API_KEY"] 
client = genai.Client(api_key=API_SIFRESI)

def kapsamli_bilanco_analizi(sembol):
    print(f"Lütfen bekleyin, {sembol} için temel oranlar ve bilançolar toplanıyor...\n")
    
    # ==========================================
    # 2. BORSAPY İLE FİNANSAL VERİLERİ ÇEKME
    # ==========================================
    hisse = bp.Ticker(sembol)
    info = hisse.info
    fast_info = hisse.fast_info
    
    # Kütüphaneye özel güvenli veri çekme aracı (Hata almamak için)
    def guvenli_al(kaynak, anahtar):
        try:
            return kaynak[anahtar]
        except:
            return "Bilinmiyor"
            
    # Temel Verileri Güvenle Çekiyoruz
    sektor = guvenli_al(info, 'sector')
    endustri = guvenli_al(info, 'industry')
    son_fiyat = guvenli_al(fast_info, 'last_price')
    piyasa_degeri = guvenli_al(fast_info, 'market_cap')
    fk_orani = guvenli_al(info, 'trailingPE')
    pddd_orani = guvenli_al(info, 'priceToBook')
    favok = guvenli_al(info, 'ebitda')
    zirve_52 = guvenli_al(info, 'fiftyTwoWeekHigh')
    dip_52 = guvenli_al(info, 'fiftyTwoWeekLow')

    # Finansal Tabloları Çekme
    try:
        gelir_tablosu = hisse.quarterly_income_stmt.iloc[:, :2].to_markdown()
        bilanco = hisse.quarterly_balance_sheet.iloc[:, :2].to_markdown()
        nakit_akis = hisse.quarterly_cashflow.iloc[:, :2].to_markdown()
    except Exception as e:
        gelir_tablosu = "Gelir tablosu detayları çekilemedi."
        bilanco = "Bilanço detayları çekilemedi."
        nakit_akis = "Nakit akış detayları çekilemedi."

    # Analist Hedefleri
    try:
        hedefler = hisse.analyst_price_targets
    except:
        hedefler = "Hedef fiyat verisi yok."

    # Yapay zekaya okutacağımız devasa ham veri paketi
    ham_veri_paketi = f"""
    Şirket Sembolü: {sembol}
    Sektör: {sektor} - {endustri}

    TEMEL GÖSTERGELER:
    - Son Fiyat: {son_fiyat} TL
    - Piyasa Değeri: {piyasa_degeri} TL
    - F/K Oranı (Trailing PE): {fk_orani}
    - PD/DD Oranı (Price to Book): {pddd_orani}
    - FAVÖK (EBITDA): {favok} TL
    - 52 Haftalık Zirve/Dip: {zirve_52} / {dip_52}
    
    ANALİST HEDEFLERİ:
    {hedefler}

    --- ÇEYREKLİK GELİR TABLOSU (Milyon TL) ---
    {gelir_tablosu}

    --- ÇEYREKLİK BİLANÇO (Varlıklar ve Yükümlülükler) ---
    {bilanco}

    --- ÇEYREKLİK NAKİT AKIŞI ---
    {nakit_akis}
    """
    
    print("Mali tablolar başarıyla indirildi! Gemini bilanço raporunu yazıyor...\n")

    # ==========================================
    # 3. GEMINI'A ÖZEL FORMAT TALİMATI (PROMPT)
    # ==========================================
    istek = f"""
    Sen uzman bir yeminli mali müşavir ve kıdemli borsa analistisin. Sana '{sembol}' hissesine ait en güncel temel oranları, çeyreklik gelir tablosunu, bilançoyu ve nakit akışını veriyorum.
    
    Senden isteğim, bu ham verileri kullanarak tıpkı profesyonel bir aracı kurumun hazırladığı gibi "Kapsamlı Bilanço Analiz Raporu" oluşturman.
    
    Raporun BAŞLIKLARI VE YAPISI KESİNLİKLE ŞU ŞEKİLDE OLMALIDIR:
    1. TEMEL GÖSTERGELER (Fiyat, Piyasa Değeri, F/K, PD/DD vb. bir özet tablo gibi)
    2. GELİR TABLOSU ANALİZİ (Ciro büyümesi, faaliyet karı ve net kar gelişimi yorumu)
    3. BİLANÇO ANALİZİ (Varlıkların kalitesi, özkaynak artışı, borçluluk durumu)
    4. NAKİT AKIŞ VE YATIRIM ANALİZİ (Şirketin nakit yaratma gücü)
    5. GENEL DEĞERLENDİRME VE BEKLENTİLER (Alt başlık olarak 'Güçlü Yönler' ve 'Dikkat Noktaları' maddeler halinde yazılmalı)

    Kurallar:
    - Sadece sana verdiğim "Ham Veriler" kısmındaki gerçek rakamları kullan. Olmayan bir veriyi uydurma.
    - Rakamsal değişimleri (Örneğin bir önceki çeyreğe göre kar artışı/azalışı) yüzdesel olarak hesaplayıp yorumla.
    - Dilin tamamen profesyonel, objektif ve yatırımcıyı aydınlatıcı olmalı.
    
    İşte Ham Veriler:
    {ham_veri_paketi}
    """
    
    cevap = client.models.generate_content(
        model='gemini-2.5-flash',
        contents=istek,
    )
    
    print("=================================================================")
    print(f"       📊 {sembol} KAPSAMLI BİLANÇO VE FİNANSAL ANALİZ RAPORU 📊")
    print("=================================================================")
    print(cevap.text)

# Sistemi çalıştıralım 
# ==========================================
# 4. SİSTEMİ ÇALIŞTIRMA KISMI (İNTERAKTİF MENÜ)
# ==========================================
print("Yapay Zeka Borsa Asistanına Hoş Geldiniz!")
print("-----------------------------------------")

while True:
    istenen_hisse = input("\nAnaliz edilecek hisse kodunu girin (Çıkmak için 'q' tuşuna basın): ").upper()
    
    if istenen_hisse == 'Q':
        print("Asistan kapatılıyor. Bol kazançlar dilerim!")
        break
        
    try:
        kapsamli_bilanco_analizi(istenen_hisse)
    except Exception as e:
        print(f"Bir hata oluştu. Lütfen hisse kodunu (Örn: THYAO, FROTO) doğru girdiğinizden emin olun.")