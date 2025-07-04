import argparse
import os
import sys
import subprocess
from typing import List, Tuple, Dict
import openai
import csv

# Absolute path to the repository root so modules are executed
# consistently regardless of the working directory.
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

import streamlit as st
import pandas as pd

import fba_agent

FRIENDLY_NAMES: Dict[str, str] = {
    "product_discovery.py": "Product Discovery",
    "market_analysis.py": "Market Analysis",
    "profitability_estimation.py": "Profitability Estimation",
    "demand_forecast.py": "Demand Forecast",
    "supplier_selection.py": "Supplier Selection",
    "supplier_contact_generator.py": "Supplier Contact Generator",
    "pricing_simulator.py": "Pricing Simulator",
    "inventory_management.py": "Inventory Management",
}

MODULES: List[Tuple[str, str]] = [
    ("Run Product Discovery", "product_discovery.py"),
    ("Run Market Analysis", "market_analysis.py"),
    ("Run Profitability Estimation", "profitability_estimation.py"),
    ("Run Demand Forecast", "demand_forecast.py"),
    ("Run Supplier Selection", "supplier_selection.py"),
    ("Generate Supplier Emails", "supplier_contact_generator.py"),
    ("Simulate Pricing Strategy", "pricing_simulator.py"),
    ("Manage Inventory", "inventory_management.py"),
]

# --- NUEVO: Diccionario de traducción para mensajes clave ---
TRANSLATIONS = {
    'en': {
        'run_all': 'Run All',
        'run_tests': 'Run Tests',
        'validate_pipeline': 'Validate Pipeline',
        'reset_pipeline': 'Reset Pipeline (delete all generated data)',
        'resetting_pipeline': 'Resetting pipeline...',
        'pipeline_reset': 'Pipeline reset. All generated data has been deleted. Please rerun the steps.',
        'results_file_exists': 'The results file {output_path} already exists. The data may be mock or outdated. If you want to start fresh, use the button below to reset the pipeline.',
        'see_roi_chart': 'To see the ROI per product chart, install plotly: pip install plotly',
        'supplier_selection_empty': 'Supplier selection results are empty.',
        'run_supplier_selection': 'Run Supplier Selection to generate summary data.',
        'failed_to_read': 'Failed to read {sel_path}: {exc}',
        'tests_failed': 'Tests failed. Check output for details.',
        'validation_failed': 'Validation reported issues. Check output for details.',
        'pipeline_completed': 'Pipeline completed. Refresh to see new results.',
        'step_success': '✅ {label} completed successfully',
        'step_failed': '❌ {label} failed',
        'installing_deps': 'Installing dependencies...',
        'env_setup_log': 'Environment Setup Log',
    },
    'es': {
        'run_all': 'Ejecutar Todo',
        'run_tests': 'Ejecutar Tests',
        'validate_pipeline': 'Validar Pipeline',
        'reset_pipeline': 'Reiniciar Pipeline (eliminar todos los datos generados)',
        'resetting_pipeline': 'Reiniciando pipeline...',
        'pipeline_reset': 'Pipeline reiniciado. Todos los datos generados han sido eliminados. Por favor, ejecuta los pasos de nuevo.',
        'results_file_exists': 'El archivo de resultados {output_path} ya existe. Los datos pueden ser mock o antiguos. Si quieres empezar limpio, usa el botón de abajo para reiniciar la pipeline.',
        'see_roi_chart': 'Para ver la gráfica de ROI por producto, instala plotly: pip install plotly',
        'supplier_selection_empty': 'Los resultados de selección de proveedores están vacíos.',
        'run_supplier_selection': 'Ejecuta la selección de proveedores para generar datos de resumen.',
        'failed_to_read': 'No se pudo leer {sel_path}: {exc}',
        'tests_failed': 'Los tests han fallado. Consulta el resultado para más detalles.',
        'validation_failed': 'La validación ha reportado problemas. Consulta el resultado para más detalles.',
        'pipeline_completed': 'Pipeline completada. Refresca para ver los nuevos resultados.',
        'step_success': '✅ {label} completado correctamente',
        'step_failed': '❌ {label} falló',
        'installing_deps': 'Instalando dependencias...',
        'env_setup_log': 'Log de instalación del entorno',
    }
}

def t(key, **kwargs):
    lang = st.session_state.get('lang', 'en')
    msg = TRANSLATIONS.get(lang, TRANSLATIONS['en']).get(key, key)
    return msg.format(**kwargs)

def run_module(script_name: str, budget: float = 0.0) -> Tuple[str, str, int, str]:
    """Run a module and return (stdout, stderr, exit_code, detailed_log)."""
    cmd = [sys.executable, script_name, "--auto"]
    inp = None
    env = os.environ.copy()
    if script_name == "product_discovery.py":
        cmd = [sys.executable, script_name, "--auto"]
        env["FBA_BUDGET"] = str(budget)
    log_lines = []
    log_lines.append(f"🚀 Running command: {' '.join(cmd)}")
    log_lines.append("-" * 30)
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ROOT_DIR,
            input=inp,
            env=env,
        )
        log_lines.append("📝 Stdout:")
        log_lines.append(result.stdout.strip())
        log_lines.append("📝 Stderr:")
        log_lines.append(result.stderr.strip())
        log_lines.append(f"Exit code: {result.returncode}")
        if result.returncode != 0:
            log_lines.append("-" * 30)
            log_lines.append(f"❌ Step failed with exit code {result.returncode}.")
            log_lines.append("Troubleshooting:")
            log_lines.append(" - Check the output above for specific errors.")
            log_lines.append(" - Ensure all required dependencies are installed (pip install -r requirements.txt).")
            log_lines.append(f" - Try running the step manually in your terminal:")
            log_lines.append(f"   cd {ROOT_DIR}")
            log_lines.append(f"   {' '.join(cmd)}")
        return result.stdout, result.stderr, result.returncode, "\n".join(log_lines)
    except Exception as exc:
        log_lines.append("-" * 30)
        log_lines.append(f"💥 An exception occurred: {exc}")
        return "", str(exc), 1, "\n".join(log_lines)


def commit_and_push_changes(
    message: str = "Auto: update after running Streamlit action",
) -> None:
    """Commit and push changes using Git if available."""
    try:
        if not os.path.isdir(os.path.join(os.getcwd(), ".git")):
            return
        subprocess.run(["git", "add", "."], cwd=os.getcwd(), check=False)
        subprocess.run(["git", "commit", "-m", message], cwd=os.getcwd(), check=False)
        subprocess.run(["git", "push"], cwd=os.getcwd(), check=False)
    except Exception:
        pass


def file_has_content(path: str) -> bool:
    """Return ``True`` if a file exists and has content (more than a header for CSVs)."""
    if not os.path.exists(path):
        return False
    if os.path.isdir(path):
        try:
            return bool(os.listdir(path))
        except OSError:
            return False
    try:
        with open(path, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) > 1
    except (IOError, UnicodeDecodeError):
        return False


def run_test_all() -> Tuple[str, int]:
    """Execute ``test_all.py`` and return a detailed log and exit code."""
    script_path = os.path.join(ROOT_DIR, "test_all.py")
    log_lines = []

    if not os.path.exists(script_path):
        log_lines.append(f"❌ Error: Test script not found at {script_path}")
        log_lines.append(
            "Troubleshooting: Ensure 'test_all.py' exists in the root directory."
        )
        return "\n".join(log_lines), 1

    cmd = [sys.executable, script_path]
    log_lines.append(f"🚀 Running command: {' '.join(cmd)}")
    log_lines.append("-" * 30)

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ROOT_DIR,
        )

        output = res.stdout + res.stderr
        log_lines.append("📝 Output:")
        log_lines.append(output.strip())

        if res.returncode != 0:
            log_lines.append("-" * 30)
            log_lines.append(f"❌ Test run failed with exit code {res.returncode}.")
            log_lines.append("Troubleshooting:")
            log_lines.append(" - Check the output above for specific errors.")
            log_lines.append(
                " - Ensure all required dependencies are installed (e.g., pip install -r requirements.txt)."
            )
            log_lines.append(
                " - Run the tests from your terminal directly to see if the issue persists:"
            )
            log_lines.append(f"   cd {ROOT_DIR}")
            log_lines.append(f"   {os.path.basename(sys.executable)} test_all.py")

        return "\n".join(log_lines), res.returncode

    except Exception as exc:
        log_lines.append("-" * 30)
        log_lines.append(
            f"💥 An exception occurred while trying to run the tests: {exc}"
        )
        return "\n".join(log_lines), 1


def run_validate_all() -> Tuple[str, int]:
    """Execute ``validate_all.py`` and return a detailed log and exit code."""
    script_path = os.path.join(ROOT_DIR, "validate_all.py")
    log_lines = []

    if not os.path.exists(script_path):
        log_lines.append(f"❌ Error: Validation script not found at {script_path}")
        log_lines.append(
            "Troubleshooting: Ensure 'validate_all.py' exists in the root directory."
        )
        return "\n".join(log_lines), 1

    cmd = [sys.executable, script_path]
    log_lines.append(f"🚀 Running command: {' '.join(cmd)}")
    log_lines.append("-" * 30)

    try:
        res = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=ROOT_DIR,
        )

        output = res.stdout + res.stderr
        log_lines.append("📝 Output:")
        log_lines.append(output.strip())

        if res.returncode != 0:
            log_lines.append("-" * 30)
            log_lines.append(
                f"❌ Validation failed with exit code {res.returncode}."
            )
            log_lines.append("Troubleshooting:")
            log_lines.append(
                " - Look for 'Error' or 'Missing' messages in the output above."
            )
            log_lines.append(
                " - Some validation checks depend on pipeline outputs. Ensure required steps have been run."
            )
            log_lines.append(
                " - Run validation from your terminal directly to see if the issue persists:"
            )
            log_lines.append(f"   cd {ROOT_DIR}")
            log_lines.append(f"   {os.path.basename(sys.executable)} validate_all.py")

        return "\n".join(log_lines), res.returncode

    except Exception as exc:
        log_lines.append("-" * 30)
        log_lines.append(
            f"💥 An exception occurred while trying to run validation: {exc}"
        )
        return "\n".join(log_lines), 1


def display_csv(path: str, title: str) -> None:
    if not os.path.exists(path):
        st.warning(f"{title}: file missing")
        return
    try:
        df = pd.read_csv(path)
    except Exception as exc:
        st.warning(f"Failed to read {path}: {exc}")
        return
    if df.empty:
        st.warning(f"{title}: file is empty")
        return
    st.subheader(title)
    st.dataframe(df)


def show_messages(dir_path: str) -> None:
    if not os.path.isdir(dir_path):
        return
    st.subheader("Supplier Messages")
    for name in sorted(os.listdir(dir_path)):
        if not name.endswith(".txt"):
            continue
        msg_path = os.path.join(dir_path, name)
        try:
            with open(msg_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception:
            content = ""
        new = st.text_area(f"{name}", content, key=msg_path)
        if new != content:
            with open(msg_path, "w", encoding="utf-8") as f:
                f.write(new)
            st.success(f"Updated {name}")


def summary_screen() -> None:
    sel_path = fba_agent.OUTPUTS["supplier_selection"]
    if not os.path.exists(sel_path):
        st.info(t('run_supplier_selection'))
        return
    try:
        df = pd.read_csv(sel_path)
    except Exception as exc:
        st.warning(t('failed_to_read', sel_path=sel_path, exc=exc))
        return
    if df.empty:
        st.warning(t('supplier_selection_empty'))
        return
    total_profit = df.get("estimated_profit", pd.Series(dtype=float)).sum()
    st.metric("Total Projected Profit", f"${total_profit:,.2f}")
    # --- NUEVO: Comprobar si plotly está instalado antes de graficar ---
    try:
        import plotly.express as px
        if "roi" in df.columns and "asin" in df.columns:
            fig = px.bar(df, x="asin", y="roi", title="ROI per Product")
            st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.info(t('see_roi_chart'))
    st.dataframe(df)


def run_prepare_environment() -> str:
    """Run pip install -r requirements.txt and return the output log."""
    import subprocess
    try:
        res = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            capture_output=True,
            text=True,
            cwd=ROOT_DIR,
        )
        log = res.stdout + res.stderr
        return log
    except Exception as exc:
        return f"Error running pip install: {exc}"


def pipeline_ui() -> None:
    st.title("Amazon FBA AI Agent")
    # --- Selector de idioma en la parte superior derecha ---
    if 'lang' not in st.session_state:
        st.session_state['lang'] = 'en'
    lang = st.sidebar.selectbox('Language / Idioma', options=[('en', 'English'), ('es', 'Español')], format_func=lambda x: x[1], index=0 if st.session_state['lang']=='en' else 1)
    st.session_state['lang'] = lang[0]
    if "logs" not in st.session_state:
        st.session_state.logs = {label: "" for label, _ in MODULES}
    if "tests_ok" not in st.session_state:
        st.session_state.tests_ok = True
    if "validation_ok" not in st.session_state:
        st.session_state.validation_ok = True
    if "dev_mode" not in st.session_state:
        st.session_state.dev_mode = True
    if "budget" not in st.session_state:
        st.session_state.budget = 1500.0

    st.sidebar.title("Configuration")
    dev_mode = st.sidebar.checkbox("Modo desarrollador (mock)", value=st.session_state.dev_mode)
    st.session_state.dev_mode = dev_mode
    budget = st.sidebar.number_input(
        "Startup Budget (USD)", min_value=100.0, value=st.session_state.budget, step=100.0
    )
    st.session_state.budget = budget

    # Mostrar Run Tests y Validate Pipeline solo en modo desarrollador
    if dev_mode:
        if st.button(t('run_tests')):
            with st.spinner("Running tests..."):
                out, code = run_test_all()
            with st.expander("Test Output", expanded=code != 0):
                st.code(out)
            st.session_state.tests_ok = code == 0
            if st.session_state.tests_ok:
                st.success("Tests passed")
            else:
                st.error(t('tests_failed'))

        if st.button(t('validate_pipeline')):
            with st.spinner("Validating pipeline..."):
                vout, vcode = run_validate_all()
            with st.expander("Validation Output", expanded=vcode != 0):
                st.code(vout)
            st.session_state.validation_ok = vcode == 0
            if st.session_state.validation_ok:
                st.success("Validation passed")
            else:
                st.error(t('validation_failed'))

    # --- NUEVO: Botón para ejecutar toda la pipeline ---
    if st.button(t('run_all')):
        with st.spinner("Running full pipeline..."):
            run_headless(auto=True)
        st.success(t('pipeline_completed'))

    st.divider()

    disabled = not (st.session_state.tests_ok and st.session_state.validation_ok)

    # Definir los archivos de salida de cada módulo en orden
    output_files = [
        ("Product Results", fba_agent.OUTPUTS["product_discovery"]),
        ("Market Analysis", fba_agent.OUTPUTS["market_analysis"]),
        ("Profitability", fba_agent.OUTPUTS["profitability_estimation"]),
        ("Demand Forecast", fba_agent.OUTPUTS["demand_forecast"]),
        ("Supplier Selection", fba_agent.OUTPUTS["supplier_selection"]),
        ("Pricing Suggestions", fba_agent.OUTPUTS["pricing_simulator"]),
        ("Inventory Management", fba_agent.OUTPUTS["inventory_management"]),
    ]

    prereqs_met = True
    for idx, (label, script) in enumerate(MODULES):
        with st.expander(label, expanded=False):
            is_step_disabled = disabled or not prereqs_met
            if st.button(label, key=f"btn_{script}", disabled=is_step_disabled):
                run_step_ui(label, script, st.session_state.budget, st.session_state.dev_mode)
            if st.session_state.dev_mode and st.session_state.logs[label]:
                st.text_area("Log", st.session_state.logs[label], height=150)
            if idx < len(output_files):
                out_title, out_path = output_files[idx]
                if os.path.exists(out_path) and file_has_content(out_path):
                    if label == "Run Supplier Selection":
                        display_supplier_selection()
                    elif label == "Generate Supplier Emails":
                        supplier_dir = fba_agent.OUTPUTS["supplier_contact_generator"]
                        if st.session_state.dev_mode and (not os.path.isdir(supplier_dir) or not os.listdir(supplier_dir)):
                            # MOCK: Mensaje simulado editable
                            default_msg = (
                                "Estimado proveedor,\n\nEstoy interesado en su producto y me gustaría recibir información sobre precios, condiciones de envío y plazos de entrega para el siguiente producto:\n- Título: Mock Product 1\n- ASIN: B0MOCK001\n\nGracias de antemano por su atención.\n\nUn saludo."
                            )
                            if "mock_supplier_msg" not in st.session_state:
                                st.session_state["mock_supplier_msg"] = default_msg
                            msg = st.text_area("Mensaje simulado a proveedor (editable)", st.session_state["mock_supplier_msg"], height=200)
                            st.session_state["mock_supplier_msg"] = msg
                            col1, col2 = st.columns(2)
                            with col1:
                                if st.button("Guardar mensaje", key="guardar_mock_msg"):
                                    st.success("Mensaje guardado (mock)")
                            with col2:
                                if st.button("Enviar mensaje", key="enviar_mock_msg"):
                                    st.success("Mensaje enviado (mock, no se realiza envío real)")
                        else:
                            # MODO REAL: Un mensaje por producto con unidades asignadas
                            supplier_csv = os.path.join("data", "supplier_selection_results.csv")
                            productos = []
                            if os.path.exists(supplier_csv):
                                with open(supplier_csv, newline='', encoding='utf-8') as f:
                                    reader = csv.DictReader(f)
                                    for row in reader:
                                        try:
                                            units = int(float(row.get("units_to_order") or row.get("Units") or row.get("units") or 0))
                                        except Exception:
                                            units = 0
                                        if units > 0:
                                            productos.append({
                                                "asin": row.get("asin") or row.get("ASIN") or "",
                                                "title": row.get("title") or row.get("Title") or "",
                                                "units": units
                                            })
                            if not productos:
                                st.info("No hay productos con unidades asignadas para contactar proveedores.")
                            for i, prod in enumerate(productos):
                                st.markdown(f"**Producto:** {prod['title']}  ")
                                st.markdown(f"**ASIN:** `{prod['asin']}`  |  **Unidades:** {prod['units']}")
                                key_msg = f"supplier_msg_{prod['asin']}"
                                if key_msg not in st.session_state:
                                    st.session_state[key_msg] = ""
                                if st.button(f"Generar mensaje con IA", key=f"generar_ia_{prod['asin']}"):
                                    prompt = (
                                        f"Redacta un correo profesional para solicitar información a un proveedor sobre el siguiente producto de Amazon:\n"
                                        f"- Título: {prod['title']}\n- ASIN: {prod['asin']}\n\n"
                                        "El correo debe ser cordial y solicitar precios, condiciones de envío y plazos de entrega."
                                    )
                                    try:
                                        openai.api_key = os.getenv("OPENAI_API_KEY")
                                        response = openai.ChatCompletion.create(
                                            model="gpt-3.5-turbo",
                                            messages=[
                                                {"role": "system", "content": "Eres un agente experto en compras FBA."},
                                                {"role": "user", "content": prompt}
                                            ]
                                        )
                                        ai_msg = response["choices"][0]["message"]["content"].strip()
                                        st.session_state[key_msg] = ai_msg
                                    except Exception as e:
                                        st.error(f"Error generando mensaje con IA: {e}")
                                msg = st.text_area(f"Mensaje a proveedor (editable) - {prod['asin']}", st.session_state[key_msg], height=200, key=f"textarea_{prod['asin']}")
                                st.session_state[key_msg] = msg
                                col1, col2 = st.columns(2)
                                with col1:
                                    if st.button("Guardar mensaje", key=f"guardar_{prod['asin']}"):
                                        st.success("Mensaje guardado")
                                with col2:
                                    if st.button("Enviar mensaje", key=f"enviar_{prod['asin']}"):
                                        st.success("Mensaje enviado (simulado)")
                    else:
                        display_csv(out_path, out_title)
                else:
                    prereqs_met = False
            else:
                prereqs_met = False

    # Mostrar mensajes de proveedores y resumen al final
    show_messages(fba_agent.OUTPUTS["supplier_contact_generator"])
    st.header("Summary")
    summary_screen()


def run_step_ui(label: str, script: str, budget: float, dev_mode: bool) -> None:
    """Execute a module and display the results in the UI."""
    import os
    import subprocess
    # Si dev_mode está activo, asegurarse de que los datos mock existen
    if dev_mode:
        data_files = [
            'data/discovery_results.csv',
            'data/market_analysis_results.csv',
            'data/profitability_estimation_results.csv',
            'data/demand_forecast_results.csv',
            'data/supplier_selection_results.csv',
        ]
        missing = [f for f in data_files if not os.path.exists(f)]
        if missing:
            subprocess.run(['python', 'mock_data.py'], encoding='utf-8')
    # --- NUEVO: Aviso si los archivos de resultados existen antes de correr módulos ---
    output_path = None
    for mod_label, mod_script in MODULES:
        if mod_label == label:
            idx = MODULES.index((mod_label, mod_script))
            if idx < len(fba_agent.OUTPUTS):
                output_path = list(fba_agent.OUTPUTS.values())[idx]
            break
    if output_path and os.path.exists(output_path):
        st.info(t('results_file_exists', output_path=output_path))
        if st.button(t('reset_pipeline')):
            with st.spinner(t('resetting_pipeline')):
                result = subprocess.run(['python', 'reset_pipeline.py'], capture_output=True, text=True)
            st.success(t('pipeline_reset'))
            st.code(result.stdout + '\n' + result.stderr)
    # --- Instalar requirements solo si falta algo ---
    if not check_requirements_installed():
        with st.spinner(t('installing_deps')):
            pip_log = run_prepare_environment()
        with st.expander(t('env_setup_log'), expanded=True):
            st.code(pip_log)
    # Ejecutar el script con el flag --mock si corresponde
    cmd = ['python', script]
    if dev_mode:
        cmd.append('--mock')
    subprocess.run(cmd, encoding='utf-8')
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
    stdout, stderr = proc.communicate()
    returncode = proc.returncode
    log = stdout + '\n' + stderr
    st.session_state.logs[label] = stdout if returncode == 0 else stderr
    if returncode == 0:
        st.success(t('step_success', label=label))
        commit_and_push_changes(f"Auto: updated results after {label}")
    else:
        st.error(t('step_failed', label=label))
    with st.expander("Step Log", expanded=returncode != 0 and dev_mode):
        st.code(log)


def run_headless(auto: bool = False) -> None:
    cmd = [sys.executable, "fba_agent.py"]
    if auto:
        cmd.append("--auto")
    subprocess.run(cmd, check=False)


def parse_cli() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="FBA Streamlit UI", add_help=False)
    parser.add_argument("--headless", action="store_true", help="run without UI")
    parser.add_argument("--auto", action="store_true", help="run pipeline automatically")
    args, _ = parser.parse_known_args()
    return args


def display_supplier_selection():
    path = fba_agent.OUTPUTS["supplier_selection"]
    log_path = "log.txt"
    if not file_has_content(path):
        # Buscar el último mensaje relevante en el log
        msg = None
        if os.path.exists(log_path):
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if (
                        f"No se encontraron productos viables para proveedores." in line or
                        "No se encontraron productos para analizar." in line or
                        "No se encontraron resultados viables en el análisis de mercado." in line or
                        "No se encontraron productos viables en la estimación de rentabilidad." in line or
                        "No se encontraron resultados viables en la estimación de demanda." in line or
                        "No se encontraron productos en el descubrimiento." in line
                    ):
                        msg_lines = [line.strip()]
                        idx = lines.index(line)
                        for extra in lines[idx+1:idx+5]:
                            if (
                                extra.strip().startswith("Total ") or
                                extra.strip().startswith("Descartad")
                            ):
                                msg_lines.append(extra.strip())
                            else:
                                break
                        msg = "\n".join(msg_lines)
                        break
        if msg:
            st.error(msg)
        else:
            st.warning("No se encontraron proveedores para los productos seleccionados. Consulta el log para más detalles.")
        return
    df = pd.read_csv(path)
    if df.empty:
        st.warning("No se encontraron proveedores para los productos seleccionados. Revisa los filtros y los datos de entrada.")
        return
    st.subheader("Selección de Proveedores")
    # Métricas resumen
    total_cost = df["total_cost"].sum() if "total_cost" in df else 0
    total_profit = df["estimated_profit"].sum() if "estimated_profit" in df else 0
    st.metric("Coste total", f"${total_cost:,.2f}")
    st.metric("Beneficio estimado", f"${total_profit:,.2f}")
    st.dataframe(df)


def check_requirements_installed() -> bool:
    """Devuelve True si todos los paquetes de requirements.txt están instalados, False si falta alguno."""
    import importlib
    import pkg_resources
    import sys
    req_path = os.path.join(ROOT_DIR, "requirements.txt")
    if not os.path.exists(req_path):
        return True  # Si no hay requirements, asumimos que está bien
    with open(req_path) as f:
        lines = [l.strip() for l in f if l.strip() and not l.startswith('#')]
    pkgs = []
    for l in lines:
        if '==' in l:
            pkgs.append(l.split('==')[0])
        elif '>=' in l:
            pkgs.append(l.split('>=')[0])
        elif l:
            pkgs.append(l.split()[0])
    for pkg in pkgs:
        try:
            importlib.import_module(pkg)
        except Exception:
            return False
    return True


if __name__ == "__main__":
    args = parse_cli()
    if args.headless:
        run_headless(auto=args.auto)
    else:
        pipeline_ui()
