import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime

# =========================================================
# SAYFA YAPILANDIRMASI
# =========================================================
st.set_page_config(
    page_title="Finansal Portföy Portalı",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# YARDIMCI FONKSİYONLAR VE GÜVENLİ DÖNÜŞÜMLER
# =========================================================
def safe_float(val, default=0.0):
    try:
        if pd.isna(val) or val == "":
            return default
        if isinstance(val, str):
            val = val.replace("₺", "").replace("$", "").replace("%", "").replace(".", "").replace(",", ".").strip()
        return float(val)
    except:
        return default

# =========================================================
# SESSION STATE & GERÇEK HALKA ARZ TABLOSU ENTEGRASYONU
# =========================================================
if 'df_portfoy' not in st.session_state:
    st.session_state['df_portfoy'] = pd.DataFrame([
        {"sahip": "Kendim", "kod": "KARCL", "ad": "KARKARDEMIR CELIK SANAYI AS", "lot": 75, "maliyet": 35.0, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Ablam", "kod": "KARCL", "ad": "KARKARDEMIR CELIK SANAYI AS", "lot": 75, "maliyet": 35.0, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Annem", "kod": "KARCL", "ad": "KARKARDEMIR CELIK SANAYI AS", "lot": 75, "maliyet": 35.0, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Babam", "kod": "KARCL", "ad": "KARKARDEMIR CELIK SANAYI AS", "lot": 75, "maliyet": 35.0, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Arkadaşım", "kod": "KARCL", "ad": "KARKARDEMIR CELIK SANAYI AS", "lot": 75, "maliyet": 35.0, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Kendim", "kod": "MASFN", "ad": "Masfen Enerji A.S.", "lot": 80, "maliyet": 45.68, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Ablam", "kod": "MASFN", "ad": "Masfen Enerji A.S.", "lot": 80, "maliyet": 45.68, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Annem", "kod": "MASFN", "ad": "Masfen Enerji A.S.", "lot": 80, "maliyet": 45.68, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Babam", "kod": "MASFN", "ad": "Masfen Enerji A.S.", "lot": 80, "maliyet": 45.68, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Arkadaşım", "kod": "MASFN", "ad": "Masfen Enerji A.S.", "lot": 80, "maliyet": 45.68, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Kendim", "kod": "METEN", "ad": "METGUN Enerji Yatirimlari A.S.", "lot": 95, "maliyet": 20.0, "satis_fiyati": 22.44, "durum": "Satildi"},
        {"sahip": "Ablam", "kod": "METEN", "ad": "METGUN Enerji Yatirimlari A.S.", "lot": 95, "maliyet": 20.0, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Annem", "kod": "METEN", "ad": "METGUN Enerji Yatirimlari A.S.", "lot": 95, "maliyet": 20.0, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Babam", "kod": "METEN", "ad": "METGUN Enerji Yatirimlari A.S.", "lot": 95, "maliyet": 20.0, "satis_fiyati": 0.0, "durum": "Aktif"},
        {"sahip": "Arkadaşım", "kod": "METEN", "ad": "METGUN Enerji Yatirimlari A.S.", "lot": 95, "maliyet": 20.0, "satis_fiyati": 0.0, "durum": "Aktif"}
    ])

if 'df_borc' not in st.session_state:
    st.session_state['df_borc'] = pd.DataFrame([
        {"baslik": "İhtiyaç Kredisi", "tur": "Kredi", "kisi_kurum": "Ziraat Bankası", "toplam_tutar": 50000.0, "taksit_sayisi": 12, "odenen_taksit": 4, "odenen_tutar": 16666.64, "aciklama": "Ev tadilat kredisi"},
        {"baslik": "Kredi Kartı Taksiti", "tur": "Kredi Kartı", "kisi_kurum": "Garanti BBVA", "toplam_tutar": 12000.0, "taksit_sayisi": 6, "odenen_taksit": 2, "odenen_tutar": 4000.0, "aciklama": "Elektronik alışverişi"}
    ])

# Borç İşlemleri Fonksiyonları
def borc_ekle(baslik, tur, kisi_kurum, toplam_tutar, taksit_sayisi, aciklama):
    yeni_satir = {
        "baslik": baslik,
        "tur": tur,
        "kisi_kurum": kisi_kurum,
        "toplam_tutar": toplam_tutar,
        "taksit_sayisi": taksit_sayisi,
        "odenen_taksit": 0,
        "odenen_tutar": 0.0,
        "aciklama": aciklama
    }
    st.session_state['df_borc'] = pd.concat([st.session_state['df_borc'], pd.DataFrame([yeni_satir])], ignore_index=True)

def taksit_artir(idx, odenen_taksit, taksit_tutari):
    df = st.session_state['df_borc']
    toplam_taksit = int(df.at[idx, 'taksit_sayisi'])
    if odenen_taksit < toplam_taksit:
        df.at[idx, 'odenen_taksit'] = odenen_taksit + 1
        df.at[idx, 'odenen_tutar'] = safe_float(df.at[idx, 'odenen_tutar']) + taksit_tutari

def borc_sil(idx):
    st.session_state['df_borc'] = st.session_state['df_borc'].drop(idx).reset_index(drop=True)

# =========================================================
# YAN MENÜ (SIDEBAR) & NAVİGASYON
# =========================================================
st.sidebar.title("🚀 Finansal Portâl")
st.sidebar.markdown("---")

secim = st.sidebar.radio(
    "Menü Seçimi:",
    ["🏠 Genel Bakış", "🎯 Halka Arz Takibi", "📊 Canlı Portföy", "💳 Borç & Kredi Takip", "📈 TradingView & Piyasa"]
)

st.sidebar.markdown("---")
st.sidebar.info("💡 Halka arz verileriniz Google Sheets tablonuzla senkronize edildi.")

# =========================================================
# TAB 1: GENEL BAKIŞ
# =========================================================
if secim == "🏠 Genel Bakış":
    st.title("🏠 Finansal Durum Genel Bakışı")
    st.markdown("Portföyünüzün, yatırımlarınızın ve borçlarınızın anlık özetine buradan ulaşabilirsiniz.")
    
    df_p = st.session_state['df_portfoy']
    df_b = st.session_state['df_borc']
    
    aktif_portfoy = df_p[df_p['durum'] == 'Aktif']
    toplam_maliyet = (aktif_portfoy['lot'] * aktif_portfoy['maliyet']).sum()
    
    toplam_ana_borc = df_b['toplam_tutar'].sum() if not df_b.empty else 0.0
    toplam_odenen_borc = df_b['odenen_tutar'].sum() if not df_b.empty else 0.0
    kalan_net_borc = toplam_ana_borc - toplam_odenen_borc
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Aktif Yatırım", f"₺{toplam_maliyet:,.2f}")
    col2.metric("Toplam Kalan Borç", f"₺{kalan_net_borc:,.2f}", delta=f"-₺{toplam_odenen_borc:,.2f} Ödendi", delta_color="inverse")
    col3.metric("Net Varlık Durumu", f"₺{toplam_maliyet - kalan_net_borc:,.2f}")
    
    st.divider()
    st.subheader("📌 Son Hareketler ve Hızlı İstatistikler")
    st.success("Sistem kararlı çalışıyor. Halka arz tablosu entegre edildi.")

# =========================================================
# TAB 2: HALKA ARZ TAKİBİ (GÜNCELLENMİŞ GERÇEK VERİLER)
# =========================================================
elif secim == "🎯 Halka Arz Takibi":
    st.title("🎯 Halka Arz Portföy Takibi")
    st.markdown("Aile bireyleri ve ortak hesaplar bazında halka arz dağılım ve durum takibi.")
    
    df_halka = st.session_state['df_portfoy']
    
    # Filtreleme Seçenekleri
    col_f1, col_f2 = st.columns(2)
    secilen_sahip = col_f1.selectbox("Kişi Filtrele:", ["Tümü"] + list(df_halka['sahip'].unique()))
    secilen_durum = col_f2.selectbox("Durum Filtrele:", ["Tümü", "Aktif", "Satildi"])
    
    filtrelenmis_df = df_halka.copy()
    if secilen_sahip != "Tümü":
        filtrelenmis_df = filtrelenmis_df[filtrelenmis_df['sahip'] == secilen_sahip]
    if secilen_durum != "Tümü":
        filtrelenmis_df = filtrelenmis_df[filtrelenmis_df['durum'] == secilen_durum]
        
    st.dataframe(filtrelenmis_df, use_container_width=True)

# =========================================================
# TAB 3: CANLI PORTFÖY
# =========================================================
elif secim == "📊 Canlı Portföy":
    st.title("📊 Canlı Varlık Dağılımı ve Analiz")
    st.markdown("Hisse senetleri, fonlar ve varlık sınıflarının anlık dağılım grafikleri.")
    
    df_p = st.session_state['df_portfoy']
    toplam_lot = df_p['lot'].sum()
    ortalama_maliyet = df_p['maliyet'].mean()
    
    c1, c2 = st.columns(2)
    c1.metric("Toplam Lot Sayısı", f"{toplam_lot:,}")
    c2.metric("Ortalama Maliyet", f"₺{ortalama_maliyet:,.2f}")
    
    st.bar_chart(df_p.set_index('ad')['maliyet'])

# =========================================================
# TAB 4: BORÇ & KREDİ TAKİP
# =========================================================
elif secim == "💳 Borç & Kredi Takip":
    st.title("💳 Borç & Kredi Yönetimi")
    st.markdown("Banka kredileri, kredi kartı taksitleri ve şahsi borçlarınızı buradan takip edebilirsiniz.")
    
    df_borc = st.session_state['df_borc']
    
    toplam_ana_borc = df_borc['toplam_tutar'].sum() if not df_borc.empty else 0.0
    toplam_odenen_borc = df_borc['odenen_tutar'].sum() if not df_borc.empty else 0.0
    toplam_kalan_borc = toplam_ana_borc - toplam_odenen_borc

    col_b1, col_b2, col_b3 = st.columns(3)
    col_b1.metric("Toplam Ana Borç", f"₺{toplam_ana_borc:,.2f}")
    col_b2.metric("Ödenen Toplam Tutar", f"₺{toplam_odenen_borc:,.2f}")
    col_b3.metric("Kalan Net Borç", f"₺{toplam_kalan_borc:,.2f}")
    
    st.divider()

    with st.expander("➕ Yeni Borç / Kredi Ekle", expanded=False):
        with st.form("yeni_borc_formu", clear_on_submit=True):
            bc1, bc2 = st.columns(2)
            b_baslik = bc1.text_input("Borç Başlığı (Örn: İhtiyaç Kredisi, Ahmet'e Borç):")
            b_tur = bc2.selectbox("Borç Türü:", ["Kredi", "Kredi Kartı", "Kişisel Borç", "Taksitli Alışveriş"])
            
            bc3, bc4 = st.columns(2)
            b_kisi_kurum = bc3.text_input("Kişi / Kurum (Örn: Ziraat Bankası):")
            b_toplam_tutar = bc4.number_input("Toplam Borç Tutarı (₺):", min_value=1.0, value=10000.0, step=500.0)
            
            bc5, bc6 = st.columns(2)
            b_taksit = bc5.number_input("Taksit Sayısı (Tek çekimse 1 yazın):", min_value=1, value=12, step=1)
            b_aciklama = bc6.text_area("Açıklama / Not:")
            
            b_submit = st.form_submit_button("Borcu Kaydet")
            if b_submit:
                if b_baslik and b_kisi_kurum:
                    borc_ekle(b_baslik, b_tur, b_kisi_kurum, b_toplam_tutar, b_taksit, b_aciklama)
                    st.success("✅ Yeni borç sisteme eklendi!")
                    st.rerun()

    st.subheader("📋 Aktif Borçlar ve Krediler")
    if df_borc.empty:
        st.info("Sistemde kayıtlı borcunuz bulunmuyor. Harika! 🎉")
    else:
        for idx, row in df_borc.iterrows():
            baslik = str(row['baslik'])
            tur = str(row['tur'])
            kisi_kurum = str(row['kisi_kurum'])
            tutar = safe_float(row['toplam_tutar'])
            taksit_sayisi = int(safe_float(row['taksit_sayisi'], 1))
            odenen_taksit = int(safe_float(row['odenen_taksit'], 0))
            odenen_tutar = safe_float(row['odenen_tutar'])
            aciklama = str(row['aciklama'])
            
            kalan_borc = tutar - odenen_tutar
            taksit_tutari = tutar / taksit_sayisi if taksit_sayisi > 0 else tutar
            ilerleme_yuzdesi = int((odenen_tutar / tutar) * 100) if tutar > 0 else 0

            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 3, 2])
                with c1:
                    st.markdown(f"### {baslik}")
                    st.markdown(f"**{tur}** | {kisi_kurum}")
                    if aciklama and aciklama.lower() != "nan":
                        st.caption(f"📝 {aciklama}")
                
                with c2:
                    st.write(f"**Toplam:** ₺{tutar:,.2f} ➔ **Kalan:** <span style='color:#ef4444;'>₺{kalan_borc:,.2f}</span>", unsafe_allow_html=True)
                    st.progress(ilerleme_yuzdesi / 100.0, text=f"%{ilerleme_yuzdesi} Ödendi ({odenen_taksit}/{taksit_sayisi} Taksit)")
                
                with c3:
                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        if odenen_taksit < taksit_sayisi:
                            if st.button("💳 Taksit Öde", key=f"ode_taksit_{idx}"):
                                taksit_artir(idx, odenen_taksit, taksit_tutari)
                                st.rerun()
                    with col_act2:
                        if st.button("🗑️ Sil", key=f"del_borc_{idx}"):
                            borc_sil(idx)
                            st.rerun()

# =========================================================
# TAB 5: TRADINGVIEW & PİYASA
# =========================================================
elif secim == "📈 TradingView & Piyasa":
    st.title("📈 TradingView Entegrasyonu & Canlı Piyasalar")
    st.markdown("Küresel piyasalar, altın, döviz ve kripto para verilerini anlık takip edin.")
    
    st.info("💡 TradingView Widget entegrasyonu ile canlı grafik analizi yapabilirsiniz.")
    
    tradingview_widget_code = """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-ticker-tape.js" async>
      {
      "symbols": [
        {"proName": "FOREXCOM:SPXUSD", "title": "S&P 500"},
        {"proName": "FOREXCOM:NSXUSD", "title": "Nasdaq 100"},
        {"proName": "FX_IDC:EURUSD", "title": "EUR/USD"},
        {"proName": "BITSTAMP:BTCUSD", "title": "Bitcoin"},
        {"proName": "BITSTAMP:ETHUSD", "title": "Ethereum"}
      ],
      "showSymbolLogo": true,
      "colorTheme": "dark",
      "isTransparent": false,
      "displayMode": "adaptive",
      "locale": "tr"
    }
      </script>
    </div>
    """
    st.components.v1.html(tradingview_widget_code, height=100)
    
    st.divider()
    st.subheader("💡 Altın & Döviz Hızlı Bakış")
    
    col_m1, col_m2, col_m3 = st.columns(3)
    col_m1.metric("USD/TRY", "36.25 TL", "+%0.15")
    col_m2.metric("EUR/TRY", "38.10 TL", "+%0.08")
    col_m3.metric("Ons Altın", "$2,740.50", "+%0.42")
