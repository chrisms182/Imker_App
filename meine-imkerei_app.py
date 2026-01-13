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
    st.session_state.storage_chart = "Balkendiagramm" 
if 'storage_zeit' not in st.session_state:
    st.session_state.storage_zeit = "Letzte 30 Tage"   
if 'storage_metrik' not in st.session_state:
    st.session_state.storage_metrik = "Gewicht"        

# --- NEU: FARBENBLIND-FREUNDLICHER POOL (Okabe-Ito Subset) ---
# Keine Rot/Grün-Konflikte. Perfekter Kontrast.
FARB_POOL = [
    ('#0072B2', '🔵'), # Blau (Stark)
    ('#E69F00', '🟠'), # Orange (Perfekter Kontrast zu Blau)
    ('#F0E442', '🟡'), # Gelb (Sehr gut sichtbar auf Dunkel)
    ('#CC79A7', '🟣'), # Rötliches Lila / Pink
    ('#56B4E9', '🧊'), # Himmelblau
]

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

# --- 3. DATEN LADEN ---
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

# --- 4. VÖLKERAUSWAHL (DYNAMISCHE FARBEN) ---
st.write("### Schnellzugriff Völker")
st.caption("Barrierefreie Farben: Blau, Orange, Gelb, Lila, Hellblau.")

alle_voelker = sorted(df['Stockname'].unique())

active_color_map = {}
active_emoji_map = {}

# Zuerst weisen wir den AKTIVEN Völkern ihre Farben zu
for idx, v_name in enumerate(st.session_state.storage_voelker):
    farb_code, icon = FARB_POOL[idx % len(FARB_POOL)]
    active_color_map[v_name] = farb_code
    active_emoji_map[v_name] = icon

cols = st.columns(10)

for i, volk_name in enumerate(alle_voelker):
    with cols[i % 10]:
        ist_aktiv = (volk_name in st.session_state.storage_voelker)
        st.image("VolkLogo.jpg", use_container_width=True)
        
        if ist_aktiv:
            button_label = f"{active_emoji_map[volk_name]} {volk_name}"
        else:
            button_label = volk_name
        
        if st.button(button_label, key=f"btn_{volk_name}", use_container_width=True, type="primary" if ist_aktiv else "secondary"):
            if ist_aktiv:
                st.session_state.storage_voelker.remove(volk_name)
            else:
                st.session_state.storage_voelker.append(volk_name)
            st.rerun()

# --- 5. ANALYSE BEREICH ---
if st.session_state.storage_voelker:
    titel_liste = [f"{active_emoji_map[v]} {v}" for v in st.session_state.storage_voelker]
    namen_string = ", ".join(titel_liste)
    
    st.markdown("<hr style='margin: 5px 0; border: none; border-top: 1px solid rgba(255,255,255,0.2);'>", unsafe_allow_html=True)
    st.subheader(f"Vergleich: {namen_string}")

    # --- METRIK BUTTONS ---
    metriken = {"Gewicht": "Gewicht", "Zunahme/Abnahme": "Gewicht_Diff", "Varroa": "Milben", "Volksstärke": "Waben_besetzt"}
    m_cols = st.columns(4)
    for i, label in enumerate(metriken.keys()):
        aktiv = (st.session_state.storage_metrik == label)
        if m_cols[i].button(label, key=f"m_{label}", use_container_width=True, type="primary" if aktiv else "secondary"):
            st.session_state.storage_metrik = label
            st.rerun()

    # --- OPTIONEN & GRAPH ---
    opt_col1, opt_col2 = st.columns([1, 2])

    with opt_col1:
        st.write("#### ⚙️ Optionen")
        
        z_opts = ["Alles anzeigen", "Dieses Jahr", "Letzte 6 Monate", "Letzte 3 Monate", "Letzte 30 Tage", "Letzte 14 Tage", "Letzte 7 Tage"]
        try: z_index = z_opts.index(st.session_state.storage_zeit)
        except ValueError: z_index = 0
        st.radio("Zeitraum auswählen:", z_opts, index=z_index, key="widget_zeit_key", on_change=save_zeit_change)
        
        c_opts = ["Linien-Diagramm", "Balkendiagramm"]
        try: c_index = c_opts.index(st.session_state.storage_chart)
        except ValueError: c_index = 0
        st.radio("Diagramm-Typ:", c_opts, index=c_index, key="widget_chart_key", on_change=save_chart_change)

    with opt_col2:
        # 1. Daten filtern
        aktuelle_voelker = st.session_state.storage_voelker
        plot_df = df[df['Stockname'].isin(aktuelle_voelker)].copy().sort_values("Datum des Eintrags")
        heute = pd.Timestamp.now().normalize()

        # 2. Zeitfilter
        auswahl = st.session_state.storage_zeit
        if auswahl == "Dieses Jahr":
            plot_df = plot_df[plot_df['Datum des Eintrags'].dt.year == heute.year]
        elif auswahl == "Letzte 6 Monate":
            plot_df = plot_df[plot_df['Datum des Eintrags'] >= (heute - pd.Timedelta(days=180))]
        elif auswahl == "Letzte 3 Monate":
            plot_df = plot_df[plot_df['Datum des Eintrags'] >= (heute - pd.Timedelta(days=90))]
        elif auswahl == "Letzte 30 Tage":
            plot_df = plot_df[plot_df['Datum des Eintrags'] >= (heute - pd.Timedelta(days=30))]
        elif auswahl == "Letzte 14 Tage":
            plot_df = plot_df[plot_df['Datum des Eintrags'] >= (heute - pd.Timedelta(days=14))]
        elif auswahl == "Letzte 7 Tage":
            plot_df = plot_df[plot_df['Datum des Eintrags'] >= (heute - pd.Timedelta(days=7))]

        # 3. Y-Achse
        y_spalte = "Gewicht"
        metrik = st.session_state.storage_metrik
        
        if metrik == "Zunahme/Abnahme":
            plot_df['Gewicht_Diff'] = plot_df.groupby('Stockname')['Gewicht'].diff()
            y_spalte = "Gewicht_Diff"
        elif metrik == "Varroa":
            y_spalte = "Milben"
        elif metrik == "Volksstärke":
            y_spalte = "Waben_besetzt"

        plot_df = plot_df.dropna(subset=[y_spalte])

        # HINWEIS WENN DATEN FEHLEN
        if not plot_df.empty:
            vorhandene_im_plot = plot_df['Stockname'].unique()
            fehlende = [v for v in aktuelle_voelker if v not in vorhandene_im_plot]
            if fehlende:
                fehlende_labels = [f"**{active_emoji_map[v]} {v}**" for v in fehlende]
                st.warning(f"⚠️ Keine Daten für {metrik} im gewählten Zeitraum: {', '.join(fehlende_labels)}")

        # 4. Plotten
        if not plot_df.empty:
            chart_typ = st.session_state.storage_chart
            
            if chart_typ == "Linien-Diagramm":
                fig = px.line(
                    plot_df, 
                    x='Datum des Eintrags', 
                    y=y_spalte, 
                    color='Stockname', 
                    color_discrete_map=active_color_map, 
                    template="plotly_dark", 
                    markers=True
                )
                fig.update_traces(
                    line=dict(width=3),
                    marker=dict(size=8, line=dict(width=1, color='white'))
                )
            else:
                fig = px.bar(
                    plot_df, 
                    x='Datum des Eintrags', 
                    y=y_spalte, 
                    color='Stockname', 
                    color_discrete_map=active_color_map, 
                    barmode='group',
                    template="plotly_dark"
                )
                fig.update_traces(marker_line_width=0)

            fig.update_layout(
                xaxis=dict(title="Datum", showgrid=False, zeroline=False),
                yaxis=dict(title=metrik, gridcolor="rgba(255,255,255,0.1)", zerolinecolor="rgba(255,255,255,0.2)"),
                plot_bgcolor="rgba(0,0,0,0)", 
                paper_bgcolor="rgba(0,0,0,0)",
                hovermode="x unified",
                margin=dict(l=0, r=0, t=10, b=0),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, title=None)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info(f"💡 Keine Daten für **'{metrik}'** im gewählten Zeitraum.")
else:
    st.info("👆 Bitte wähle oben ein oder mehrere Völker aus.")
