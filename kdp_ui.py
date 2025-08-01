import streamlit as st
import pandas as pd
import subprocess
import os

st.sidebar.title("📚 Panel de navegación")
section = st.sidebar.radio("Selecciona una sección", ["KDP", "FBA", "Análisis", "Ventas"], index=0)

if section == "KDP":
    st.title("📘 Kindle Direct Publishing (KDP)")

    st.subheader("🔎 Análisis de Nichos")

    selected_keyword = st.selectbox(
        "Selecciona una keyword base",
        ["diario", "planner", "cuaderno", "notebook", "gratitud"],
    )

    if st.button("Buscar Nichos"):
        with st.spinner("Buscando nichos rentables en Amazon..."):
            subprocess.run([
                "python",
                "kdp_discovery.py",
                "--keyword",
                selected_keyword,
            ], check=True)

    # Paso 2: Mostrar tabla si existe archivo
    if os.path.exists("niches_found.csv"):
        niches_df = pd.read_csv("niches_found.csv")

        st.markdown("### 📊 Nichos Detectados")
        st.markdown("Fuente: *Selenium scraping sobre Amazon.es autocomplete*")

        st.dataframe(niches_df[["niche", "competition", "avg_bsr", "saturation", "search_volume"]])

        st.markdown(
            """
            **Notas de interpretación:**
            - `competition < 1000` → baja saturación.
            - `BSR < 100000` → alta demanda.
            - `saturation = competition / avg_bsr`.
            - `search_volume` es un placeholder hasta integrar una API.
            """
        )

        niches = niches_df["niche"].dropna().unique().tolist()

        st.header("🔍 Análisis de Competencia")

        if len(niches) < 5:
            st.warning("Menos de 5 nichos detectados. Se analizarán todos automáticamente.")
            summary_rows = []

            for niche in niches:
                st.write(f"📊 Analizando: **{niche}**...")
                subprocess.run(["python", "kdp_competition.py", "--niche", niche, "--mock"], check=True)
                result_df = pd.read_csv("competitor_analysis.csv")
                avg_row = result_df.tail(1)
                avg_row.insert(0, "niche", niche)
                summary_rows.append(avg_row)

            summary_df = pd.concat(summary_rows, ignore_index=True)
            st.subheader("📈 Resumen de Nichos")
            st.dataframe(summary_df[["niche", "price", "reviews", "bsr", "keyword_density"]].rename(columns={
                "price": "avg_price",
                "reviews": "avg_reviews",
                "bsr": "avg_bsr",
                "keyword_density": "avg_keyword_density"
            }))

        else:
            selected_niche = st.selectbox("Selecciona un nicho para analizar:", niches)
            if st.button("Analizar competencia"):
                subprocess.run(["python", "kdp_competition.py", "--niche", selected_niche, "--mock"], check=True)
                result_df = pd.read_csv("competitor_analysis.csv")
                st.subheader(f"📄 Resultados para: {selected_niche}")
                st.dataframe(result_df)
    else:
        st.warning(
            "⚠️ Aún no se ha generado el archivo niches_found.csv. Haz clic en 'Buscar Nichos'."
        )
