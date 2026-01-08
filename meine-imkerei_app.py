import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="Imker-Analyse", layout="wide")
st.title("🐝 Meine Völker-Auswertung")

# --- DATEI-LOGIK ---
# Wir schauen, ob eine Basis-Datei auf GitHub liegt
DEFAULT_FILE = "daten.csv"
uploaded_file = st.file_uploader("KIM-CSV Datei hochladen (optional, überschreibt Basis-Daten)", type=["csv"])

# Entscheidung: Welche Datei nehmen wir?
file_to_load = None

if uploaded_file is not None:
    file_to_load = uploaded_file
    st.info("Du nutzt gerade eine manuell hochgeladene Datei.")
elif os.path.exists(DEFAULT_FILE):
    file_to_load = DEFAULT_FILE
    st.success(f"Basis-Daten ({DEFAULT_FILE}) erfolgreich von GitHub geladen.")
else:
    st.warning("Keine Daten gefunden. Bitte lade eine CSV-Datei hoch oder hinterlege 'daten.csv' auf GitHub.")

if file_to_load:
    # 1. Daten einlesen
    try:
        df = pd.read_csv(file_to_load, sep=None, engine='python', encoding='latin-1')
    except Exception:
        df = pd.read_csv(file_to_load, sep=None, engine='python', encoding='utf-8')

    # Datum konvertieren und bereinigen
    df['Datum des Eintrags'] = pd.to_datetime(df['Datum des Eintrags'], dayfirst=True, errors='coerce')
    df = df.dropna(subset=['Datum des Eintrags', 'Stockname'])

    # --- SIDEBAR ---
    st.sidebar.header("Einstellungen")
    x_modus = st.sidebar.radio("X-Achse Anzeige:", ["Kalenderdatum", "Tage ab Start"])
    
    st.sidebar.header("Design")
    bg_modus = st.sidebar.radio("Hintergrund-Stil:", ["Status-Zonen", "Monats-Raster", "Kein Hintergrund"])
    
    alle_voelker = sorted(df['Stockname'].unique())
    auswahl_voelker = st.sidebar.multiselect("Völker auswählen:", alle_voelker, default=alle_voelker[:1])

    # --- DATEN-VORBEREITUNG ---
    df_plot = df[df['Stockname'].isin(auswahl_voelker)].copy()
    df_plot = df_plot.dropna(subset=['Gewicht']).sort_values("Datum des Eintrags")

    if not df_plot.empty:
        # X-Achsen Logik
        if x_modus == "Tage ab Start":
            df_plot['X_Achse'] = df_plot.groupby('Stockname')['Datum des Eintrags'].transform(lambda x: (x - x.min()).dt.days)
            label_x = "Tage seit Beobachtungsbeginn"
        else:
            df_plot['X_Achse'] = df_plot['Datum des Eintrags']
            label_x = "Datum"

        # Haupt-Graph erstellen
        fig = px.line(
            df_plot, 
            x='X_Achse', 
            y='Gewicht', 
            color='Stockname',
            markers=True,
            title=f"Gewichtsverlauf ({x_modus})",
            hover_data={"X_Achse": False, "Datum des Eintrags": "|%d.%m.%Y"}
        )

        # --- HINTERGRUND & ACHSEN LOGIK ---
        if bg_modus == "Status-Zonen":
            fig.add_hrect(y0=0, y1=15, fillcolor="red", opacity=0.15, annotation_text="Futternot", line_width=0)
            fig.add_hrect(y0=15, y1=20, fillcolor="yellow", opacity=0.15, annotation_text="Beobachten", line_width=0)
            fig.add_hrect(y0=20, y1=45, fillcolor="green", opacity=0.08, annotation_text="Optimal", line_width=0)
            show_ticks = True
        
        elif bg_modus == "Monats-Raster" and x_modus == "Kalenderdatum":
            show_ticks = False
            start_m = df_plot['Datum des Eintrags'].min().replace(day=1)
            end_m = df_plot['Datum des Eintrags'].max()
            current = start_m
            i = 0
            monate_namen = {1:"Jan", 2:"Feb", 3:"Mär", 4:"Apr", 5:"Mai", 6:"Jun", 
                           7:"Jul", 8:"Aug", 9:"Sep", 10:"Okt", 11:"Nov", 12:"Dez"}
            
            while current <= end_m:
                next_m = (current + pd.DateOffset(months=1))
                mid_point = current + (next_m - current) / 2
                if i % 2 == 0:
                    fig.add_vrect(x0=current, x1=next_m, fillcolor="white", opacity=0.07, line_width=0)
                fig.add_annotation(
                    x=mid_point, y=0, yref="paper",
                    text=f"<b>{monate_namen[current.month]} {current.year}</b>",
                    showarrow=False, font=dict(size=12, color="gray"),
                    yshift=-25
                )
                current = next_m
                i += 1
            fig.update_layout(margin=dict(b=80))
        else:
            show_ticks = True
            fig.update_layout(margin=dict(b=40))

        fig.update_xaxes(title_text=label_x, showticklabels=show_ticks)
        fig.update_yaxes(title_text="Gewicht (kg)")
        st.plotly_chart(fig, use_container_width=True)
        
        # --- WARNSYSTEM ---
        aktuelle_werte = df_plot.sort_values('Datum des Eintrags').groupby('Stockname').last()
        for stock, row in aktuelle_werte.iterrows():
            if row['Gewicht'] < 15:
                st.error(f"⚠️ **{stock}** kritisch: Nur noch {row['Gewicht']}kg!")
    else:
        st.warning("Keine Gewichtsdaten für die Auswahl gefunden.")
