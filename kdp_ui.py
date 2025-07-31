import os
import subprocess
import pandas as pd
import streamlit as st

# Sidebar with default selection on "KDP"
section = st.sidebar.radio("Selecciona una sección", ["KDP"], index=0)

if section == "KDP":
    st.header("🔍 Análisis de Competencia")
    niche_file = "niches_found.csv"

    if not os.path.exists(niche_file):
        st.warning("Primero ejecuta el análisis de nichos para generar niches_found.csv")
    else:
        niches_df = pd.read_csv(niche_file)
        niches = niches_df["niche"].dropna().unique().tolist()

        if not niches:
            st.warning("El archivo niches_found.csv está vacío.")
        elif len(niches) < 5:
            st.warning("Menos de 5 nichos detectados. Se analizarán todos automáticamente.")
            summary_rows = []
            for niche in niches:
                st.write(f"Analizando competencia para: **{niche}**...")
                subprocess.run(["python", "kdp_competition.py", "--niche", niche, "--mock"], check=True)
                result_df = pd.read_csv("competitor_analysis.csv")
                avg_row = result_df.tail(1)
                avg_row.insert(0, "niche", niche)
                summary_rows.append(avg_row)

            if summary_rows:
                summary_df = pd.concat(summary_rows, ignore_index=True)
                summary_df = summary_df[["niche", "price", "reviews", "bsr", "keyword_density"]]
                summary_df = summary_df.rename(columns={
                    "price": "avg_price",
                    "reviews": "avg_reviews",
                    "bsr": "avg_bsr",
                    "keyword_density": "avg_keyword_density",
                })
                st.dataframe(summary_df)
        else:
            selected_niche = st.selectbox("Selecciona un nicho para analizar:", niches)
            if st.button("Analizar competencia"):
                subprocess.run(["python", "kdp_competition.py", "--niche", selected_niche, "--mock"], check=True)
                result_df = pd.read_csv("competitor_analysis.csv")
                st.subheader("Resultados")
                st.dataframe(result_df)
