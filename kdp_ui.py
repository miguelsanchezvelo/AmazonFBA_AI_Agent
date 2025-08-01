import argparse
import os
import json
import subprocess
import pandas as pd
import streamlit as st
import sys

DEFAULT_KEYWORDS = [
    "diario",
    "planner",
    "cuaderno",
    "notebook",
    "gratitud",
    "recetas",
    "viajes",
    "hábitos",
    "niños",
    "embarazo",
]

KEYWORDS_FILE = "keywords.json"
NICHES_FILE = "niches_found.csv"


def ensure_keywords() -> list[str]:
    """Return list of keywords, creating the file with defaults if needed."""
    if not os.path.exists(KEYWORDS_FILE):
        with open(KEYWORDS_FILE, "w", encoding="utf-8") as f:
            json.dump({"keywords": DEFAULT_KEYWORDS}, f, indent=4, ensure_ascii=False)
    try:
        with open(KEYWORDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data.get("keywords", DEFAULT_KEYWORDS)
    except Exception:
        pass
    return DEFAULT_KEYWORDS


def kdp_section() -> None:
    """Render the niche discovery section."""
    st.subheader("🔎 Análisis de Nichos")

    keyword_options = ensure_keywords()
    selected_keyword = st.selectbox("Selecciona una keyword base:", keyword_options)

    if st.button("Buscar Nichos"):
        with st.spinner(f"Buscando nichos relacionados con '{selected_keyword}'..."):
            subprocess.run([sys.executable, "kdp_discovery.py", "--keyword", selected_keyword], check=False)

    if os.path.exists(NICHES_FILE):
        df = pd.read_csv(NICHES_FILE)
        st.markdown("### 📊 Nichos Detectados")
        st.markdown("Fuente: *Selenium scraping sobre Amazon.es autocomplete*")
        cols = [c for c in ["niche", "competition", "avg_bsr", "saturation", "search_volume"] if c in df.columns]
        if cols:
            st.dataframe(df[cols])
        else:
            st.dataframe(df)
        st.markdown(
            """
    **Notas de interpretación:**
    - Una **competencia baja** (< 1000) indica menos saturación.
    - Un **BSR bajo** (< 100000) indica buena demanda.
    - `saturation = competition / avg_bsr` mide la dificultad relativa.
    - `search_volume` se mostrará como "N/A" hasta conectar con una API externa.
    """
        )
    else:
        st.warning("⚠️ Aún no se ha generado el archivo niches_found.csv. Haz clic en 'Buscar Nichos'.")


def run_headless(auto: bool = False) -> None:
    """Run a headless niche search using the first keyword."""
    keywords = ensure_keywords()
    keyword = keywords[0] if keywords else ""
    cmd = [sys.executable, "kdp_discovery.py", "--keyword", keyword]
    if auto:
        cmd.append("--auto")
    subprocess.run(cmd, check=False)


def parse_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KDP Toolkit UI", add_help=False)
    parser.add_argument("--headless", action="store_true", help="run without UI")
    parser.add_argument("--auto", action="store_true", help="run automated niche search")
    args, _ = parser.parse_known_args()
    return args


def main() -> None:
    args = parse_cli()
    if args.headless:
        run_headless(auto=args.auto)
    else:
        st.set_page_config(page_title="KDP Toolkit", layout="wide")
        kdp_section()


if __name__ == "__main__":
    main()
