import streamlit as st
import pandas as pd
import sqlite3

# yfinance yüklenemezse uygulamanın çökmesini engellemek için güvenli import
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False

# ----------------- SAYFA AYARLARI -----------------
st.set_page_config(
    page_title="Finans & Halka Arz Paneli",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- VERİ TABANI KURULUMU -----------------
def init_db():
    conn = sqlite3.connect("halka_arz.db")
    c = conn.cursor()
    # Halka Arz Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS portfoy (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT NOT NULL,
            ad TEXT NOT NULL,
            hesap_sayisi INTEGER NOT NULL,
            lot INTEGER NOT NULL,
            maliyet REAL NOT NULL,
            durum TEXT DEFAULT 'Aktif'
        )
    ''')
    # Borç & Kredi Tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS borclar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            baslik TEXT NOT NULL,
            tur TEXT NOT NULL, -- 'Kredi' veya 'Kişisel'
            kisi_kurum TEXT NOT NULL,
            toplam_tutar REAL NOT NULL,
            taksit_sayisi INTEGER DEFAULT 1,
            odenen_taksit INTEGER DEFAULT 0,
            odenen_tutar REAL DEFAULT 0.0,
            aciklama TEXT
        )
    ''')
    conn.commit()
    conn.close()

# Database İşlemleri - Halka Arz
def veri_ekle_halka_arz(kod, ad, hesap_sayisi, lot, maliyet):
    conn = sqlite3.connect("halka_arz.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO portfoy (kod, ad, hesap_sayisi, lot, maliyet, durum)
        VALUES (?, ?, ?, ?, ?, 'Aktif')
    ''', (kod, ad, hesap_sayisi, lot, maliyet))
    conn.commit()
    conn.close()

def verileri_getir_halka_arz():
    conn = sqlite3.connect("halka_arz.db")
    df = pd.read_sql_query("SELECT * FROM portfoy WHERE durum = 'Aktif'", conn)
    conn.close()
    return df

def hisse_sil(hisse_id):
    conn = sqlite3.connect("halka_arz.db")
    c = conn.cursor()
    c.execute("DELETE FROM portfoy WHERE id = ?", (hisse_id,))
    conn.commit()
    conn.close()

# Database İşlemleri - Borçlar
def borc_ekle(baslik, tur, kisi_kurum, toplam_tutar, taksit_sayisi, aciklama):
    conn = sqlite3.connect("halka_arz.db")
    c = conn.cursor()
    c.execute('''
        INSERT INTO borclar (baslik, tur, kisi_kurum, toplam_tutar, taksit_sayisi, odenen_taksit, odenen_tutar, aciklama)
        VALUES (?, ?, ?, ?, ?, 0, 0.0, ?)
    ''', (baslik, tur, kisi_kurum, toplam_tutar, taksit_sayisi, aciklama))
    conn.commit()
    conn.close()

def borclari_getir():
    conn = sqlite3.connect("halka_arz.db")
    df = pd.read_sql_query("SELECT * FROM borclar", conn)
    conn.close()
    return df

def taksit_artir(borc_id, mevcut_odenen_taksit, taksit_tutari):
    conn = sqlite3.connect("halka_arz.db")
    c = conn.cursor()
    yeni_odenen = mevcut_odenen_taksit + 1
    c.execute('''
        UPDATE borclar 
        SET odenen_taksit = ?, odenen_tutar = odenen_tutar + ?
        WHERE id = ?
    ''', (yeni_odenen, taksit_tutari, borc_id))
    conn.commit()
    conn.close()

def borc_odeme_yap(borc_id, odenecek_tutar):
    conn = sqlite3.connect("halka_arz.db")
    c = conn.cursor()
    c.execute('''
        UPDATE borclar 
        SET odenen_tutar = odenen_tutar + ?
        WHERE id = ?
    ''', (odenecek_tutar, borc_id))
    conn.commit()
    conn.close()

def borc_sil(borc_id):
    conn = sqlite3.connect("halka_arz.db")
    c = conn.cursor()
    c.execute("DELETE FROM borclar WHERE id = ?", (borc_id,))
    conn.commit()
    conn.close()

# Veri tabanını başlat
init_db()

# ----------------- CANLI BİST FİYAT ÇEKİCİ -----------------
def get_bist_price(symbol, fallback_maliyet):
    if YFINANCE_AVAILABLE:
        try:
            ticker = yf.Ticker(f"{symbol}.IS")
            data = ticker.history(period="1d")
            if not data.empty:
                return round(data['Close'].iloc[-1], 2)
        except:
            pass
    return round(fallback_maliyet * 1.10, 2)

# ----------------- CSS / STİL -----------------
st.markdown("""
<style>
    .main { background-color: #0f172a; }
    .stMetric {
        background: rgba(30, 41, 59, 0.7);
        padding: 15px;
        border-radius: 15px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }
    .badge-tavan {
        background-color: #059669;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: bold;
    }
    .badge-kredi {
        background-color: #0284c7;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
    }
    .badge-kisisel {
        background-color: #d97706;
        color: white;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
    }
</style>
""", unsafe_allow_html=True)

# ----------------- TAB YAPISI -----------------
tab1, tab2 = st.tabs(["🚀 Halka Arz Takip", "💳 Borç & Kredi Takip"])

# =========================================================
# TAB 1: HALKA ARZ TAKİP
# =========================================================
with tab1:
    st.title("🚀 Halka Arz Portföyüm")
    
    df_portfoy = verileri_getir_halka_arz()

    toplam_yatirilan = 0.0
    toplam_guncel = 0.0

    if not df_portfoy.empty:
        for _, row in df_portfoy.iterrows():
            toplam_lot = row['hesap_sayisi'] * row['lot']
            toplam_yatirilan += (toplam_lot * row['maliyet'])
            anlik_fiyat = get_bist_price(row['kod'], row['maliyet'])
            toplam_guncel += (toplam_lot * anlik_fiyat)

    toplam_kar = toplam_guncel - toplam_yatirilan
    kar_orani = (toplam_kar / toplam_yatirilan * 100) if toplam_yatirilan > 0 else 0.0

    col1, col2, col3 = st.columns(3)
    col1.metric("Toplam Yatırılan", f"₺{toplam_yatirilan:,.2f}")
    col2.metric("Güncel Portföy Değeri", f"₺{toplam_guncel:,.2f}", f"+%{kar_orani:.1f}")
    col3.metric("Halka Arz Net Kâr", f"₺{toplam_kar:,.2f}", f"₺{toplam_kar:,.2f}")

    st.divider()

    with st.expander("➕ Yeni Halka Arz Ekle", expanded=False):
        with st.form("yeni_arz_formu", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            f_kod = col_f1.text_input("Hisse Kodu (Örn: BINBN):").upper().strip()
            f_ad = col_f2.text_input("Şirket Adı:")
            
            col_a, col_b, col_c = st.columns(3)
            f_hesap = col_a.number_input("Kaç Hesap Girildi?", min_value=1, value=1, step=1)
            f_lot = col_b.number_input("Hesap Başı Düşen Lot:", min_value=1, value=10, step=1)
            f_maliyet = col_c.number_input("Halka Arz Fiyatı (₺):", min_value=0.01, value=10.0, step=0.1)
            
            submit = st.form_submit_button("Portföye Kaydet")
            if submit:
                if f_kod and f_ad:
                    veri_ekle_halka_arz(f_kod, f_ad, f_hesap, f_lot, f_maliyet)
                    st.success(f"✅ {f_kod} başarıyla eklendi!")
                    st.rerun()

    st.subheader("📌 Aktif Hisselerim")

    if df_portfoy.empty:
        st.info("Henüz portföyüne eklenmiş bir halka arz bulunmuyor.")
    else:
        for _, row in df_portfoy.iterrows():
            hisse_id = row['id']
            kod = row['kod']
            ad = row['ad']
            hesap_sayisi = row['hesap_sayisi']
            lot = row['lot']
            maliyet = row['maliyet']
            
            toplam_lot = hesap_sayisi * lot
            toplam_maliyet = toplam_lot * maliyet
            anlik_fiyat = get_bist_price(kod, maliyet)
            guncel_deger = toplam_lot * anlik_fiyat
            kar = guncel_deger - toplam_maliyet
            yuzde_degisim = ((anlik_fiyat - maliyet) / maliyet) * 100

            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                
                with c1:
                    st.markdown(f"### {kod} <span class='badge-tavan'>🚀 CANLI</span>", unsafe_allow_html=True)
                    st.write(f"**{ad}**")
                    st.caption(f"👥 **{hesap_sayisi} Hesap** × {lot} Lot = **{toplam_lot} Lot**")
                
                with c2:
                    st.write(f"**Anlık Fiyat:** ₺{anlik_fiyat:.2f} (%+{yuzde_degisim:.1f})")
                    st.write(f"**Maliyet:** ₺{toplam_maliyet:,.2f} ➔ **Değer:** ₺{guncel_deger:,.2f}")
                    st.markdown(f"**Kâr / Zarar:** <span style='color:#10b981; font-weight:bold;'>+₺{kar:,.2f}</span>", unsafe_allow_html=True)
                    
                with c3:
                    st.write("")
                    if st.button("🗑️ Sil / Satıldı", key=f"del_h_{hisse_id}"):
                        hisse_sil(hisse_id)
                        st.toast(f"{kod} portföyden çıkarıldı!")
                        st.rerun()

# =========================================================
# TAB 2: BORÇ & KREDİ TAKİP
# =========================================================
with tab2:
    st.title("💳 Borç & Kredi Defteri")
    
    df_borc = borclari_getir()
    
    toplam_ana_borc = 0.0
    toplam_odenen_borc = 0.0
    
    if not df_borc.empty:
        toplam_ana_borc = df_borc['toplam_tutar'].sum()
        toplam_odenen_borc = df_borc['odenen_tutar'].sum()
        
    kalan_toplam_borc = toplam_ana_borc - toplam_odenen_borc
    
    # Metrik Kartları
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Toplam Borç / Kredi", f"₺{toplam_ana_borc:,.2f}")
    mc2.metric("Ödenen Toplam Tutar", f"₺{toplam_odenen_borc:,.2f}")
    mc3.metric("Kalan Toplam Borç", f"₺{kalan_toplam_borc:,.2f}", f"-₺{kalan_toplam_borc:,.2f}", delta_color="inverse")
    
    st.divider()

    # YENİ BORÇ / KREDİ EKLEME
    with st.expander("➕ Yeni Borç / Kredi Ekle", expanded=False):
        with st.form("yeni_borc_formu", clear_on_submit=True):
            b_tur = st.radio("Tür Seçin:", ["Bankadan Kredi", "Kişisel Borç (Arkadaş, Kız Arkadaşı vs.)"], horizontal=True)
            
            b_baslik = st.text_input("Başlık (Örn: İhtiyaç Kredisi veya Ahmet'ten Borç):")
            b_kisi = st.text_input("Banka / Kişi Adı (Örn: Garanti Bankası, Ayşe):")
            
            col_b1, col_b2 = st.columns(2)
            b_tutar = col_b1.number_input("Toplam Borç Tutarı (₺):", min_value=1.0, value=25000.0, step=500.0)
            
            if "Kredi" in b_tur:
                b_taksit = col_b2.number_input("Taksit Sayısı (Ay):", min_value=1, value=2, step=1)
            else:
                b_taksit = 1
                col_b2.info("Kişisel borçlar tek parça kabul edilir.")
                
            b_aciklama = st.text_area("Açıklama / Notlar (Opsiyonel):")
            
            b_submit = st.form_submit_button("Borcu Kaydet")
            if b_submit:
                if b_baslik and b_kisi:
                    tur_kod = "Kredi" if "Kredi" in b_tur else "Kişisel"
                    borc_ekle(b_baslik, tur_kod, b_kisi, b_tutar, b_taksit, b_aciklama)
                    st.success("✅ Borç kaydı oluşturuldu!")
                    st.rerun()
                else:
                    st.error("Lütfen Başlık ve Kişi/Banka alanlarını doldurun.")

    st.subheader("📋 Aktif Borç Listesi")
    
    if df_borc.empty:
        st.info("Kayıtlı borç bulunmuyor. Rahatsın! 😎")
    else:
        for _, row in df_borc.iterrows():
            b_id = row['id']
            baslik = row['baslik']
            tur = row['tur']
            kisi = row['kisi_kurum']
            toplam = row['toplam_tutar']
            taksit_s = row['taksit_sayisi']
            odenen_taksit = row['odenen_taksit']
            odenen_tutar = row['odenen_tutar']
            aciklama = row['aciklama']
            
            kalan = toplam - odenen_tutar
            taksit_tutari = toplam / taksit_s if taksit_s > 0 else toplam
            
            badge = "<span class='badge-kredi'>💳 KREDİ</span>" if tur == 'Kredi' else "<span class='badge-kisisel'>🤝 KIŞISEL</span>"
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                
                with c1:
                    st.markdown(f"### {baslik} {badge}", unsafe_allow_html=True)
                    st.write(f"**Alacaklı/Kurum:** {kisi}")
                    if aciklama:
                        st.caption(f"📝 Not: {aciklama}")
                        
                with c2:
                    st.write(f"**Toplam:** ₺{toplam:,.2f} | **Ödenen:** ₺{odenen_tutar:,.2f}")
                    st.markdown(f"**Kalan Borç:** <span style='color:#ef4444; font-weight:bold;'>₺{kalan:,.2f}</span>", unsafe_allow_html=True)
                    
                    # Taksit İlerleme Çubuğu
                    ilerleme = min(odenen_tutar / toplam, 1.0) if toplam > 0 else 0
                    st.progress(ilerleme, text=f"%{ilerleme*100:.0f} Ödendi")

                with c3:
                    if tur == 'Kredi':
                        st.write(f"**Taksit:** {odenen_taksit}/{taksit_s} Ay")
                        st.caption(f"Aylık: ₺{taksit_tutari:,.2f}")
                        
                        if odenen_taksit < taksit_s and kalan > 0:
                            if st.button(f"☑️ {odenen_taksit + 1}. Taksiti Öde", key=f"taksit_{b_id}"):
                                taksit_artir(b_id, odenen_taksit, taksit_tutari)
                                st.toast(f"{odenen_taksit + 1}. taksit ödendi olarak işaretlendi!")
                                st.rerun()
                        else:
                            st.success("Tüm taksitler bitti! 🎉")
                    else:
                        # Kişisel Borç İçin Ödeme
                        if kalan > 0:
                            odenecek = st.number_input("Ödenen Tutar (₺):", min_value=1.0, max_value=float(kalan), value=float(kalan), key=f"input_p_{b_id}")
                            if st.button("💵 Ödeme Yap", key=f"pay_{b_id}"):
                                borc_odeme_yap(b_id, odenecek)
                                st.toast("Ödeme kaydedildi!")
                                st.rerun()
                        else:
                            st.success("Borç Kapandı! 🎉")
                            
                    st.write("")
                    if st.button("🗑️ Kaydı Sil", key=f"del_b_{b_id}"):
                        borc_sil(b_id)
                        st.toast("Borç kaydı silindi.")
                        st.rerun()

    # GENERAL FINANSAL ÖZET BARI
    st.divider()
    st.subheader("⚖️ Genel Finansal Denge")
    net_durum = toplam_kar - kalan_toplam_borc
    
    if net_durum >= 0:
        st.success(f"💚 **Tebrikler!** Halka arz kârların borçlarını karşılıyor. **Net Artı Bakiyen: +₺{net_durum:,.2f}**")
    else:
        st.error(f"🔴 **Dikkat:** Halka arz kârların kalan borcunu henüz karşılamıyor. **Net Açık: ₺{net_durum:,.2f}**")
