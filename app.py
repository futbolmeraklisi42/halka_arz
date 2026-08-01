import streamlit as st
import pandas as pd
import yfinance as yf

# Sayfa Yapılandırması (Mobil Uyumlu & Geniş)
st.set_page_config(
    page_title="Halka Arz Takip",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Dark Mode Özel CSS Dokunuşları
st.markdown("""
<style>
    .main { background-color: #0e1117; }
    .stMetric {
        background-color: #1e293b;
        padding: 15px;
        border-radius: 15px;
        border: 1px solid #334155;
    }
    .badge-tavan {
        background-color: #059669;
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

# Örnek Veri Seti (İleride bunu SQLite veya Google Sheets'e bağlayabiliriz)
if "portfoy" not in st.session_state:
    st.session_state.portfoy = [
        {"kod": "BINBN", "ad": "Binbin Skooter", "hesap_sayisi": 3, "lot": 15, "maliyet": 10.00, "durum": "Aktif"},
        {"kod": "EFORC", "ad": "Efor Çay", "hesap_sayisi": 2, "lot": 40, "maliyet": 14.50, "durum": "Aktif"}
    ]

# ----------------- BAŞLIK VE ÖZET KARTLARI -----------------
st.title("🚀 Halka Arz Portföyüm")
st.caption("Canlı Borsa & Çoklu Hesap Takip Paneli")

# Canlı Fiyat Çekme Fonksiyonu
def get_bist_price(symbol):
    try:
        # BIST hisseleri için .IS uzantısı kullanılır
        ticker = yf.Ticker(f"{symbol}.IS")
        data = ticker.history(period="1d")
        if not data.empty:
            return round(data['Close'].iloc[-1], 2)
    except:
        pass
    return None

# Toplam Hesaplamalar
toplam_yatirilan = 0.0
toplam_guncel = 0.0

for h in st.session_state.portfoy:
    toplam_lot = h["hesap_sayisi"] * h["lot"]
    maliyet_tutar = toplam_lot * h["maliyet"]
    toplam_yatirilan += maliyet_tutar
    
    # Canlı fiyat (Eğer çekilemezse varsayılan test fiyatı)
    canli_fiyat = get_bist_price(h["kod"]) or (h["maliyet"] * 1.4)
    toplam_guncel += (toplam_lot * canli_fiyat)

toplam_kar = toplam_guncel - toplam_yatirilan
kar_orani = (toplam_kar / toplam_yatirilan * 100) if toplam_yatirilan > 0 else 0

# Üst Metrikler
col1, col2, col3 = st.columns(3)
col1.metric("Toplam Yatırılan", f"₺{toplam_yatirilan:,.2f}")
col2.metric("Güncel Portföy", f"₺{toplam_guncel:,.2f}", f"+%{kar_orani:.1f}")
col3.metric("Toplam Net Kâr", f"₺{toplam_kar:,.2f}", f"₺{toplam_kar:,.2f}")

st.divider()

# ----------------- YENİ HALKA ARZ EKLEME -----------------
with st.expander("➕ Yeni Halka Arz Ekle", expanded=False):
    with st.form("yeni_arz_formu"):
        f_kod = st.text_input("Hisse Kodu (Örn: BINBN):").upper()
        f_ad = st.text_input("Şirket Adı:")
        col_a, col_b, col_c = st.columns(3)
        f_hesap = col_a.number_input("Kaç Hesap?", min_value=1, value=1)
        f_lot = col_b.number_input("Hesap Başı Lot:", min_value=1, value=10)
        f_maliyet = col_c.number_input("Halka Arz Fiyatı (₺):", min_value=0.1, value=10.0)
        
        submit = st.form_submit_button("Portföye Ekle")
        if submit and f_kod:
            st.session_state.portfoy.append({
                "kod": f_kod, "ad": f_ad, "hesap_sayisi": f_hesap,
                "lot": f_lot, "maliyet": f_maliyet, "durum": "Aktif"
            })
            st.success(f"{f_kod} başarıyla eklendi!")
            st.rerun()

# ----------------- AKTİF PORTFÖY LİSTESİ -----------------
st.subheader("📌 Aktif Hisselerim")

for idx, item in enumerate(st.session_state.portfoy):
    toplam_lot = item["hesap_sayisi"] * item["lot"]
    toplam_maliyet = toplam_lot * item["maliyet"]
    
    # Fiyat çekimi
    fiyat = get_bist_price(item["kod"]) or (item["maliyet"] * 1.45) 
    guncel_deger = toplam_lot * fiyat
    kar = guncel_deger - toplam_maliyet
    yuzde = ((fiyat - item["maliyet"]) / item["maliyet"]) * 100

    with st.container(border=True):
        c1, c2, c3 = st.columns([2, 2, 1])
        
        with c1:
            st.markdown(f"### {item['kod']} <span class='badge-tavan'>🚀 TAVAN</span>", unsafe_allow_html=True)
            st.caption(f"{item['ad']} | **{item['hesap_sayisi']} Hesap** × {item['lot']} Lot = **{toplam_lot} Lot**")
        
        with c2:
            st.write(f"**Anlık Fiyat:** ₺{fiyat:.2f} (%+{yuzde:.1f})")
            st.write(f"**Maliyet:** ₺{toplam_maliyet:,.2f} ➔ **Değer:** ₺{guncel_deger:,.2f}")
            st.markdown(f"**Kâr/Zarar:** <span style='color:#059669; font-weight:bold;'>+₺{kar:,.2f}</span>", unsafe_allow_html=True)
            
        with c3:
            if st.button("Satış Yap", key=f"sat_{idx}"):
                st.toast(f"{item['kod']} satış kaydı alındı!")
