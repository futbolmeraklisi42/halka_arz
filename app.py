import streamlit as st
import pandas as pd
import requests
import json
import re
import gspread

# ----------------- SAYFA AYARLARI -----------------
st.set_page_config(
    page_title="Finans & Varlık Yönetim Portalı",
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

def safe_float(val, default=0.0):
    if val is None or val == "":
        return default
    if isinstance(val, (int, float)):
        return float(val)
    
    val_str = str(val).strip()
    try:
        val_str = val_str.replace(',', '.')
        return float(val_str)
    except:
        return default

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
                worksheet.append_row(["kod", "ad", "sahip", "lot", "maliyet", "satis_fiyati", "durum"])
            elif worksheet_name == "gelecek_arzlar":
                worksheet.append_row(["kod", "ad", "fiyat", "talep_tarihi", "islem_tarihi", "durum"])
            elif worksheet_name == "borclar":
                worksheet.append_row(["baslik", "tur", "kisi_kurum", "toplam_tutar", "taksit_sayisi", "odenen_taksit", "odenen_tutar", "aciklama"])
            elif worksheet_name == "nakitler":
                worksheet.append_row(["tanim", "kisi_hesap", "tutar", "birim", "aciklama"])

        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        
        if not df.empty:
            if worksheet_name == "portfoy":
                df["maliyet"] = df["maliyet"].apply(safe_float)
                df["satis_fiyati"] = df["satis_fiyati"].apply(safe_float)
                df["lot"] = df["lot"].apply(lambda x: int(safe_float(x, 1)))
            elif worksheet_name == "gelecek_arzlar":
                df["fiyat"] = df["fiyat"].apply(safe_float)
            elif worksheet_name == "borclar":
                df["toplam_tutar"] = df["toplam_tutar"].apply(safe_float)
                df["odenen_tutar"] = df["odenen_tutar"].apply(safe_float)
                df["taksit_sayisi"] = df["taksit_sayisi"].apply(lambda x: int(safe_float(x, 1)))
                df["odenen_taksit"] = df["odenen_taksit"].apply(lambda x: int(safe_float(x, 0)))
            elif worksheet_name == "nakitler":
                df["tutar"] = df["tutar"].apply(safe_float)

        return df
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
            
            export_df = df.copy()
            for col in export_df.columns:
                export_df[col] = export_df[col].astype(str)
                
            worksheet.update(range_name='A1', values=[export_df.columns.values.tolist()] + export_df.values.tolist())
            st.cache_data.clear()
    except Exception as e:
        st.error(f"Kaydetme Hatası [{worksheet_name}]: {e}")

# --- PORTFÖY İŞLEMLERİ ---
def veri_ekle_halka_arz_kisi(kod, ad, sahip, lot, maliyet):
    df = verileri_getir("portfoy")
    if "sahip" not in df.columns:
        df["sahip"] = "Kendim"
        
    yeni_veri = pd.DataFrame([{
        "kod": str(kod).upper().strip(),
        "ad": str(ad),
        "sahip": str(sahip),
        "lot": int(lot),
        "maliyet": safe_float(maliyet),
        "satis_fiyati": 0.0,
        "durum": "Aktif"
    }])
    df = pd.concat([df, yeni_veri], ignore_index=True)
    veri_kaydet("portfoy", df)

def hisse_satis_yap(index_no, satis_fiyati):
    df = verileri_getir("portfoy")
    df.at[index_no, "satis_fiyati"] = safe_float(satis_fiyati)
    df.at[index_no, "durum"] = "Satildi"
    veri_kaydet("portfoy", df)

def hisse_sil(index_no):
    df = verileri_getir("portfoy")
    df = df.drop(index_no).reset_index(drop=True)
    veri_kaydet("portfoy", df)

# --- GELECEK ARZ İŞLEMLERİ ---
def gelecek_arz_ekle(kod, ad, fiyat, talep_tarihi, islem_tarihi, durum):
    df = verileri_getir("gelecek_arzlar")
    yeni_veri = pd.DataFrame([{
        "kod": str(kod).upper().strip(),
        "ad": str(ad),
        "fiyat": safe_float(fiyat),
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
        "toplam_tutar": safe_float(toplam_tutar),
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
    df.at[index_no, "odenen_tutar"] = safe_float(df.at[index_no, "odenen_tutar"]) + safe_float(taksit_tutari)
    veri_kaydet("borclar", df)

def borc_odeme_yap(index_no, odenecek_tutar):
    df = verileri_getir("borclar")
    df.at[index_no, "odenen_tutar"] = safe_float(df.at[index_no, "odenen_tutar"]) + safe_float(odenecek_tutar)
    veri_kaydet("borclar", df)

def borc_sil(index_no):
    df = verileri_getir("borclar")
    df = df.drop(index_no).reset_index(drop=True)
    veri_kaydet("borclar", df)

# --- NAKİT İŞLEMLERİ ---
def nakit_ekle(tanim, kisi_hesap, tutar, birim, aciklama):
    df = verileri_getir("nakitler")
    yeni_veri = pd.DataFrame([{
        "tanim": tanim,
        "kisi_hesap": kisi_hesap,
        "tutar": safe_float(tutar),
        "birim": birim,
        "aciklama": aciklama
    }])
    df = pd.concat([df, yeni_veri], ignore_index=True)
    veri_kaydet("nakitler", df)

def nakit_sil(index_no):
    df = verileri_getir("nakitler")
    df = df.drop(index_no).reset_index(drop=True)
    veri_kaydet("nakitler", df)

# ----------------- TRADINGVIEW CANLI BİST VERİSİ -----------------
@st.cache_data(ttl=300)
def canlı_bist_veri_cek(symbol):
    symbol = str(symbol).upper().strip()
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
    return safe_float(fallback_maliyet)

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
            "ad": str(symbol).upper(),
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
    .badge-sahip { background-color: #8b5cf6; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; font-weight: bold; }
    .badge-satildi { background-color: #64748b; color: white; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
</style>
""", unsafe_allow_html=True)

# Manuel Önbellek Yenileme
with st.sidebar:
    st.write("🔄 **Veri Güncelleme**")
    if st.button("Verileri Yenile"):
        st.cache_data.clear()
        st.rerun()

# ----------------- TAB YAPISI -----------------
tab1, tab2, tab3, tab4 = st.tabs(["🚀 Portföyüm", "💵 Boştaki Nakit & Varlıklar", "📅 Halka Arz Takvimi", "💳 Borç & Kredi Takip"])

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
            toplam_lot = safe_float(row['lot'], 1)
            maliyet_fiyat = safe_float(row['maliyet'])
            toplam_yatirilan_aktif += (toplam_lot * maliyet_fiyat)
            anlik_fiyat = get_bist_price(row['kod'], maliyet_fiyat)
            toplam_guncel_aktif += (toplam_lot * anlik_fiyat)

    potansiyel_kar = toplam_guncel_aktif - toplam_yatirilan_aktif

    gerceklesen_kar = 0.0
    if not df_satilan.empty:
        for idx, row in df_satilan.iterrows():
            toplam_lot = safe_float(row['lot'], 1)
            maliyet_fiyat = safe_float(row['maliyet'])
            satis_fiyati = safe_float(row['satis_fiyati'])
            
            maliyet_tutar = toplam_lot * maliyet_fiyat
            satis_tutar = toplam_lot * satis_fiyati
            gerceklesen_kar += (satis_tutar - maliyet_tutar)

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Aktif Yatırılan", f"₺{toplam_yatirilan_aktif:,.2f}")
    col2.metric("Aktif Portföy Değeri", f"₺{toplam_guncel_aktif:,.2f}")
    
    pot_delta_str = f"+₺{potansiyel_kar:,.2f}" if potansiyel_kar >= 0 else f"-₺{abs(potansiyel_kar):,.2f}"
    col3.metric("Anlık Potansiyel Kâr", f"₺{potansiyel_kar:,.2f}", pot_delta_str)
    
    gercek_delta_str = f"+₺{gerceklesen_kar:,.2f}" if gerceklesen_kar >= 0 else f"-₺{abs(gerceklesen_kar):,.2f}"
    col4.metric("Cepteki Net Kâr (Satılan)", f"₺{gerceklesen_kar:,.2f}", gercek_delta_str)

    st.divider()

    with st.expander("➕ Yeni Halka Arz Ekle", expanded=False):
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

        with st.form("yeni_arz_kisi_formu", clear_on_submit=True):
            col_f1, col_f2 = st.columns(2)
            f_kod = col_f1.text_input("Hisse Kodu:", value=sorgu_kod).upper().strip()
            f_ad = col_f2.text_input("Şirket Adı:", value=otomatik_ad)
            
            st.write("👥 **Kişi ve Lot Dağılımını Girin:**")
            col_k1, col_k2, col_k3, col_k4, col_k5 = st.columns(5)
            lot_kendim = col_k1.number_input("Kendim (Lot):", min_value=0, value=10, step=1)
            lot_abla = col_k2.number_input("Ablam (Lot):", min_value=0, value=0, step=1)
            lot_anne = col_k3.number_input("Annem (Lot):", min_value=0, value=0, step=1)
            lot_baba = col_k4.number_input("Babam (Lot):", min_value=0, value=0, step=1)
            lot_arkadas = col_k5.number_input("Arkadaşım (Lot):", min_value=0, value=0, step=1)
            
            f_maliyet = st.number_input("Halka Arz Fiyatı (Hisse Başı ₺):", min_value=0.01, value=float(otomatik_fiyat), step=0.01, format="%.2f")
            
            submit = st.form_submit_button("Portföye Kaydet")
            if submit:
                if f_kod and f_ad:
                    eklenen_kisi_sayisi = 0
                    kisi_lot_dict = {
                        "Kendim": lot_kendim,
                        "Ablam": lot_abla,
                        "Annem": lot_anne,
                        "Babam": lot_baba,
                        "Arkadaşım": lot_arkadas
                    }
                    
                    for kisi, lot_miktari in kisi_lot_dict.items():
                        if lot_miktari > 0:
                            veri_ekle_halka_arz_kisi(f_kod, f_ad, kisi, lot_miktari, f_maliyet)
                            eklenen_kisi_sayisi += 1
                    
                    if eklenen_kisi_sayisi > 0:
                        st.success(f"✅ {f_kod} seçilen kişiler için kaydedildi!")
                        st.rerun()

    sub_tab1, sub_tab2 = st.tabs(["📌 Aktif Hisselerim (Sade Görünüm)", "📜 Satılan & Geçmiş Hisseler"])

    # --- SADELEŞTİRİLMİŞ AKTİF HİSSE KARTLARI ---
    with sub_tab1:
        if df_aktif.empty:
            st.info("Şu an aktif portföyünde hisse bulunmuyor.")
        else:
            # Hisse koduna göre grupla
            unique_kods = df_aktif["kod"].unique()
            
            for kod in unique_kods:
                sub_df = df_aktif[df_aktif["kod"] == kod]
                sirket_adi = sub_df.iloc[0]["ad"]
                
                # Toplam hesaplamalar
                toplam_lot = sub_df["lot"].sum()
                birim_maliyet = sub_df.iloc[0]["maliyet"]
                toplam_maliyet = toplam_lot * birim_maliyet
                
                anlik_fiyat = get_bist_price(kod, birim_maliyet)
                toplam_guncel_deger = toplam_lot * anlik_fiyat
                toplam_kar = toplam_guncel_deger - toplam_maliyet
                
                yuzde_degisim = ((anlik_fiyat - birim_maliyet) / birim_maliyet) * 100 if birim_maliyet > 0 else 0
                yuzde_str = f"+%{yuzde_degisim:.2f}" if yuzde_degisim >= 0 else f"-%{abs(yuzde_degisim):.2f}"
                kar_renk = "#10b981" if toplam_kar >= 0 else "#ef4444"
                kar_str = f"+₺{toplam_kar:,.2f}" if toplam_kar >= 0 else f"-₺{abs(toplam_kar):,.2f}"

                # SADE TEK KUTU (EXPANDER)
                with st.expander(f"📈 **{kod}** — Toplam: {toplam_lot} Lot | Anlık: ₺{anlik_fiyat:.2f} ({yuzde_str}) | Kâr: {kar_str}", expanded=True):
                    
                    # Üst özet bilgisi
                    c_info1, c_info2, c_info3 = st.columns(3)
                    c_info1.write(f"🏢 **Şirket:** {sirket_adi}")
                    c_info2.write(f"💵 **Toplam Maliyet:** ₺{toplam_maliyet:,.2f} (Birim: ₺{birim_maliyet:.2f})")
                    c_info3.write(f"💰 **Toplam Güncel Değer:** ₺{toplam_guncel_deger:,.2f}")
                    
                    st.divider()
                    st.markdown("#### 👥 Hesap/Kişi Dağılımı ve Satış İşlemleri")

                    # Kişilerin alt listesi
                    for idx, row in sub_df.iterrows():
                        sahip = str(row.get('sahip', 'Kendim'))
                        lot = int(safe_float(row['lot'], 1))
                        k_maliyet = lot * birim_maliyet
                        k_deger = lot * anlik_fiyat
                        k_kar = k_deger - k_maliyet
                        k_kar_str = f"+₺{k_kar:,.2f}" if k_kar >= 0 else f"-₺{abs(k_kar):,.2f}"
                        k_kar_renk = "#10b981" if k_kar >= 0 else "#ef4444"

                        kc1, kc2, kc3, kc4 = st.columns([2, 3, 2, 2])
                        with kc1:
                            st.markdown(f"<span class='badge-sahip'>👤 {sahip}</span>", unsafe_allow_html=True)
                            st.caption(f"📦 {lot} Lot")
                        with kc2:
                            st.write(f"Maliyet: ₺{k_maliyet:,.2f} ➔ Değer: **₺{k_deger:,.2f}**")
                        with kc3:
                            st.markdown(f"Kâr: <span style='color:{k_kar_renk}; font-weight:bold;'>{k_kar_str}</span>", unsafe_allow_html=True)
                        with kc4:
                            # Sadece bu kişininkini sat veya sil
                            col_b1, col_b2 = st.columns(2)
                            with col_b1:
                                with st.popover("💵 Sat"):
                                    st.write(f"**{sahip} - {kod} Satışı**")
                                    satis_f = st.number_input("Satış Fiyatı (₺):", min_value=0.01, value=float(anlik_fiyat), step=0.01, key=f"s_inp_{idx}")
                                    if st.button("Onayla", key=f"s_btn_{idx}"):
                                        hisse_satis_yap(idx, satis_f)
                                        st.rerun()
                            with col_b2:
                                if st.button("🗑️ Sil", key=f"del_h_{idx}"):
                                    hisse_sil(idx)
                                    st.rerun()
                        st.write("---")

    with sub_tab2:
        if df_satilan.empty:
            st.info("Henüz satışını yaptığın bir hisse bulunmuyor.")
        else:
            for idx, row in df_satilan.iterrows():
                kod = str(row['kod'])
                ad = str(row['ad'])
                sahip = str(row.get('sahip', 'Kendim'))
                lot = int(safe_float(row['lot'], 1))
                maliyet = safe_float(row['maliyet'])
                satis_fiyati = safe_float(row['satis_fiyati'])
                
                toplam_maliyet = lot * maliyet
                toplam_satis_tutari = lot * satis_fiyati
                net_kar = toplam_satis_tutari - toplam_maliyet
                kar_orani = ((satis_fiyati - maliyet) / maliyet) * 100 if maliyet > 0 else 0

                kar_orani_str = f"+%{kar_orani:.2f}" if kar_orani >= 0 else f"-%{abs(kar_orani):.2f}"
                net_kar_str = f"+₺{net_kar:,.2f}" if net_kar >= 0 else f"-₺{abs(net_kar):,.2f}"
                net_kar_renk = "#10b981" if net_kar >= 0 else "#ef4444"

                with st.container(border=True):
                    c1, c2, c3 = st.columns([2, 2, 1])
                    with c1:
                        st.markdown(f"### {kod} <span class='badge-satildi'>✅ SATILDI ({sahip})</span>", unsafe_allow_html=True)
                        st.write(f"**{ad}**")
                        st.caption(f"📦 **{lot} Lot**")
                    with c2:
                        st.write(f"**Maliyet:** ₺{maliyet:.2f} ➔ **Satış:** ₺{satis_fiyati:.2f} ({kar_orani_str})")
                        st.markdown(f"**Cebine Giren Kâr:** <span style='color:{net_kar_renk}; font-weight:bold;'>{net_kar_str}</span>", unsafe_allow_html=True)
                    with c3:
                        if st.button("🗑️ Sil", key=f"del_s_{idx}"):
                            hisse_sil(idx)
                            st.rerun()

# =========================================================
# TAB 2: BOŞTA DURAN NAKİT & VARLIKLAR
# =========================================================
with tab2:
    st.title("💵 Borsa Hesaplarında & Cepte Duran Nakitler")
    st.caption("Farklı hesaplarda senin adına duran boşta TL, Dolar, Euro veya Altın nakitlerini buradan takip et.")
    
    df_nakit = verileri_getir("nakitler")
    
    toplam_boştaki_nakit_tl = 0.0
    if not df_nakit.empty:
        for _, row in df_nakit.iterrows():
            toplam_boştaki_nakit_tl += safe_float(row['tutar'])
            
    st.metric("Cebimdeki / Hesaplardaki Toplam Boşta Nakit (TL)", f"₺{toplam_boştaki_nakit_tl:,.2f}")
    st.divider()

    with st.expander("➕ Yeni Boşta Nakit / Para Ekle", expanded=True):
        with st.form("yeni_nakit_formu", clear_on_submit=True):
            cn1, cn2 = st.columns(2)
            n_tanim = cn1.text_input("Nakit Tanımı (Örn: Borsa Hesabı Boşta Para, Cüzdan, Abla Hesabı Para):")
            n_kisi = cn2.selectbox("Paranın Durduğu Hesap/Kişi:", ["Kendi Borsa Hesabım", "Ablamın Hesabı", "Annemin Hesabı", "Babamın Hesabı", "Cüzdan/Nakit"])
            
            cn3, cn4 = st.columns(2)
            n_tutar = cn3.number_input("Tutar (₺):", min_value=1.0, value=1000.0, step=100.0)
            n_birim = cn4.selectbox("Para Birimi:", ["TL", "USD", "EUR", "GOLD"])
            
            n_aciklama = st.text_area("Açıklama / Not (Opsiyonel):")
            
            n_submit = st.form_submit_button("Nakiti Kaydet")
            if n_submit:
                if n_tanim:
                    nakit_ekle(n_tanim, n_kisi, n_tutar, n_birim, n_aciklama)
                    st.success("✅ Nakit varlık eklendi!")
                    st.rerun()

    st.subheader("📋 Kayıtlı Boşta Nakit Listesi")
    if df_nakit.empty:
        st.info("Henüz boşta nakit kaydı girmediniz.")
    else:
        for idx, row in df_nakit.iterrows():
            tanim = str(row['tanim'])
            kisi_hesap = str(row['kisi_hesap'])
            tutar = safe_float(row['tutar'])
            birim = str(row['birim'])
            aciklama = str(row['aciklama'])

            with st.container(border=True):
                nc1, nc2, nc3 = st.columns([2, 2, 1])
                with nc1:
                    st.markdown(f"### 💵 {tanim}")
                    st.write(f"**Bulunduğu Yer:** {kisi_hesap}")
                    if aciklama and aciklama.lower() != "nan":
                        st.caption(f"📝 Not: {aciklama}")
                with nc2:
                    st.markdown(f"### <span style='color:#10b981;'>₺{tutar:,.2f} {birim}</span>", unsafe_allow_html=True)
                with nc3:
                    if st.button("🗑️ Sil", key=f"del_nakit_{idx}"):
                        nakit_sil(idx)
                        st.rerun()

# =========================================================
# TAB 3: GELECEK HALKA ARZLAR
# =========================================================
with tab3:
    st.title("📅 Gelecek Halka Arzlar & Takvim")
    df_gelecek = verileri_getir("gelecek_arzlar")

    with st.expander("➕ Manuel Gelecek Halka Arz Ekle", expanded=False):
        with st.form("yeni_gelecek_arz", clear_on_submit=True):
            cg1, cg2 = st.columns(2)
            g_kod = cg1.text_input("Hisse Kodu:").upper().strip()
            g_ad = cg2.text_input("Şirket Adı:")
            
            cg3, cg4, cg5 = st.columns(3)
            g_fiyat = cg3.number_input("Halka Arz Fiyatı (₺):", min_value=0.0, value=15.0, step=0.01, format="%.2f")
            g_talep = cg4.text_input("Talep Toplama Tarihi:")
            g_islem = cg5.text_input("İşlem Tarihi:")
            
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
            gkod = str(row['kod'])
            gad = str(row['ad'])
            gfiyat = safe_float(row['fiyat'])
            gtalep = str(row['talep_tarihi'])
            gislem = str(row['islem_tarihi'])

            with st.container(border=True):
                gc1, gc2, gc3 = st.columns([2, 2, 1])
                with gc1:
                    st.markdown(f"### {gkod}")
                    st.write(f"**{gad}**")
                    st.write(f"**Fiyat:** ₺{gfiyat:.2f}" if gfiyat > 0 else "**Fiyat:** Açıklanmadı")
                with gc2:
                    st.write(f"📅 **Talep Toplama:** {gtalep if gtalep else 'Açıklanmadı'}")
                    st.write(f"🔔 **İşlem Tarihi:** {gislem if gislem else 'Açıklanmadı'}")
                with gc3:
                    if st.button("🗑️ Sil", key=f"gdel_{idx}"):
                        gelecek_arz_sil(idx)
                        st.rerun()

# =========================================================
# TAB 4: BORÇ & KREDİ TAKİP
# =========================================================
with tab4:
    st.title("💳 Borç & Kredi Defteri")
    
    df_borc = verileri_getir("borclar")
    
    toplam_ana_borc = 0.0
    toplam_odenen_borc = 0.0
    
    if not df_borc.empty:
        for _, row in df_borc.iterrows():
            toplam_ana_borc += safe_float(row['toplam_tutar'])
            toplam_odenen_borc += safe_float(row['odenen_tutar'])
        
    kalan_toplam_borc = toplam_ana_borc - toplam_odenen_borc
    
    mc1, mc2, mc3 = st.columns(3)
    mc1.metric("Toplam Borç / Kredi", f"₺{toplam_ana_borc:,.2f}")
    mc2.metric("Ödenen Toplam Tutar", f"₺{toplam_odenen_borc:,.2f}")
    mc3.metric("Kalan Toplam Borç", f"₺{kalan_toplam_borc:,.2f}", f"-₺{kalan_toplam_borc:,.2f}", delta_color="inverse")
    
    st.divider()

    with st.expander("➕ Yeni Borç / Kredi Ekle", expanded=False):
        with st.form("yeni_borc_formu", clear_on_submit=True):
            b_tur = st.radio("Tür Seçin:", ["Bankadan Kredi", "Kişisel Borç"], horizontal=True)
            b_baslik = st.text_input("Başlık (Örn: İhtiyaç Kredisi):")
            b_kisi = st.text_input("Banka / Kişi Adı:")
            
            col_b1, col_b2 = st.columns(2)
            b_tutar = col_b1.number_input("Toplam Borç Tutarı (₺):", min_value=1.0, value=25000.0, step=500.0)
            
            b_taksit = col_b2.number_input("Taksit Sayısı (Ay):", min_value=1, value=2, step=1) if "Kredi" in b_tur else 1
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
            baslik = str(row['baslik'])
            tur = str(row['tur'])
            kisi = str(row['kisi_kurum'])
            toplam = safe_float(row['toplam_tutar'])
            taksit_s = int(safe_float(row['taksit_sayisi'], 1))
            odenen_taksit = int(safe_float(row['odenen_taksit'], 0))
            odenen_tutar = safe_float(row['odenen_tutar'])
            aciklama = str(row['aciklama'])
            
            kalan = toplam - odenen_tutar
            taksit_tutari = toplam / taksit_s if taksit_s > 0 else toplam
            
            with st.container(border=True):
                c1, c2, c3 = st.columns([2, 2, 1])
                with c1:
                    st.markdown(f"### {baslik}")
                    st.write(f"**Alacaklı/Kurum:** {kisi}")
                    if aciklama and aciklama.lower() != "nan":
                        st.caption(f"📝 Not: {aciklama}")
                with c2:
                    st.write(f"**Toplam:** ₺{toplam:,.2f} | **Ödenen:** ₺{odenen_tutar:,.2f}")
                    st.markdown(f"**Kalan Borç:** <span style='color:#ef4444; font-weight:bold;'>₺{kalan:,.2f}</span>", unsafe_allow_html=True)
                    ilerleme = min(odenen_tutar / toplam, 1.0) if toplam > 0 else 0
                    st.progress(ilerleme, text=f"%{ilerleme*100:.0f} Ödendi")
                with c3:
                    if tur == 'Kredi':
                        st.write(f"**Taksit:** {odenen_taksit}/{taksit_s} Ay")
                        if odenen_taksit < taksit_s and kalan > 0:
                            if st.button(f"☑️ Taksit Öde", key=f"taksit_{idx}"):
                                taksit_artir(idx, odenen_taksit, taksit_tutari)
                                st.rerun()
                    else:
                        if kalan > 0:
                            odenecek = st.number_input("Tutar (₺):", min_value=1.0, max_value=float(kalan), value=float(kalan), key=f"input_p_{idx}")
                            if st.button("💵 Öde", key=f"pay_{idx}"):
                                borc_odeme_yap(idx, odenecek)
                                st.rerun()
                    if st.button("🗑️ Sil", key=f"del_b_{idx}"):
                        borc_sil(idx)
                        st.rerun()

    # GENEL SERVET ÖZETİ
    st.divider()
    st.subheader("⚖️ Cebindeki Tam Net Servet & Denge")
    toplam_toplam_varliklar = toplam_guncel_aktif + gerceklesen_kar + toplam_boştaki_nakit_tl
    net_varlik = toplam_toplam_varliklar - kalan_toplam_borc
    
    st.info(f"""
    * 📈 **Aktif Borsa Portföy Değeri:** ₺{toplam_guncel_aktif:,.2f}
    * 💵 **Hesaplardaki Boştaki Nakitler:** ₺{toplam_boştaki_nakit_tl:,.2f}
    * 💰 **Satıştan Cebine Giren Kâr:** ₺{gerceklesen_kar:,.2f}
    * 💳 **Kalan Toplam Borçlar:** ₺{kalan_toplam_borc:,.2f}
    """)
    
    if net_varlik >= 0:
        st.success(f"💚 **NET SERVETİN:** **+₺{net_varlik:,.2f}**")
    else:
        st.error(f"🔴 **NET SERVET AÇIĞIN:** **-₺{abs(net_varlik):,.2f}**")
