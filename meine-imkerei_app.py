import streamlit as st
import pandas as pd
import plotly.express as px
import os

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
        st.success(f"✅ Basis-Daten ({DEFAULT_FILE}) geladen.")
    else:
        st.info("ℹ️ Keine Daten gefunden. Bitte CSV hochladen.")

with col2:
    st.image("BienenLogo.jpg", use_container_width=True)


# --- Verarbeitung ---
if file_to_load:
    # 1. Daten einlesen mit Fehler-Toleranz
    try:
        df = pd.read_csv(file_to_load, sep=None, engine='python', encoding='latin-1')
    except Exception:
        df = pd.read_csv(file_to_load, sep=None, engine='python', encoding='utf-8')


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


# --- OPTIONEN & DIAGRAMM (Nur anzeigen, wenn ein Volk gewählt wurde) ---
if st.session_state.auswahl_voelker:
    gewaehltes_volk = st.session_state.auswahl_voelker[0]
    
    st.divider() # Eine Trennlinie für die Optik
    st.subheader(f"Analyse für: {gewaehltes_volk}")

    # Wir erstellen zwei Spalten für die Optionen
    opt_col1, opt_col2 = st.columns([1, 2])

    with opt_col1:
        st.write("#### ⚙️ Anzeige-Optionen")
        zeitraum = st.radio(
            "Zeitraum auswählen:",
            ["Alles anzeigen", "Letzte 30 Tage", "Letzte 7 Tage"]
        )
        
        darstellung = st.selectbox(
            "Diagramm-Typ:",
            ["Linien-Diagramm", "Balken-Diagramm"]
        )

    with opt_col2:
        # Hier filtern wir die Daten für das Diagramm
        volk_df = df[df['Stockname'] == gewaehltes_volk]
        
        # Beispiel-Diagramm
        fig = px.line(volk_df, x='Datum des Eintrags', y='Gewicht', 
                     title=f"Gewichtsverlauf {gewaehltes_volk}",
                     markers=True)
        
        # Linienstärke anpassen für Darkmode
        fig.update_traces(line=dict(width=4))
        
        st.plotly_chart(fig, use_container_width=True)

else:
    # Hinweistext, wenn noch nichts geklickt wurde
    st.info("👆 Bitte wähle oben ein Volk aus, um die Details zu sehen.")
