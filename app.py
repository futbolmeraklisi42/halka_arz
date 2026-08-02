import streamlit as st
import pandas as pd
import requests
import json
import re
import gspread

# ----------------- SAYFA AYARLARI -----------------
st.set_page_config(
    page_title="Finans & Halka Arz Portalı",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ----------------- GOOGLE SHEETS BAGLANTISI -----------------
@st.cache_resource
def get_gsheet_client():
    try:
        creds = dict(st.secrets["gcp_service_account"])
        
        if "private_key" in creds:
            pk = str(creds["private_key"]).strip()
            pk = pk.strip("'\"")
            pk = pk.replace("\\n", "\n")
            
            lines = pk.split("\n")
            cleaned_lines = []
            for line in lines:
                line_str = line.strip()
                if "BEGIN PRIVATE KEY" in line_str or "END PRIVATE KEY" in line_str:
                    cleaned_lines.append(line_str)
                else:
                    clean_body = re.sub(r'[^A-Za-z0-9+/=]', '', line_str)
                    if clean_body:
                        cleaned_lines.append(clean_body)
            
            creds["private_key"] = "\n".join(cleaned_lines)

        return gspread.service_account_from_dict(creds)
    except Exception as e:
        st.error(f"Google Auth Hatası: {e}")
        return None

# API Kotasını korumak için 5 Dakika (300sn) Caching
@st.cache_data(ttl=300, show_spinner="Veriler çekiliyor...")
def verileri_getir(worksheet_name):
    try:
        client = get_gsheet_client()
        if not client:
            return pd.DataFrame()
        
        sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
        sh = client.open_by_url(sheet_url)
        
        try:
            worksheet = sh.worksheet(worksheet_name)
        except gspread.exceptions.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")
            if worksheet_name == "portfoy":
                worksheet.append_row(["kod", "ad", "hesap_sayisi", "lot", "maliyet", "satis_fiyati", "durum"])
            elif worksheet_name == "gelecek_arzlar":
                worksheet.append_row(["kod", "ad", "fiyat", "talep_tarihi", "islem_tarihi", "durum"])
            elif worksheet_name == "borclar":
                worksheet.append_row(["baslik", "tur", "kisi_kurum", "toplam_tutar", "taksit_sayisi", "odenen_taksit", "odenen_tutar", "aciklama"])

        data = worksheet.get_all_records()
        return pd.DataFrame(data)
    except Exception as e:
        st.error(f"Tablo Okuma Hatası [{worksheet_name}]: {e}")
        return pd.DataFrame()

def veri_kaydet(worksheet_name, df):
    try:
        client = get_gsheet_client()
        if client:
            sheet_url = st.secrets["connections"]["gsheets"]["spreadsheet"]
            sh = client.open_by_url(sheet_url)
            
            try:
                worksheet = sh.worksheet(worksheet_name)
            except gspread.exceptions.WorksheetNotFound:
                worksheet = sh.add_worksheet(title=worksheet_name, rows="100", cols="20")

            worksheet.clear()
            worksheet.update(range_name='A1', values=[df.columns.values.tolist()] + df.values.tolist())
            st.cache_data.clear()
    except Exception as e:
        st.error(f"Kaydetme Hatası [{worksheet_name}]: {e}")

# --- PORTFÖY İŞLEMLERİ ---
def veri_ekle_halka_arz(kod, ad, hesap_sayisi, lot, maliyet):
    df = verileri_getir("portfoy")
    
    # Kuruş Hatalarını Önleyen Dönüştürücü
    try:
        maliyet_val = float(str(maliyet).replace(',', '.'))
    except:
        maliyet_val = 0.0

    yeni_veri = pd.DataFrame([{
        "kod": kod,
        "ad": ad,
        "hesap_sayisi": int(hesap_sayisi),
        "lot": int(lot),
        "maliyet": maliyet_val,
        "satis_fiyati": 0.0,
        "durum": "Aktif"
    }])
    df = pd.concat([df, yeni_veri], ignore_index=True)
    veri_kaydet("portfoy", df)

def hisse_satis_yap(index_no, satis_fiyati):
    df = verileri_getir("portfoy")
    try:
        satis_val = float(str(satis_fiyati).replace(',', '.'))
    except:
        satis_val = 0.0
        
    df.at[index_no, "satis_fiyati"] = satis_val
    df.at[index_no, "durum"] = "Satildi"
    veri_kaydet("portfoy", df)

def hisse_sil(index_no):
    df = verileri_getir("portfoy")
    df = df.drop(index_no).reset_index(drop=True)
    veri_kaydet("portfoy", df)

# --- GELECEK ARZ İŞLEMLERİ ---
def gelecek_arz_ekle(kod, ad, fiyat, talep_tarihi, islem_tarihi, durum):
    df = verileri_getir("gelecek_arzlar")
    try:
        fiyat_val = float(str(fiyat).replace(',', '.'))
    except:
        fiyat_val = 0.0
        
    yeni_veri = pd.DataFrame([{
        "kod": kod,
        "ad": ad,
        "fiyat": fiyat_val,
        "talep_tarihi": str(talep_tarihi),
        "islem_tarihi": str(islem_tarihi),
        "durum": durum
    }])
    df = pd.concat([df, yeni_veri], ignore_index=True)
    veri_kaydet("gelecek_arzlar", df)

def gelecek_arz_sil(index_no):
    df = verileri_getir("gelecek_arzlar")
    df = df.drop(index_no).reset_index(drop=True)
    veri_kaydet("gelecek_arzlar", df)

# --- BORÇ İŞLEMLERİ ---
def borc_ekle(baslik, tur, kisi_kurum, toplam_tutar, taksit_sayisi, aciklama):
    df = verileri_getir("borclar")
    yeni_veri = pd.DataFrame([{
        "baslik": baslik,
        "tur": tur,
        "kisi_kurum": kisi_kurum,
        "toplam_tutar": float(toplam_tutar),
        "taksit_sayisi": int(taksit_sayisi),
        "odenen_taksit": 0,
        "odenen_tutar": 0.0,
        "aciklama": aciklama
    }])
    df = pd.concat([df, yeni_veri], ignore_index=True)
    veri_kaydet("borclar", df)

def taksit_artir(index_no, mevcut_odenen_taksit, taksit_tutari):
    df = verileri_getir("borclar")
    df.at[index_no, "odenen_taksit"] = int(mevcut_odenen_taksit) + 1
    df.at[index_no, "odenen_tutar"] = float(df.at[index_no, "odenen_tutar"]) + float(taksit_tutari)
    veri_kaydet("borclar", df)

def borc_odeme_yap(index_no, odenecek_tutar):
    df = verileri_getir("borclar")
    df.at[index_no, "odenen_tutar"] = float(df.at[index_no, "odenen_tutar"]) + float(odenecek_tutar)
    veri_kaydet("borclar", df)

def borc_sil(index_no):
    df = verileri_getir("borclar")
    df = df.drop(index_no).reset_index(drop=True)
    veri_kaydet("borclar", df)

# ----------------- TRADINGVIEW CANLI BİST VERİSİ -----------------
@st.cache_data(ttl=300)
def canlı_bist_veri_cek(symbol):
    symbol = symbol.upper().strip()
    url = "https://scanner.tradingview.com/turkey/scan"
    
    payload = {
        "symbols": {
            "tickers": [f"BIST:{symbol}"]
        },
        "columns": ["close", "description"]
    }
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Content-Type': 'application/json'
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            if data and "data" in data and len(data["data"]) > 0:
                d = data["data"][0]["d"]
                fiyat = float(d[0])
                sirket_adi = d[1] if d[1] else symbol
                return {"basarili": True, "fiyat": fiyat, "ad": sirket_adi, "kaynak": "TradingView"}
    except Exception:
        pass

    return {"basarili": False, "fiyat": None, "ad": symbol, "kaynak": "Yok"}

def get_bist_price(symbol, fallback_maliyet):
    veri = canlı_bist_veri_cek(symbol)
    if veri["basarili"]:
        return veri["fiyat"]
    return round(fallback_maliyet, 2)

def hisse_durumunu_sorgula(symbol):
    if not symbol:
        return {"durum": "BOŞ", "fiyat": None, "ad": "", "mesaj": "Lütfen bir hisse kodu yazın."}
    
    veri = canlı_bist_veri_cek(symbol)
    if veri["basarili"]:
        return {
            "durum": "ISLEM_GORUYOR",
            "fiyat": veri["fiyat"],
            "ad": veri["ad"],
            "mesaj": f"🟢 Canlı Veri Alındı ({veri['kaynak']}): {symbol} borsada aktif!"
        }
    else:
        return {
            "durum": "BEKLEMEDE",
            "fiyat": None,
            "ad": symbol.upper(),
            "mesaj": "🟡 Hisse henüz işleme açılmamış veya BIST verisi henüz girilmemiş."
        }

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
    .badge-tavan { background-color: #059669; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; }
    .badge-satildi { background-color: #64748b; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; }
    .badge-kredi { background-color: #0284c7; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; }
    .badge-kisisel { background-color: #d97706; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; }
    .badge-taslak { background-color: #6b7280; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; }
    .badge-talep { background-color: #f59e0b; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; }
    .badge-islem { background-color: #10b981; color: white; padding: 3px 10px; border-radius: 12px; font-size: 11px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

# Manuel Önbellek Yenileme Butonu
with st.sidebar:
    st.write("🔄 **Veri Güncelleme**")
    if st.button("Verileri Yenile"):
        st.cache_data.clear()
        st.rerun()

# ----------------- TAB YAPISI -----------------
tab1, tab2, tab3 = st.tabs(["🚀 Portföyüm", "📅 Halka Arz Takvimi", "💳 Borç & Kredi Takip"])

# =========================================================
# TAB 1: HALKA ARZ PORTFÖYÜ
# =========================================================
with tab1:
    st.title("🚀 Halka Arz Portföyüm")
    
    df_portfoy = verileri_getir("portfoy")
    
    df_aktif = pd.DataFrame()
    df_satilan = pd.DataFrame()
    
    if not df_portfoy.empty and "durum" in df_portfoy.columns:
        df_aktif = df_portfoy[df_portfoy["durum"] == "Aktif"]
        df_satilan = df_portfoy[df_portfoy["durum"] == "Satildi"]

    toplam_yatirilan_aktif = 0.0
    toplam_guncel_aktif = 0.0
    if not df_aktif.empty:
        for idx, row in df_aktif.iterrows():
            toplam_lot = int(row['hesap_sayisi']) * int(row['lot'])
            maliyet_fiyat = float(str(row['maliyet']).replace(',', '.'))
            toplam_yatirilan_aktif += (toplam_lot * maliyet_fiyat)
            anlik_fiyat = get_bist_price(row['kod'], maliyet_fiyat)
            toplam_guncel_aktif += (toplam_lot * anlik_fiyat)

    potansiyel_kar = toplam_guncel_aktif - toplam_yatirilan_aktif

    gerceklesen_kar = 0.0
    if not df_satilan.empty:
        for idx, row in df_satilan.iterrows():
            toplam_lot = int(row['hesap_sayisi']) * int(row['lot'])
            maliyet_fiyat = float(str(row['maliyet']).replace(',', '.'))
            satis_fiyati = float(str(row['satis_fiyati']).replace(',', '.'))
            
            maliyet_tutar = toplam_lot * maliyet_fiyat
            satis_tutar = toplam_lot * satis_fiyati
            gerceklesen_kar += (satis_tutar - maliyet_tutar)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Aktif Yatırılan", f"₺{toplam_yatirilan_aktif:,.2f}")
    col2.metric("Aktif Portföy Değeri", f"₺{toplam_guncel_aktif:,.2f}")
    
    # Metrik Renkleri
    pot_delta_str = f"+₺{potansiyel_kar:,.2f}" if potansiyel_kar >= 0 else f"-₺{abs(potansiyel_kar):,.2f}"
    col3.metric("Anlık Potansiyel Kâr", f"₺{potansiyel_kar:,.2f}", pot_delta_str)
    
    gercek_delta_str = f"+₺{gerceklesen_kar:,.2f}" if gerceklesen_kar >= 0 else f"-₺{abs(gerceklesen_kar):,.2f}"
    col4.metric("Cepteki Net Kâr (Satılan)", f"₺{gerceklesen_kar:,.2f}", gercek_delta_str)

    st.divider()

    with st.expander("➕ Halka Arz Ekle (TradingView Canlı Sorgulama)", expanded=False):
        sorgu_kod = st.text_input("Hisse Kodu (Örn: KARCL veya MASFN):", key="sorgu_input").upper().strip()
        
        otomatik_fiyat = 10.0
        otomatik_ad = ""
        
        if sorgu_kod:
            bilgi = hisse_durumunu_sorgula(sorgu_kod)
            if bilgi["durum"] == "ISLEM_GORUYOR":
                st.success(f"{bilgi['mesaj']} (TradingView Fiyatı: ₺{bilgi['fiyat']:.2f})")
                otomatik_fiyat = float(bilgi['fiyat'])
                otomatik_ad = bilgi['ad']
            else:
                st.info(bilgi['mesaj'])

        with st.form("yeni_arz_formu", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            f_kod = col_f1.text_input("Hisse Kodu:", value=sorgu_kod).upper().strip()
            f_ad = col_f2.text_input("Şirket Adı:", value=otomatik_ad)
            
            col_a, col_b, col_c = st.columns(3)
            f_hesap = col_a.number_input("Kaç Hesap Girildi?", min_value=1, value=1, step=1)
            f_lot = col_b.number_input("Hesap Başı Düşen Lot:", min_value=1, value=10, step=1)
            f_maliyet = col_c.number_input("Halka Arz Fiyatı (Hisse Başı ₺):", min_value=0.01, value=otomatik_fiyat, step=0.01, format="%.2f")
            
            submit = st.form_submit_button("Portföye Kaydet")
            if submit:
                if f_kod and f_ad:
                    veri_ekle_halka_arz(f_kod, f_ad, f_hesap, f_lot, f_maliyet)
                    st.success(f"✅ {f_kod} başarıyla Google Sheets'e eklendi!")
                    st.rerun()

    sub_tab1, sub_tab2 = st.tabs(["📌 Aktif Hisselerim", "📜 Satılan & Geçmiş Hisseler"])

    with sub_tab1:
        if df_aktif.empty:
            st.info("Şu an aktif portföyünde hisse bulunmuyor.")
        else:
            for idx, row in df_aktif.iterrows():
                kod = row['kod']
                ad = row['ad']
                hesap_sayisi = int(row['hesap_sayisi'])
                lot = int(row['lot'])
                maliyet = float(str(row['maliyet']).replace(',', '.'))
                
                toplam_lot = hesap_sayisi * lot
                toplam_maliyet = toplam_lot * maliyet
                anlik_fiyat = get_bist_price(kod, maliyet)
                guncel_deger = toplam_lot * anlik_fiyat
                kar = guncel_deger - toplam_maliyet
                yuzde_degisim = ((anlik_fiyat - maliyet) / maliyet) * 100 if maliyet > 0 else 0

                yuzde_str = f"+%{yuzde_degisim:.2f}" if yuzde_degisim >= 0 else f"-%{abs(yuzde_degisim):.2f}"
                
                if kar >= 0:
                    kar_str = f"+₺{kar:,.2f}"
                    kar_renk = "#10b981"  # Yeşil
                else:
                    kar_str = f"-₺{abs(kar):,.2f}"
                    kar_renk = "#ef4444"  # Kırmızı

                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    
                    with c1:
                        st.markdown(f"### {kod} <span class='badge-tavan'>🚀 CANLI</span>", unsafe_allow_html=True)
                        st.write(f"**{ad}**")
                        st.caption(f"👥 **{hesap_sayisi} Hesap** × {lot} Lot = **{toplam_lot} Lot**")
                    
                    with c2:
                        st.write(f"**Anlık Fiyat:** ₺{anlik_fiyat:.2f} ({yuzde_str})")
                        st.write(f"**Maliyet:** ₺{toplam_maliyet:,.2f} ➔ **Değer:** ₺{guncel_deger:,.2f}")
                        st.markdown(f"**Kâr / Zarar:** <span style='color:{kar_renk}; font-weight:bold;'>{kar_str}</span>", unsafe_allow_html=True)
                        
                    with c3:
                        with st.popover("💵 Satış Yap"):
                            st.write(f"**{kod} Satış Kaydı**")
                            satis_f = st.number_input("Hisseleri Kaçtan Sattın? (₺):", min_value=0.01, value=float(anlik_fiyat), step=0.01, format="%.2f", key=f"s_input_{idx}")
                            if st.button("Satışı Onayla", key=f"btn_sat_{idx}"):
                                hisse_satis_yap(idx, satis_f)
                                st.toast(f"{kod} satılanlara aktarıldı!")
                                st.rerun()
                        
                        st.write("")
                        if st.button("🗑️ Sil", key=f"del_h_{idx}"):
                            hisse_sil(idx)
                            st.toast(f"{kod} silindi.")
                            st.rerun()

    with sub_tab2:
        if df_satilan.empty:
            st.info("Henüz satışını yaptığın bir hisse bulunmuyor.")
        else:
            for idx, row in df_satilan.iterrows():
                kod = row['kod']
                ad = row['ad']
                hesap_sayisi = int(row['hesap_sayisi'])
                lot = int(row['lot'])
                maliyet = float(str(row['maliyet']).replace(',', '.'))
                satis_fiyati = float(str(row['satis_fiyati']).replace(',', '.'))
                
                toplam_lot = hesap_sayisi * lot
                toplam_maliyet = toplam_lot * maliyet
                toplam_satis_tutari = toplam_lot * satis_fiyati
                net_kar = toplam_satis_tutari - toplam_maliyet
                kar_orani = ((satis_fiyati - maliyet) / maliyet) * 100 if maliyet > 0 else 0

                kar_orani_str = f"+%{kar_orani:.2f}" if kar_orani >= 0 else f"-%{abs(kar_orani):.2f}"
                
                if net_kar >= 0:
                    net_kar_str = f"+₺{net_kar:,.2f}"
                    net_kar_renk = "#10b981" # Yeşil
                else:
                    net_kar_str = f"-₺{abs(net_kar):,.2f}"
                    net_kar_renk = "#ef4444" # Kırmızı

                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    
                    with c1:
                        st.markdown(f"### {kod} <span class='badge-satildi'>✅ SATILDI</span>", unsafe_allow_html=True)
                        st.write(f"**{ad}**")
                        st.caption(f"👥 **{hesap_sayisi} Hesap** × {lot} Lot = **{toplam_lot} Lot**")
                    
                    with c2:
                        st.write(f"**Maliyet:** ₺{maliyet:.2f} ➔ **Satış:** ₺{satis_fiyati:.2f} ({kar_orani_str})")
                        st.write(f"**Harcanan:** ₺{toplam_maliyet:,.2f} ➔ **Ele Geçen:** ₺{toplam_satis_tutari:,.2f}")
                        st.markdown(f"**Cebine Giren Kâr:** <span style='color:{net_kar_renk}; font-weight:bold;'>{net_kar_str}</span>", unsafe_allow_html=True)
                        
                    with c3:
                        st.write("")
                        if st.button("🗑️ Arşivden Sil", key=f"del_s_{idx}"):
                            hisse_sil(idx)
                            st.toast(f"{kod} arşivden silindi.")
                            st.rerun()

# =========================================================
# TAB 2: GELECEK HALKA ARZLAR VE TAKVİM
# =========================================================
with tab2:
    st.title("📅 Gelecek Halka Arzlar & Takvim")
    df_gelecek = verileri_getir("gelecek_arzlar")

    with st.expander("➕ Manuel Gelecek Halka Arz Ekle", expanded=False):
        with st.form("yeni_gelecek_arz", clear_on_submit=True):
            cg1, cg2 = st.columns(2)
            g_kod = cg1.text_input("Hisse Kodu (Belirsizse Taslak yaz):").upper().strip()
            g_ad = cg2.text_input("Şirket Adı:")
            
            cg3, cg4, cg5 = st.columns(3)
            g_fiyat = cg3.number_input("Halka Arz Fiyatı (₺):", min_value=0.0, value=15.0, step=0.01, format="%.2f")
            g_talep = cg4.text_input("Talep Toplama Tarihi (Örn: 12-13 Ağustos):")
            g_islem = cg5.text_input("İşlem Tarihi (Örn: 18 Ağustos):")
            
            g_durum = st.selectbox("Arz Durumu:", ["Taslak (SPK Bekliyor)", "Talep Toplanıyor", "İşlem Tarihi Belli Oldu"])
            
            g_submit = st.form_submit_button("Takvime Ekle")
            if g_submit:
                if g_ad:
                    gelecek_arz_ekle(g_kod, g_ad, g_fiyat, g_talep, g_islem, g_durum)
                    st.success("✅ Takvime eklendi!")
                    st.rerun()

    st.subheader("📋 Yaklaşan & Onaylanan Halka Arzlar")
    
    if df_gelecek.empty:
        st.info("Henüz takvime eklenmiş halka arz bulunmuyor.")
    else:
        for idx, row in df_gelecek.iterrows():
            gkod = row['kod']
            gad = row['ad']
            gfiyat = float(str(row['fiyat']).replace(',', '.')) if str(row['fiyat']).replace('.','',1).replace(',','',1).isdigit() else 0.0
            gtalep = row['talep_tarihi']
            gislem = row['islem_tarihi']
            gdurum = row['durum']

            badge_style = "badge-taslak"
            if "Talep" in str(gdurum):
                badge_style = "badge-talep"
            elif "İşlem" in str(gdurum):
                badge_style = "badge-islem"

            with st.container(border=True):
                gc1, gc2, gc3 = st.columns([2, 2, 1])
                
                with gc1:
                    st.markdown(f"### {gkod} <span class='{badge_style}'>{gdurum}</span>", unsafe_allow_html=True)
                    st.write(f"**{gad}**")
                    st.write(f"**Halka Arz Fiyatı:** ₺{gfiyat:.2f}" if gfiyat > 0 else "**Halka Arz Fiyatı:** Açıklanmadı")

                with gc2:
                    st.write(f"📅 **Talep Toplama:** {gtalep if gtalep else 'Açıklanmadı'}")
                    st.write(f"🔔 **Borsa İşlem Tarihi:** {gislem if gislem else 'Açıklanmadı'}")

                with gc3:
                    with st.popover("➕ Portföyüme Aktar"):
                        st.write("Düşen lot miktarını girip portföyüne ekle:")
                        p_hesap = st.number_input("Kaç Hesap?", min_value=1, value=1, key=f"gh_{idx}")
                        p_lot = st.number_input("Lot Sayısı?", min_value=1, value=10, key=f"gl_{idx}")
                        p_fiyat = st.number_input("Arz Fiyatı (₺):", min_value=0.01, value=float(gfiyat) if gfiyat > 0 else 10.0, step=0.01, format="%.2f", key=f"gf_{idx}")
                        if st.button("Aktarmayı Onayla", key=f"g_btn_{idx}"):
                            veri_ekle_halka_arz(gkod, gad, p_hesap, p_lot, p_fiyat)
                            gelecek_arz_sil(idx)
                            st.toast("Hisse portföyüne başarıyla aktarıldı!")
                            st.rerun()

                    st.write("")
                    if st.button("🗑️ Sil", key=f"gdel_{idx}"):
                        gelecek_arz_sil(idx)
                        st.toast("Takvimden silindi.")
                        st.rerun()

# =========================================================
# TAB 3: BORÇ & KREDİ TAKİP
# =========================================================
with tab3:
    st.title("💳 Borç & Kredi Defteri")
    
    df_borc = verileri_getir("borclar")
    
    toplam_ana_borc = 0.0
    toplam_odenen_borc = 0.0
    
    if not df_borc.empty:
        toplam_ana_borc = pd.to_numeric(df_borc['toplam_tutar'], errors='coerce').fillna(0).sum()
        toplam_odenen_borc = pd.to_numeric(df_borc['odenen_tutar'], errors='coerce').fillna(0).sum()
        
    kalan_toplam_borc = toplam_ana_borc - toplam_odenen_borc
    
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Toplam Borç / Kredi", f"₺{toplam_ana_borc:,.2f}")
    mc2.metric("Ödenen Toplam Tutar", f"₺{toplam_odenen_borc:,.2f}")
    mc3.metric("Kalan Toplam Borç", f"₺{kalan_toplam_borc:,.2f}", f"-₺{kalan_toplam_borc:,.2f}", delta_color="inverse")
    
    st.divider()

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

    st.subheader("📋 Aktif Borç Listesi")
    
    if df_borc.empty:
        st.info("Kayıtlı borç bulunmuyor. Rahatsın! 😎")
    else:
        for idx, row in df_borc.iterrows():
            baslik = row['baslik']
            tur = row['tur']
            kisi = row['kisi_kurum']
            toplam = float(row['toplam_tutar']) if str(row['toplam_tutar']).replace('.','',1).isdigit() else 0.0
            taksit_s = int(row['taksit_sayisi']) if str(row['taksit_sayisi']).isdigit() else 1
            odenen_taksit = int(row['odenen_taksit']) if str(row['odenen_taksit']).isdigit() else 0
            odenen_tutar = float(row['odenen_tutar']) if str(row['odenen_tutar']).replace('.','',1).isdigit() else 0.0
            aciklama = row['aciklama']
            
            kalan = toplam - odenen_tutar
            taksit_tutari = toplam / taksit_s if taksit_s > 0 else toplam
            
            badge = "<span class='badge-kredi'>💳 KREDİ</span>" if tur == 'Kredi' else "<span class='badge-kisisel'>🤝 KIŞISEL</span>"
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                
                with c1:
                    st.markdown(f"### {baslik} {badge}", unsafe_allow_html=True)
                    st.write(f"**Alacaklı/Kurum:** {kisi}")
                    if aciklama and str(aciklama) != "nan":
                        st.caption(f"📝 Not: {aciklama}")
                        
                with c2:
                    st.write(f"**Toplam:** ₺{toplam:,.2f} | **Ödenen:** ₺{odenen_tutar:,.2f}")
                    st.markdown(f"**Kalan Borç:** <span style='color:#ef4444; font-weight:bold;'>₺{kalan:,.2f}</span>", unsafe_allow_html=True)
                    
                    ilerleme = min(odenen_tutar / toplam, 1.0) if toplam > 0 else 0
                    st.progress(ilerleme, text=f"%{ilerleme*100:.0f} Ödendi")

                with c3:
                    if tur == 'Kredi':
                        st.write(f"**Taksit:** {odenen_taksit}/{taksit_s} Ay")
                        st.caption(f"Aylık: ₺{taksit_tutari:,.2f}")
                        
                        if odenen_taksit < taksit_s and kalan > 0:
                            if st.button(f"☑️ {odenen_taksit + 1}. Taksiti Öde", key=f"taksit_{idx}"):
                                taksit_artir(idx, odenen_taksit, taksit_tutari)
                                st.toast(f"{odenen_taksit + 1}. taksit ödendi olarak işaretlendi!")
                                st.rerun()
                        else:
                            st.success("Tüm taksitler bitti! 🎉")
                    else:
                        if kalan > 0:
                            odenecek = st.number_input("Ödenen Tutar (₺):", min_value=1.0, max_value=float(kalan), value=float(kalan), key=f"input_p_{idx}")
                            if st.button("💵 Ödeme Yap", key=f"pay_{idx}"):
                                borc_odeme_yap(idx, odenecek)
                                st.toast("Ödeme kaydedildi!")
                                st.rerun()
                        else:
                            st.success("Borç Kapandı! 🎉")
                            
                    st.write("")
                    if st.button("🗑️ Kaydı Sil", key=f"del_b_{idx}"):
                        borc_sil(idx)
                        st.toast("Borç kaydı silindi.")
                        st.rerun()

    # GENERAL FİNANSAL ÖZET BARI
    st.divider()
    st.subheader("⚖️ Genel Finansal Denge")
    toplam_cebe_giren_kar = gerceklesen_kar + potansiyel_kar
    net_durum = toplam_cebe_giren_kar - kalan_toplam_borc
    
    if net_durum >= 0:
        st.success(f"💚 **Tebrikler!** Toplam Halka Arz kârın (Anlık + Satılan) kalan borçlarını karşılıyor. **Net Artı Bakiyen: +₺{net_durum:,.2f}**")
    else:
        st.error(f"🔴 **Dikkat:** Halka arz kârların kalan borcunu henüz karşılamıyor. **Net Açık: ₺{net_durum:,.2f}**")
