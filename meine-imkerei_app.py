import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re
from datetime import datetime

# 1. SETUP
st.set_page_config(page_title="Imker-Analyse", layout="wide")

# CSS
st.markdown("""
<style>
div[data-testid="stDownloadButton"] button {
    min-height: 64px !important;
    height: 64px !important;
    border-radius: 8px !important;
    border: 1px solid rgba(250, 250, 250, 0.2);
}
</style>
""", unsafe_allow_html=True)

# --- SPEICHER (State Management) ---
if 'storage_voelker' not in st.session_state: st.session_state.storage_voelker = []
if 'storage_chart' not in st.session_state: st.session_state.storage_chart = "Liniendiagramm" 
if 'storage_zeit' not in st.session_state: st.session_state.storage_zeit = "Letzte 6 Monate"   
if 'storage_metrik' not in st.session_state: st.session_state.storage_metrik = "Gewicht"        
# Standards
if 'storage_stauchung' not in st.session_state: st.session_state.storage_stauchung = True 
if 'storage_zeros' not in st.session_state: st.session_state.storage_zeros = False          

# 🟢 NEUE FARB-PALETTE (Maximaler Kontrast)
FARB_POOL = [
    ('#E6194B', '🔴'), ('#3CB44B', '🟢'), ('#FFE119', '🟡'), ('#4363D8', '🔵'), 
    ('#F58231', '🟠'), ('#911EB4', '🟣'), ('#42D4F4', '💧'), ('#F032E6', '🌸'), 
    ('#BFEF45', '🍏'), ('#A9A9A9', '🐘')
]

# Helper
def save_chart_change(): st.session_state.storage_chart = st.session_state.widget_chart_key
def save_zeit_change(): st.session_state.storage_zeit = st.session_state.widget_zeit_key
def save_stauchung_change(): st.session_state.storage_stauchung = st.session_state.widget_stauchung_key
def save_zeros_change(): st.session_state.storage_zeros = st.session_state.widget_zeros_key
def natural_sort_key(s): return [int(text) if text.isdigit() else text.lower() for text in re.split('([0-9]+)', str(s))]

# --- 2. HEADER ---
head_col1, head_col2 = st.columns([2, 1], vertical_alignment="bottom")
download_placeholder = None

with head_col1:
    st.title("Meine Völker - Auswertung")
    up_col, dl_col = st.columns([0.8, 0.2], vertical_alignment="bottom")
    
    with up_col:
        uploaded_file = st.file_uploader("KIM-CSV Datei hochladen", type=["csv"])
    
    with dl_col:
        download_placeholder = st.empty()
    
    DEFAULT_FILE = "daten.csv"
    file_to_load = None
    
    if uploaded_file:
        file_to_load = uploaded_file
        st.success(f"✅ Datei geladen: {uploaded_file.name}")
    elif os.path.exists(DEFAULT_FILE):
        file_to_load = DEFAULT_FILE
        st.success(f"✅ Basis-Daten geladen")
    else:
        st.info("ℹ️ Bitte CSV hochladen.")

with head_col2:
    st.image("BienenLogo.jpg", use_container_width=True) 
    pass

# --- 3. LOGIK ---
if file_to_load:
    df = None
    try:
        if hasattr(file_to_load, 'seek'): file_to_load.seek(0)
        
        try:
            df = pd.read_csv(file_to_load, sep=',', encoding='latin-1')
            if len(df.columns) < 2: raise Exception("Falscher Trenner")
        except:
            if hasattr(file_to_load, 'seek'): file_to_load.seek(0)
            df = pd.read_csv(file_to_load, sep=';', encoding='latin-1')

        df.columns = df.columns.str.strip()
        
        # 🟢 1. REINIGUNG & UMBENENNUNG
        rename_map = {}
        erkannte_futter_spalte = "Keine Spalte gefunden"
        
        for col in df.columns:
            if "hlte" in col and "Milben" in col: 
                rename_map[col] = "Milben_Count"
            if "hlzeitraum"in col and "Tage" in col:
                rename_map[col] = "Milben_Days"

            # 🔴 NEUE LOGIK: Suche exakt nach "Futtermenge", ignoriere "Bewertung"
            c_low = col.lower()
            if "futtermenge" in c_low and "bewertung" not in c_low:
                rename_map[col] = "Futtermenge_Clean"
                erkannte_futter_spalte = col
                        
        df = df.rename(columns=rename_map)
        df = df.loc[:, ~df.columns.duplicated()]

        # Feedback für dich
        if erkannte_futter_spalte != "Keine Spalte gefunden":
            st.info(f"🔍 Info: Original-Spalte **'{erkannte_futter_spalte}'** wird für die Futtermenge verwendet.")
        else:
            st.warning("⚠️ Konnte die Spalte 'Futtermenge' nicht finden. Überprüfe die CSV-Datei.")

        # Sicherstellen, dass Futtermenge eine Zahl ist (z.B. '2,5' -> 2.5)
        if 'Futtermenge_Clean' in df.columns:
            df['Futtermenge_Clean'] = df['Futtermenge_Clean'].astype(str).str.replace(',', '.', regex=False)
            df['Futtermenge_Clean'] = pd.to_numeric(df['Futtermenge_Clean'], errors='coerce')

        # 🟢 2. VARROA BERECHNUNG (Milben / Tage)
        if 'Milben_Count' in df.columns and 'Milben_Days' in df.columns:
            c = pd.to_numeric(df['Milben_Count'], errors='coerce')
            d = pd.to_numeric(df['Milben_Days'], errors='coerce').fillna(1).replace(0, 1) 
            df['Milben'] = c / d
            
        if 'Datum des Eintrags' not in df.columns:
            st.error(f"❌ Spalte 'Datum des Eintrags' fehlt.")
            st.stop()

        df['Datum des Eintrags'] = pd.to_datetime(df['Datum des Eintrags'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Datum des Eintrags', 'Stockname'])
        
        csv_daten = df.to_csv(index=False, sep=';', encoding='latin-1', errors='replace')
        heute_str = datetime.now().strftime('%Y-%m-%d')
        
        download_placeholder.download_button(
            label="💾 Für Excel Speichern", 
            data=csv_daten, file_name=f"KIM_Daten_{heute_str}.csv",
            mime="text/csv", use_container_width=True, type="secondary"
        )
        
    except Exception as e:
        st.error(f"❌ Fehler: {e}")
        st.stop()
else:
    st.stop()

# --- 4. VÖLKERAUSWAHL ---
st.write("### Schnellzugriff Völker")
alle_voelker = sorted(df['Stockname'].unique(), key=natural_sort_key)

c_all, c_none, c_dummy = st.columns([0.2, 0.2, 0.6])
with c_all:
    if st.button("✅ Alle auswählen", use_container_width=True):
        st.session_state.storage_voelker = list(alle_voelker)
        st.rerun()
with c_none:
    if st.button("❌ Auswahl leeren", use_container_width=True):
        st.session_state.storage_voelker = []
        st.rerun()

active_color_map = {}
active_emoji_map = {}
for idx, v_name in enumerate(st.session_state.storage_voelker):
    farb_code, icon = FARB_POOL[idx % len(FARB_POOL)]
    active_color_map[v_name] = farb_code
    active_emoji_map[v_name] = icon

cols = st.columns(10)
for i, volk_name in enumerate(alle_voelker):
    with cols[i % 10]:
        ist_aktiv = (volk_name in st.session_state.storage_voelker)
        st.image("VolkLogo.jpg", use_container_width=True)
        label = f"{active_emoji_map[volk_name]} {volk_name}" if ist_aktiv else volk_name
        if st.button(label, key=f"btn_{volk_name}", use_container_width=True, type="primary" if ist_aktiv else "secondary"):
            if ist_aktiv: st.session_state.storage_voelker.remove(volk_name)
            else: st.session_state.storage_voelker.append(volk_name)
            st.rerun()

# --- 5. ANALYSE ---
if st.session_state.storage_voelker:
    st.markdown("<hr style='margin: 5px 0; border: none; border-top: 1px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    
    metriken = {"Gewicht": "Gewicht", "Zunahme/Abnahme": "Gewicht_Diff", "Varroa (Milben/Tag)": "Milben", "Futtermenge (kg)": "Futtermenge_Clean"}
    
    m_cols = st.columns(4)
    for i, label in enumerate(metriken.keys()):
        aktiv = (st.session_state.storage_metrik == label)
        if m_cols[i].button(label, key=f"m_{label}", use_container_width=True, type="primary" if aktiv else "secondary"):
            st.session_state.storage_metrik = label
            st.rerun()

    opt_col1, opt_col2 = st.columns([1, 4])
    
    with opt_col1:
        st.write("#### ⚙️ Optionen")
        
        verfuegbare_jahre = sorted(df['Datum des Eintrags'].dt.year.unique(), reverse=True)
        jahre_str = [str(j) for j in verfuegbare_jahre]
        
        standard_opts = ["Alles anzeigen", "Letzte 6 Monate", "Letzte 3 Monate", "Letzte 30 Tage", "Letzte 14 Tage", "Letzte 7 Tage"]
        alle_optionen = standard_opts + jahre_str
        
        try: z_index = alle_optionen.index(st.session_state.storage_zeit)
        except: z_index = 1 
        st.radio("Zeitraum:", alle_optionen, index=z_index, key="widget_zeit_key", on_change=save_zeit_change)
        
        c_opts = ["Liniendiagramm", "Balkendiagramm"]
        try: c_index = c_opts.index(st.session_state.storage_chart)
        except: c_index = 0
        st.radio("Typ:", c_opts, index=c_index, key="widget_chart_key", on_change=save_chart_change)
        
        st.write("---")
        st.checkbox("Leere Werte als '0' anzeigen", value=st.session_state.storage_zeros, key="widget_zeros_key", on_change=save_zeros_change)
        st.checkbox("Zeitleiste stauchen", value=st.session_state.storage_stauchung, key="widget_stauchung_key", on_change=save_stauchung_change)

    with opt_col2:
        aktuelle_voelker = st.session_state.storage_voelker
        plot_df = df[df['Stockname'].isin(aktuelle_voelker)].copy().sort_values("Datum des Eintrags")
        heute = pd.Timestamp.now().normalize()

        days_map = {"Letzte 7 Tage": 7, "Letzte 14 Tage": 14, "Letzte 30 Tage": 30, "Letzte 3 Monate": 90, "Letzte 6 Monate": 180}
        auswahl = st.session_state.storage_zeit
        
        start_date = None
        end_date = heute + pd.Timedelta(days=1) 

        if auswahl in days_map:
            start_date = heute - pd.Timedelta(days=days_map[auswahl])
            plot_df = plot_df[plot_df['Datum des Eintrags'] >= start_date]
        elif auswahl.isdigit(): 
            wahl_jahr = int(auswahl)
            start_date = pd.Timestamp(year=wahl_jahr, month=1, day=1)
            end_date = pd.Timestamp(year=wahl_jahr, month=12, day=31)
            plot_df = plot_df[plot_df['Datum des Eintrags'].dt.year == wahl_jahr]

        y_spalte = "Gewicht"
        metrik = st.session_state.storage_metrik
        
        if metrik == "Zunahme/Abnahme":
            plot_df['Gewicht_Diff'] = plot_df.groupby('Stockname')['Gewicht'].diff()
            y_spalte = "Gewicht_Diff"
            if st.session_state.storage_zeros: plot_df[y_spalte] = plot_df[y_spalte].fillna(0)
            
        elif metrik == "Varroa (Milben/Tag)": 
            y_spalte = "Milben"
            if st.session_state.storage_zeros: plot_df[y_spalte] = plot_df[y_spalte].fillna(0)
            
        elif metrik == "Futtermenge (kg)": 
            y_spalte = "Futtermenge_Clean"
            if y_spalte in plot_df.columns and st.session_state.storage_zeros:
                plot_df[y_spalte] = plot_df[y_spalte].fillna(0)

        if y_spalte in plot_df.columns:
            plot_df = plot_df.dropna(subset=[y_spalte])

        if not plot_df.empty and y_spalte in plot_df.columns:
            sortierte_voelker = sorted(plot_df['Stockname'].unique(), key=natural_sort_key)
            plot_df['Stockname'] = pd.Categorical(plot_df['Stockname'], categories=sortierte_voelker, ordered=True)
            plot_df = plot_df.sort_values(by=['Datum des Eintrags', 'Stockname'])

            if not st.session_state.storage_stauchung:
                if st.session_state.storage_chart == "Liniendiagramm":
                    fig = px.line(plot_df, x='Datum des Eintrags', y=y_spalte, color='Stockname', 
                                  color_discrete_map=active_color_map, template="plotly_dark", markers=True,
                                  category_orders={'Stockname': sortierte_voelker})
                    fig.update_traces(line=dict(width=3), marker=dict(size=8, line=dict(width=1, color='white')))
                else:
                    fig = px.bar(plot_df, x='Datum des Eintrags', y=y_spalte, color='Stockname', 
                                 color_discrete_map=active_color_map, barmode='group', template="plotly_dark",
                                 category_orders={'Stockname': sortierte_voelker})
                
                x_axis_config = dict(title=None, showgrid=False, zeroline=False, ticklabelmode="period", dtick="M1", tickformat="%b %y")
                if start_date: x_axis_config['range'] = [start_date, end_date]

            else:
                plot_df['Datum_Label'] = plot_df['Datum des Eintrags'].dt.strftime('%d.%m.%y')
                sorted_labels = plot_df['Datum_Label'].unique()
                
                if st.session_state.storage_chart == "Liniendiagramm":
                    fig = px.line(plot_df, x='Datum_Label', y=y_spalte, color='Stockname', 
                                  color_discrete_map=active_color_map, template="plotly_dark", markers=True,
                                  category_orders={'Stockname': sortierte_voelker})
                    fig.update_traces(line=dict(width=3), marker=dict(size=8, line=dict(width=1, color='white')))
                else:
                    fig = px.bar(plot_df, x='Datum_Label', y=y_spalte, color='Stockname', 
                                 color_discrete_map=active_color_map, barmode='group', template="plotly_dark",
                                 category_orders={'Stockname': sortierte_voelker})
                
                x_axis_config = dict(title=None, showgrid=False, type='category', categoryorder='array', categoryarray=sorted_labels)

            y_axis_config = dict(title=metrik, gridcolor="rgba(255,255,255,0.1)")
            fig.update_layout(xaxis=x_axis_config, yaxis=y_axis_config, plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None))
            st.plotly_chart(fig, use_container_width=True)
        else:
            if y_spalte not in plot_df.columns:
                 st.error(f"⚠️ Spalte für Futtermenge nicht gefunden.")
            else:
                 st.info(f"💡 Keine Daten für **'{metrik}'** im gewählten Zeitraum.")
else:
    st.info("👆 Bitte wähle oben ein oder mehrere Völker aus.")
