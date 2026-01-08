import streamlit as st
import pandas as pd
import plotly.express as px
import os
from datetime import datetime

st.set_page_config(page_title="Imker-Analyse", layout="wide")
if 'auswahl_voelker' not in st.session_state:
    st.session_state.auswahl_voelker = []


# --- HEADER BEREICH ---
col1, col2 = st.columns([2, 1], vertical_alignment="bottom")
with col1:
    st.title("Meine Völker - Auswertung")

    # Datei-Upload
    uploaded_file = st.file_uploader("Neue KIM-CSV Datei hochladen (überschreibt Basisdatei)", type=["csv"])

    # Datei-Logik
    DEFAULT_FILE = "daten.csv"
    file_to_load = None
    
    if uploaded_file is not None:
        file_to_load = uploaded_file
        # Kleiner Hinweis direkt unter dem Uploader
        st.info(f"ℹ️ Du nutzt gerade eine manuell hochgeladene Datei. ({uploaded_file.name})")
    elif os.path.exists(DEFAULT_FILE):
        file_to_load = DEFAULT_FILE
        ts = os.path.getmtime(DEFAULT_FILE)
        datum_str = datetime.fromtimestamp(ts).strftime('%d.%m.%Y um %H:%M')
        st.success(f"✅ Basis-Daten ({DEFAULT_FILE}, Stand: {datum_str} Uhr) geladen.")
    else:
        st.info("ℹ️ Keine Daten gefunden. Bitte CSV hochladen.")

with col2:
    st.image("BienenLogo.jpg", use_container_width=True)


# --- Verarbeitung ---
if file_to_load:
    # 1. Daten einlesen mit Fehler-Toleranz
    df = None # Initialisierung
    try:
        df = pd.read_csv(file_to_load, sep=None, engine='python', encoding='latin-1')
    except Exception:
        try:
            df = pd.read_csv(file_to_load, sep=None, engine='python', encoding='utf-8')
        except Exception as e:
            st.error(f"❌ Die Datei konnte nicht gelesen werden: {e}")
    
    # Der "Sauberkeits"-Check
    if df is not None:
        # Datum konvertieren und bereinigen
        df['Datum des Eintrags'] = pd.to_datetime(df['Datum des Eintrags'], dayfirst=True, errors='coerce')
        df = df.dropna(subset=['Datum des Eintrags', 'Stockname'])        
    else:
        st.error("⚠️ Fehler: Es konnten keine Daten aus der Datei extrahiert werden.")
        st.stop() # Stoppt die App hier, damit keine Folgefehler kommen
else:
    st.info("💡 Bitte lade eine CSV-Datei hoch, um mit der Analyse zu beginnen.")
    st.stop()


# --- Völkerauswahl mit "Gedrückt"-Effekt & Abwahl ---
st.write("### Schnellzugriff Völker")
alle_voelker = sorted(df['Stockname'].unique())

spalten_pro_reihe = 10
for i in range(0, len(alle_voelker), spalten_pro_reihe):
    aktuelle_auswahl = alle_voelker[i : i + spalten_pro_reihe]
    cols = st.columns(spalten_pro_reihe)
    
    for j, volk_name in enumerate(aktuelle_auswahl):
        with cols[j]:
            # 1. Prüfen: Ist dieses Volk gerade das ausgewählte?
            ist_aktiv = (st.session_state.auswahl_voelker == [volk_name])
            
            # 2. Optik anpassen: Primary-Farbe (Gelb) wenn aktiv, sonst normal
            st.image("VolkLogo.jpg", use_container_width=True)
            
            if st.button(
                volk_name, 
                key=f"btn_{volk_name}", 
                use_container_width=True, 
                type="primary" if ist_aktiv else "secondary"
            ):
                # 3. Logik beim Klicken:
                if ist_aktiv:
                    # Wenn es schon aktiv war -> abwählen
                    st.session_state.auswahl_voelker = []
                else:
                    # Wenn es nicht aktiv war -> dieses Volk wählen
                    st.session_state.auswahl_voelker = [volk_name]
                
                # Seite neu laden, um die Farben und Diagramme sofort zu ändern
                st.rerun()


# OPTIONEN & DIAGRAMM (Nur anzeigen, wenn ein Volk gewählt wurde)
if st.session_state.auswahl_voelker:
    gewaehltes_volk = st.session_state.auswahl_voelker[0]
    
    st.divider() 
    st.subheader(f"Analyse für: {gewaehltes_volk}")

    # --- 1. NEU: METRIK-AUSWAHL BUTTONS ---
    st.write("#### 📊 Welche Werte möchtest du analysieren?")
    
    metriken = {
        "Gewicht": "Gewicht",
        "Zunahme/Abnahme": "Gewicht_Diff",
        "Varroa": "Gezählte Milben",
        "Volksstärke": "Besetzte Waben"
    }

    if 'gewaehlte_metrik' not in st.session_state:
        st.session_state.gewaehlte_metrik = "Gewicht"

    m_cols = st.columns(4) # Wir nehmen fest 4 Spalten für die 4 Metriken
    for i, (label, spalte) in enumerate(metriken.items()):
        with m_cols[i]:
            ist_metrik_aktiv = (st.session_state.gewaehlte_metrik == label)
            if st.button(label, key=f"m_{label}", use_container_width=True, 
                         type="primary" if ist_metrik_aktiv else "secondary"):
                st.session_state.gewaehlte_metrik = label
                st.rerun()

    # --- 2. LAYOUT: LINKS OPTIONEN, RECHTS DIAGRAMM ---
    opt_col1, opt_col2 = st.columns([1, 2])

    with opt_col1:
        st.write("#### ⚙️ Anzeige-Optionen")
        zeitraum = st.radio(
            "Zeitraum auswählen:",
            ["Alles anzeigen", "Letzte 30 Tage", "Letzte 7 Tage"]
        )
        # Hier kannst du weitere Filter einbauen

    with opt_col2:
        # Daten filtern und berechnen
        volk_df = df[df['Stockname'] == gewaehltes_volk].copy().sort_values("Datum des Eintrags")
        
        # Berechnung für die Differenz-Metrik
        if st.session_state.gewaehlte_metrik == "Zunahme/Abnahme":
            volk_df['Gewicht_Diff'] = volk_df['Gewicht'].diff()
            y_achse = 'Gewicht_Diff'
        else:
            y_achse = metriken[st.session_state.gewaehlte_metrik]

        # Graph zeichnen
        if not volk_df[y_achse].dropna().empty:
            fig = px.line(volk_df, x='Datum des Eintrags', y=y_achse, 
                          title=f"{st.session_state.gewaehlte_metrik} - {gewaehltes_volk}",
                          markers=True)
            
            fig.update_traces(line=dict(width=4), marker=dict(size=10))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning(f"Keine Daten für '{st.session_state.gewaehlte_metrik}' vorhanden.")

else:
    st.info("👆 Bitte wähle oben ein Volk aus, um die Details zu sehen.")
