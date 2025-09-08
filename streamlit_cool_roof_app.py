
import math
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px

st.set_page_config(page_title="Kalkulator Dachu Chłodnego", page_icon="🧊", layout="wide")

# ---------- THEME & HEADER ----------
st.title("🧊 Kalkulator Dachu Chłodnego — przyjazny dla klienta (PL)")
st.caption("Na bazie właściwości Twojej powłoki: TSR = 88%, emisyjność ε = 0.902, SRI = 111")

with st.expander("ℹ️ O aplikacji"):
    st.markdown("""
    Ten kalkulator pokazuje roczne i 20–letnie **oszczędności energii elektrycznej, kosztów i emisji CO₂**
    dzięki zastosowaniu **chłodnego dachu** (TSR 88%, ε 0.902, SRI 111) w porównaniu do ciemnego dachu.
    
    **Jak to działa?**
    - Stała oszczędność chłodu: **5 833 Btu/ft²·rok** (na podstawie podanych właściwości powłoki).
    - Przeliczamy ją na energię elektryczną w kWh na podstawie sprawności klimatyzacji (EER).
    - Wyniki skalujemy do powierzchni dachu i kosztów energii.
    """)

# ---------- SIDEBAR: INPUTS ----------
st.sidebar.header("Wejście")

# Defaults (Poland-friendly)
default_price = 0.85   # PLN/kWh
default_ef = 0.77      # kg CO2/kWh

area_m2 = st.sidebar.number_input("Powierzchnia dachu (m²)", min_value=10.0, value=1000.0, step=10.0)
roof_type = st.sidebar.selectbox("Rodzaj dachu", ["Blacha (metal)", "Beton", "Papa/bitum"], index=0,
                                 help="Typ przegrody wpływa na dynamikę nagrzewania. W kalkulatorze działa jako delikatny współczynnik korygujący.")

ac_band = st.sidebar.selectbox("Efektywność klimatyzacji (przedział)", ["Stary", "Standard", "Wysoka sprawność"], index=1,
                               help="Wybierz przybliżony przedział jeśli nie znasz parametrów urządzenia.")
custom_eer_on = st.sidebar.checkbox("Podaj własny EER", value=False)
if custom_eer_on:
    eer = st.sidebar.number_input("EER (Energy Efficiency Ratio)", min_value=5.0, value=11.0, step=0.5,
                                  help="EER = Btu/h na 1 Watt. COP ≈ EER / 3.412")
else:
    if ac_band == "Stary":
        eer = 9.0
    elif ac_band == "Standard":
        eer = 11.0
    else:
        eer = 13.0

price_pln = st.sidebar.number_input("Cena energii (zł/kWh)", min_value=0.0, value=default_price, step=0.05)
ef_kg_per_kwh = st.sidebar.number_input("Współczynnik emisji CO₂ (kg/kWh)", min_value=0.0, value=default_ef, step=0.01,
                                        help="Średnio w PL ~0.77 kg/kWh (PSE/KOBiZE). Możesz wpisać własną wartość.")

st.sidebar.markdown("---")
st.sidebar.subheader("Założenia techniczne")
st.sidebar.markdown("""
- **TSR** = 88% (bardzo wysoka refleksyjność)
- **Emisyjność** ε = 0.902 (wysoka)
- **SRI** = 111 (wyjątkowo chłodna powierzchnia)
- **Redukcja chłodu**: 5 833 Btu/ft²·rok
""")

# ---------- HEURISTIC ROOF TYPE MULTIPLIER ----------
# Small modifiers to reflect different roof dynamics (heuristic)
roof_multipliers = {
    "Blacha (metal)": 1.00,
    "Beton": 0.95,          # thermal mass dampens peak benefit a bit annually
    "Papa/bitum": 1.05      # very dark/absorptive baseline -> slightly higher relative benefit
}
roof_mult = roof_multipliers[roof_type]

# ---------- CORE CALCULATIONS ----------
FT2_PER_M2 = 10.7639
BTU_TO_J = 1055.06

area_ft2 = area_m2 * FT2_PER_M2
reduction_btu_per_ft2 = 5833.0 * roof_mult   # adjusted by roof type
total_reduction_btu = area_ft2 * reduction_btu_per_ft2

# Electricity savings from thermal reduction via EER
# kWh = (Btu / (EER * 1000))
kwh_saved = total_reduction_btu / (eer * 1000.0)

# Money and carbon
pln_saved = kwh_saved * price_pln
kg_co2_saved = kwh_saved * ef_kg_per_kwh
t_co2_saved = kg_co2_saved / 1000.0

# GJ (thermal) for info
gj_saved = (total_reduction_btu * BTU_TO_J) / 1e9

# Friendly equivalents
KG_PER_TREE_PER_YEAR = 22.0   # kg CO2 per tree per year
KG_PER_CAR_KM = 0.2           # kg CO2 per car-km

trees_eq = kg_co2_saved / KG_PER_TREE_PER_YEAR if KG_PER_TREE_PER_YEAR > 0 else 0
km_eq = kg_co2_saved / KG_PER_CAR_KM if KG_PER_CAR_KM > 0 else 0

# 20-year projections (no discounting/degradation here; can be made configurable)
years = np.arange(1, 21)
kwh_yearly = np.full_like(years, kwh_saved, dtype=float)
pln_yearly = np.full_like(years, pln_saved, dtype=float)
tco2_yearly = np.full_like(years, t_co2_saved, dtype=float)

kwh_cum = np.cumsum(kwh_yearly)
pln_cum = np.cumsum(pln_yearly)
tco2_cum = np.cumsum(tco2_yearly)

# ---------- TOP KPIs ----------
col1, col2, col3, col4 = st.columns(4)
col1.metric("Roczna oszczędność energii", f"{kwh_saved:,.0f} kWh")
col2.metric("Roczna oszczędność kosztów", f"{pln_saved:,.0f} zł")
col3.metric("Roczna redukcja CO₂", f"{kg_co2_saved:,.0f} kg")
col4.metric("Redukcja chłodu", f"{gj_saved:,.2f} GJ/rok")

# ---------- DETAILS TABLE ----------
st.subheader("Szczegóły obliczeń")
df = pd.DataFrame({
    "Parametr": [
        "Powierzchnia dachu", "Rodzaj dachu", "EER (efektywność)",
        "Cena energii", "Wsp. emisji CO₂", "Redukcja chłodu (Btu/ft²·rok)",
        "Redukcja chłodu (GJ/rok)", "Oszczędność energii (kWh/rok)",
        "Oszczędność kosztów (zł/rok)", "Redukcja CO₂ (kg/rok)", "Redukcja CO₂ (t/rok)",
        "Ekwiwalent drzew (szt./rok)", "Ekwiwalent km samochodem (km/rok)"
    ],
    "Wartość": [
        f"{area_m2:,.0f} m²", roof_type, f"{eer:.1f}",
        f"{price_pln:.2f} zł/kWh", f"{ef_kg_per_kwh:.2f} kg/kWh", f"{reduction_btu_per_ft2:,.0f}",
        f"{gj_saved:,.2f}", f"{kwh_saved:,.0f}", f"{pln_saved:,.0f}", f"{kg_co2_saved:,.0f}", f"{t_co2_saved:,.2f}",
        f"{trees_eq:,.0f}", f"{km_eq:,.0f}"
    ]
})
st.dataframe(df, use_container_width=True)

# ---------- CHARTS ----------
st.markdown("### 📈 20‑letnie oszczędności — kumulacja")

df_cum = pd.DataFrame({
    "Rok": years,
    "Energia (kWh)": kwh_cum,
    "Koszty (zł)": pln_cum,
    "CO₂ (t)": tco2_cum
})
fig1 = px.line(df_cum, x="Rok", y=["Energia (kWh)", "Koszty (zł)", "CO₂ (t)"],
               markers=True, title="Kumulatywne oszczędności w czasie")
st.plotly_chart(fig1, use_container_width=True)

st.markdown("### 📊 Ekwiwalenty środowiskowe (roczne)")
df_eq = pd.DataFrame({
    "Ekwiwalent": ["Posadzone drzewa (szt./rok)", "Uniknięte km samochodem (km/rok)"],
    "Wartość": [trees_eq, km_eq]
})
fig2 = px.bar(df_eq, x="Ekwiwalent", y="Wartość", text="Wartość", title="Łatwe porównanie dla klienta")
fig2.update_traces(texttemplate="%{text:.0f}", textposition="outside")
st.plotly_chart(fig2, use_container_width=True)

# ---------- PAYBACK (OPTIONAL) ----------
st.markdown("### 💰 Opcjonalnie: czas zwrotu (payback)")
cost_on = st.checkbox("Włącz obliczanie czasu zwrotu (podaj koszt powłoki)")
if cost_on:
    unit_cost = st.number_input("Koszt powłoki (zł/m²)", min_value=0.0, value=50.0, step=5.0)
    capex = unit_cost * area_m2
    if pln_saved > 0:
        payback_years = capex / pln_saved
        st.info(f"Szacowany prosty czas zwrotu: **{payback_years:,.1f} lat** (CAPEX {capex:,.0f} zł / {pln_saved:,.0f} zł/rok)")
    else:
        st.warning("Brak oszczędności kosztowych — nie można policzyć zwrotu.")

# ---------- DOWNLOADS ----------
st.markdown("---")
st.subheader("Pobierz wyniki")
# Export a one-row summary CSV
summary = pd.DataFrame([{
    "Powierzchnia_m2": area_m2,
    "Rodzaj_dachu": roof_type,
    "EER": eer,
    "Cena_energii_PLN_kWh": price_pln,
    "EF_kgCO2_kWh": ef_kg_per_kwh,
    "kWh_rok": kwh_saved,
    "PLN_rok": pln_saved,
    "tCO2_rok": t_co2_saved,
    "kWh_20lat": kwh_cum[-1],
    "PLN_20lat": pln_cum[-1],
    "tCO2_20lat": tco2_cum[-1],
}])

st.download_button("Pobierz podsumowanie (CSV)", summary.to_csv(index=False).encode("utf-8"), "kalkulator_dachu_podsumowanie.csv", "text/csv")

with st.expander("📘 Słowniczek pojęć"):
    st.markdown("""
    - **TSR (Total Solar Reflectance)** — procent promieniowania słonecznego odbijanego przez powierzchnię. Im wyższy, tym chłodniejszy dach.
    - **Emisyjność (ε)** — zdolność powierzchni do oddawania ciepła w podczerwieni. Wysoka emisyjność pomaga szybciej się schładzać.
    - **SRI (Solar Reflectance Index)** — łączy TSR i emisyjność; porównuje jak gorąca będzie powierzchnia w słońcu vs. standard.
    - **EER (Energy Efficiency Ratio)** — stosunek chłodu (Btu/h) do mocy (W). **Większy EER = niższy pobór energii**. (COP ≈ EER/3.412)
    - **Współczynnik emisji CO₂** — ile CO₂ powstaje przy wytworzeniu 1 kWh prądu (kg/kWh).
    - **GJ** — gigadżul, jednostka energii (1 GJ = 277.78 kWh).
    """)
