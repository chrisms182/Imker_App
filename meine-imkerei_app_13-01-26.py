import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

# --- 1. KONFIGURATION & INITIALISIERUNG ---
st.set_page_config(page_title="Imker-Analyse", layout="wide")

# Speicher-Variablen
if 'storage_voelker' not in st.session_state:
    st.session_state.storage_voelker = []
if 'storage_chart' not in st.session_state:
    st.session_state.storage_chart = "Linien-Diagramm" 
if 'storage_zeit' not in st.session_state:
    st.session_state.storage_zeit = "Dieses Jahr"   
if 'storage_metrik' not in st.session_state:
    st.session_state.storage_metrik = "Gewicht"        

# --- CALLBACKS ---
def save_chart_change():
    st.session_state.storage_chart = st.session_state.widget_chart_key

def save_zeit_change():
    st.session_state.storage_zeit = st.session_state.widget_zeit_key

# --- 2. HEADER & DATEI-UPLOAD ---
col1, col2 = st.columns([2, 1], vertical_alignment="bottom")
with col1:
    st.title("Meine Völker - Auswertung")
    uploaded_file = st.file_uploader("Neue KIM-CSV Datei hochladen", type=["csv"])
    
    DEFAULT_FILE = "daten.csv"
    file_to_load = None
    
    if uploaded_file:
        file_to_load = uploaded_file
        st.info(f"ℹ️ Datei: {uploaded_file.name}")
    elif os.path.exists(DEFAULT_FILE):
        file_to_load = DEFAULT_FILE
        ts = os.path.getmtime(DEFAULT_FILE)
        st.success(f"✅ Basis-Daten geladen (Stand: {datetime.fromtimestamp(ts).strftime('%d.%m.%Y %H:%M')})")
    else:
        st.info("ℹ️ Bitte CSV hochladen.")

with col2:
    st.image("BienenLogo.jpg", use_container_width=True)

# --- 3. DATEN LADEN (ROBUST & INTELLIGENT V2) ---
if file_to_load:
    df = None
    erfolgreich_gelesen = False
    
    versuche = [(';', 'latin-1'), (',', 'latin-1'), (';', 'utf-8'), (',', 'utf-8')]
    
    for trenner, encoding in versuche:
        try:
            if hasattr(file_to_load, 'seek'): file_to_load.seek(0)
            temp_df = pd.read_csv(file_to_load, sep=trenner, encoding=encoding)
            if len(temp_df.columns) > 1:
                df = temp_df
                erfolgreich_gelesen = True
                break 
        except Exception:
            continue

    if erfolgreich_gelesen and df is not None:
        try:
            df.columns = df.columns.str.strip()
            rename_map = {}
            for col in df.columns:
                if "Milben" in col: rename_map[col] = "Milben"
                if "Besetzte Waben" in col: rename_map[col] = "Waben_besetzt"
            df = df.rename(columns=rename_map)
            
            if 'Datum des Eintrags' not in df.columns:
                st.error(f"❌ Fehler: Spalte 'Datum des Eintrags' fehlt.")
                st.stop()

            df['Datum des Eintrags'] = pd.to_datetime(df['Datum des Eintrags'], dayfirst=True, errors='coerce')
            df = df.dropna(subset=['Datum des Eintrags', 'Stockname'])
            
        except Exception as e:
            st.error(f"❌ Fehler bei der Verarbeitung: {e}")
            st.stop()
    else:
        st.error("❌ Die Datei konnte nicht gelesen werden.")
        st.stop()
else:
    st.stop()

# --- 4. VÖLKERAUSWAHL ---
st.write("### Schnellzugriff Völker")
alle_voelker = sorted(df['Stockname'].unique())
cols = st.columns(10)

for i, volk_name in enumerate(alle_voelker):
    with cols[i % 10]:
        ist_aktiv = (st.session_state.storage_voelker == [volk_name])
        st.image("VolkLogo.jpg", use_container_width=True)
        if st.button(volk_name, key=f"btn_{volk_name}", use_container_width=True, type="primary" if ist_aktiv else "secondary"):
            st.session_state.storage_voelker = [] if ist_aktiv else [volk_name]
            st.rerun()

# --- 5. ANALYSE BEREICH ---
if st.session_state.storage_voelker:
    gewaehltes_volk = st.session_state.storage_voelker[0]
    st.markdown("""
        <hr style='margin: 5px 0; border: none; border-top: 1px solid rgba(255,255,255,0.2);'>
    """, unsafe_allow_html=True)


    # --- METRIK BUTTONS ---
    metriken = {"Gewicht": "Gewicht", "Zunahme/Abnahme": "Gewicht_Diff", "Varroa": "Milben", "Volksstärke": "Waben_besetzt"}
    m_cols = st.columns(4)
    for i, label in enumerate(metriken.keys()):
        aktiv = (st.session_state.storage_metrik == label)
        if m_cols[i].button(label, key=f"m_{label}", use_container_width=True, type="primary" if aktiv else "secondary"):
            st.session_state.storage_metrik = label
            st.rerun()

    # --- OPTIONEN & GRAPH ---
    opt_col1, opt_col2 = st.columns([1, 3])

    with opt_col1:
        st.write("#### ⚙️ Optionen")
        
        z_opts = [
            "Alles anzeigen", "Dieses Jahr", "Letzte 6 Monate", 
            "Letzte 3 Monate", "Letzte 30 Tage", "Letzte 14 Tage", "Letzte 7 Tage"
        ]
        try: z_index = z_opts.index(st.session_state.storage_zeit)
        except ValueError: z_index = 0
            
        st.radio("Zeitraum auswählen:", z_opts, index=z_index, key="widget_zeit_key", on_change=save_zeit_change)
        
        c_opts = ["Linien-Diagramm", "Balkendiagramm"]
        try: c_index = c_opts.index(st.session_state.storage_chart)
        except ValueError: c_index = 0
            
        st.radio("Diagramm-Typ:", c_opts, index=c_index, key="widget_chart_key", on_change=save_chart_change)

    with opt_col2:
        # Daten filtern
        volk_df = df[df['Stockname'] == gewaehltes_volk].copy().sort_values("Datum des Eintrags")
        heute = pd.Timestamp.now().normalize()

        auswahl = st.session_state.storage_zeit
        if auswahl == "Dieses Jahr":
            volk_df = volk_df[volk_df['Datum des Eintrags'].dt.year == heute.year]
        elif auswahl == "Letzte 6 Monate":
            volk_df = volk_df[volk_df['Datum des Eintrags'] >= (heute - pd.Timedelta(days=180))]
        elif auswahl == "Letzte 3 Monate":
            volk_df = volk_df[volk_df['Datum des Eintrags'] >= (heute - pd.Timedelta(days=90))]
        elif auswahl == "Letzte 30 Tage":
            volk_df = volk_df[volk_df['Datum des Eintrags'] >= (heute - pd.Timedelta(days=30))]
        elif auswahl == "Letzte 14 Tage":
            volk_df = volk_df[volk_df['Datum des Eintrags'] >= (heute - pd.Timedelta(days=14))]
        elif auswahl == "Letzte 7 Tage":
            volk_df = volk_df[volk_df['Datum des Eintrags'] >= (heute - pd.Timedelta(days=7))]

        # Y-Achse bestimmen
        y_spalte = "Gewicht"
        metrik = st.session_state.storage_metrik
        
        if metrik == "Zunahme/Abnahme":
            volk_df['Gewicht_Diff'] = volk_df['Gewicht'].diff()
            y_spalte = "Gewicht_Diff"
        elif metrik == "Varroa":
            y_spalte = "Milben"
        elif metrik == "Volksstärke":
            y_spalte = "Waben_besetzt"

        plot_df = volk_df.dropna(subset=[y_spalte])

        # Plotten
        if not plot_df.empty:
            chart_typ = st.session_state.storage_chart
            
            # --- STYLING VARIIABLEN ---
            # HIER IST DIE ÄNDERUNG:
            # Wir haben die Breite von 20 Stunden auf 36 Stunden erhöht (1.5 Tage)
            # Das macht die Balken fast doppelt so dick.
            balken_breite = 1000 * 60 * 60 * 36 

            if chart_typ == "Linien-Diagramm":
                fig = px.line(plot_df, x='Datum des Eintrags', y=y_spalte, template="plotly_dark", markers=True)
                fig.update_traces(
                    line=dict(color='#FFC107', width=3),
                    marker=dict(size=8, color='#FFC107', line=dict(width=1, color='white')),
                    fill='tozeroy', 
                    fillcolor='rgba(255, 193, 7, 0.1)'
                )
            else:
                fig = px.bar(plot_df, x='Datum des Eintrags', y=y_spalte, template="plotly_dark")
                
                # Farbenlogik
                if metrik == "Zunahme/Abnahme":
                    farben = ['#2ECC71' if x >= 0 else '#E74C3C' for x in plot_df[y_spalte]]
                    fig.update_traces(marker_color=farben, marker_line_width=0, width=balken_breite)
                else:
                    fig.update_traces(marker_color='#FFC107', marker_line_width=0, width=balken_breite)

            fig.update_layout(
                xaxis=dict(title="Datum", showgrid=False, zeroline=False),
                yaxis=dict(title=metrik, gridcolor="rgba(255,255,255,0.1)", zerolinecolor="rgba(255,255,255,0.2)"),
                plot_bgcolor="rgba(0,0,0,0)", 
                paper_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified",
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"💡 Keine Daten für **'{metrik}'** im gewählten Zeitraum.")
else:
    st.info("👆 Bitte wähle oben ein Volk aus.")

