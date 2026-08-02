import pandas as pd
import streamlit as st

# Sayfa Yapılandırması
st.set_page_config(
    page_title="Halka Arz Takip Sistemi", page_icon="📈", layout="wide"
)

st.title("📈 Halka Arz Takip ve Portföy Yönetimi")
st.caption("5 Hesaplık Toplam Takip Sistemi")

# Sabit Hesap Sayısı
HESAP_SAYISI = 5

# Veri Seti (İşlenen Geçmiş Veriler)
data = [
    {
        "Hisse": "EKDMR",
        "Alış Tarihi": "18.05.2026",
        "Tek Hesap Lot": 27,
        "Satış Tarihi": "02.06.2026",
        "Satış Fiyatı (TL)": 25.00,
    },
    {
        "Hisse": "ORZAX",
        "Alış Tarihi": "01.07.2026",
        "Tek Hesap Lot": 39,
        "Satış Tarihi": "07.07.2026",
        "Satış Fiyatı (TL)": 75.90,
    },
    {
        "Hisse": "BETAE",
        "Alış Tarihi": "30.06.2026",
        "Tek Hesap Lot": 29,
        "Satış Tarihi": "07.07.2026",
        "Satış Fiyatı (TL)": 64.35,
    },
    {
        "Hisse": "SOHOE",
        "Alış Tarihi": "03.07.2026",
        "Tek Hesap Lot": 15,
        "Satış Tarihi": "06.07.2026",
        "Satış Fiyatı (TL)": 16.50,
    },
    {
        "Hisse": "GOLDA",
        "Alış Tarihi": "06.07.2026",
        "Tek Hesap Lot": 130,
        "Satış Tarihi": "16.07.2026",
        "Satış Fiyatı (TL)": 16.28,
    },
    {
        "Hisse": "ISVEA",
        "Alış Tarihi": "03.07.2026",
        "Tek Hesap Lot": 47,
        "Satış Tarihi": "17.07.2026",
        "Satış Fiyatı (TL)": 22.52,
    },
    {
        "Hisse": "SSAAT",
        "Alış Tarihi": "08.07.2026",
        "Tek Hesap Lot": 72,
        "Satış Tarihi": "16.07.2026",
        "Satış Fiyatı (TL)": 52.70,
    },
    {
        "Hisse": "SARAE",
        "Alış Tarihi": "10.07.2026",
        "Tek Hesap Lot": 62,
        "Satış Tarihi": "22.07.2026",
        "Satış Fiyatı (TL)": 102.40,
    },
]

# DataFrame Oluşturma
df = pd.DataFrame(data)

# Hesaplamalar (5 Hesap için)
df["Toplam Lot (5 Hesap)"] = df["Tek Hesap Lot"] * HESAP_SAYISI
df["Toplam Hasılat (TL)"] = df["Toplam Lot (5 Hesap)"] * df["Satış Fiyatı (TL)"]

# Özet Metrikler (Üst Panel)
toplam_islem = len(df)
toplam_lot_sayisi = df["Toplam Lot (5 Hesap)"].sum()
toplam_ciro = df["Toplam Hasılat (TL)"].sum()

col1, col2, col3 = st.columns(3)
col1.metric("Toplam Halka Arz", f"{toplam_islem} Şirket")
col2.metric("Sattığın Toplam Lot", f"{toplam_lot_sayisi:,} Lot")
col3.metric("Toplam Brüt Hasılat", f"₺{toplam_ciro:,.2f}")

st.divider()

# Tablo Görünümü
st.subheader("📋 Halka Arz Detay Tablosu")

# Tabloyu Formatlama
formatted_df = df.copy()
formatted_df["Satış Fiyatı (TL)"] = formatted_df["Satış Fiyatı (TL)"].apply(
    lambda x: f"₺{x:.2f}"
)
formatted_df["Toplam Hasılat (TL)"] = formatted_df["Toplam Hasılat (TL)"].apply(
    lambda x: f"₺{x:,.2f}"
)

st.dataframe(formatted_df, use_container_width=True)

# Görsel Grafik (Hisse Başına Hasılat)
st.divider()
st.subheader("📊 Hisse Başına Kazandırılan Toplam Tutar")
st.bar_chart(df.set_index("Hisse")["Toplam Hasılat (TL)"])
