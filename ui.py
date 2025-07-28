import argparse
import os
import sys
import subprocess
from typing import List, Tuple, Dict
import openai
import csv
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
from statsmodels.tsa.holtwinters import ExponentialSmoothing
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
import datetime
import base64
import tempfile
import smtplib
from email.message import EmailMessage
import importlib
import pkg_resources
import io
import plotly.figure_factory as ff
from prophet import Prophet
from sklearn.metrics import mean_absolute_error, mean_squared_error
import plotly.graph_objects as go
import kdp_module

# Absolute path to the repository root so modules are executed
# consistently regardless of the working directory.
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))

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

FRIENDLY_LABELS = {
    'en': {
        'Run Product Discovery': 'Product Discovery',
        'Run Market Analysis': 'Market Analysis',
        'Run Profitability Estimation': 'Profitability Estimation',
        'Run Demand Forecast': 'Demand Forecast',
        'Run Supplier Selection': 'Supplier Selection',
        'Generate Supplier Emails': 'Supplier Emails',
        'Simulate Pricing Strategy': 'Pricing Simulator',
        'Manage Inventory': 'Inventory Management',
    },
    'es': {
        'Run Product Discovery': 'Descubrimiento de productos',
        'Run Market Analysis': 'Análisis de mercado',
        'Run Profitability Estimation': 'Estimación de rentabilidad',
        'Run Demand Forecast': 'Predicción de demanda',
        'Run Supplier Selection': 'Selección de proveedores',
        'Generate Supplier Emails': 'Emails a proveedores',
        'Simulate Pricing Strategy': 'Simulador de precios',
        'Manage Inventory': 'Gestión de inventario',
    }
}

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
        'supplier_selection_title': 'Supplier Selection',
        'configuration': 'Configuration',
        'dev_mode': 'Developer mode (mock)',
        'budget': 'Startup Budget (USD)',
        'api_keys_section': 'API Keys & Email Provider',
        'save_api_keys': 'Save API Keys',
        'api_keys_saved': 'API keys saved!',
        'unsaved_changes': 'You have unsaved changes.',
        'activate_email_agent': 'Activate email agent',
        'connecting_email': 'Connecting to email...',
        'latest_emails': 'Latest emails:',
        'from': 'From',
        'subject': 'Subject',
        'date': 'Date',
        'email_agent_instructions': 'Email agent instructions',
        'email_instruction_placeholder': 'Instruction (e.g. send a test email to address x)',
        'send_instruction': 'Send instruction to agent',
        'test_email_sent': 'Test email sent to {to_addr}.',
        'test_email_error': 'Error sending email: {error}',
        'instruction_not_recognized': 'Instruction not recognized. Currently only supported: "send a test email to address x".',
        'email_address': 'Email Address',
        'email_password': 'Email Password / App Password',
        'imap_server': 'IMAP server',
        'smtp_server': 'SMTP server',
        'smtp_port': 'SMTP port',
        'last_emails': 'Last emails:',
        'success': 'Success',
        'error': 'Error',
        'warning': 'Warning',
        'info': 'Info',
        'supplier_message_editor': 'Supplier Message Editor',
        'select_product': 'Select product',
        'message': 'Message',
        'instruction_for_chatgpt': "Instruction for ChatGPT (e.g. 'Make it more formal, add a professional signature')",
        'save_message': 'Save message',
        'send_message': 'Send message',
        'improve_with_chatgpt': 'Improve with ChatGPT',
        'chatgpt_suggestion': 'ChatGPT suggestion',
        'replace_with_suggestion': 'Replace with suggestion',
        'message_saved': 'Message saved.',
        'message_sent': 'Message for {name} sent (simulated).',
        'message_replaced': 'Message replaced with ChatGPT suggestion.',
        'email_provider': 'Email Provider',
        'summary': 'Summary',
        'step_log': 'Step Log',
        'log': 'Log',
        'supplier_messages': 'Supplier Messages',
        'editable': 'editable',
        'email_template_example': 'Email template example',
        'no_product_selected': 'No product selected.',
        'reset_pipeline_confirm': 'Reset Pipeline (delete all generated data)',
        'env_setup_log': 'Environment Setup Log',
        'amazon_fba_ai_agent': 'Amazon FBA AI Agent',
        'running_full_pipeline': 'Running the full pipeline...',
        'demand_analysis': 'Demand Analysis',
        'estimated_demand': 'Estimated Demand',
        'real_demand': 'Real Demand (units sold)',
        'forecast_error': 'Forecast Error',
        'correction_factor': 'Correction Factor',
        'suggested_next_forecast': 'Suggested Next Forecast',
        'select_forecasting_method': 'Select forecasting method',
        'correction_factor_method': 'Correction Factor Method:',
        'not_enough_data': 'Not enough data to compute demand adjustment.',
        'exp_smoothing': 'Simple Exponential Smoothing (α=0.5):',
        'holt_winters_forecast': 'Holt-Winters (Seasonal) Forecast:',
        'prophet_forecast': 'Prophet (AI) Forecast:',
        'no_sales_history': 'No sales history available for this product.',
        'not_enough_data_hw': 'Not enough data for Holt-Winters (need at least 6 periods).',
        'not_enough_data_prophet': 'Not enough data for Prophet (need at least 6 periods).',
        'description': 'Description:',
        'when_to_use': 'When to use:',
        'select_method': 'Select forecasting method',
        'correction_desc': 'Adjusts the forecast by multiplying by the ratio between real and estimated demand. Useful for quick corrections when there is no trend or seasonality.',
        'correction_rec': 'Recommended if you have little historical data or demand is stable.',
        'exp_smoothing_desc': 'Simple exponential smoothing: combines the last real demand and the last forecast. Useful for series without trend or seasonality.',
        'exp_smoothing_rec': 'Recommended for products with stable demand and no seasonal patterns.',
        'holt_winters_desc': 'Holt-Winters: advanced model that adjusts forecasts considering trend and seasonality. Requires several periods of data.',
        'holt_winters_rec': 'Recommended if you detect seasonal peaks or clear trends in sales.',
        'prophet_desc': 'Prophet (Meta): AI model for time series, robust to seasonality and outliers. Easy to use and very interpretable.',
        'prophet_rec': 'Recommended to compare with classic methods and validate forecast robustness.',
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
        'supplier_selection_title': 'Selección de Proveedores',
        'configuration': 'Configuración',
        'dev_mode': 'Modo desarrollador (mock)',
        'budget': 'Presupuesto inicial (USD)',
        'api_keys_section': 'Llaves API y proveedor de email',
        'save_api_keys': 'Guardar llaves API',
        'api_keys_saved': '¡Llaves API guardadas!',
        'unsaved_changes': 'Tienes cambios sin guardar.',
        'activate_email_agent': 'Activar agente de email',
        'connecting_email': 'Conectando al correo...',
        'latest_emails': 'Últimos emails:',
        'from': 'De',
        'subject': 'Asunto',
        'date': 'Fecha',
        'email_agent_instructions': 'Instrucciones al agente de email',
        'email_instruction_placeholder': 'Instrucción (ej: manda un correo de prueba a la direccion x)',
        'send_instruction': 'Enviar instrucción al agente',
        'test_email_sent': 'Correo de prueba enviado a {to_addr}.',
        'test_email_error': 'Error al enviar correo: {error}',
        'instruction_not_recognized': 'Instrucción no reconocida. Por ahora solo se soporta: "manda un correo de prueba a la direccion x".',
        'email_address': 'Dirección de correo',
        'email_password': 'Contraseña de correo / App Password',
        'imap_server': 'Servidor IMAP',
        'smtp_server': 'Servidor SMTP',
        'smtp_port': 'Puerto SMTP',
        'last_emails': 'Últimos emails:',
        'success': 'Éxito',
        'error': 'Error',
        'warning': 'Aviso',
        'info': 'Info',
        'supplier_message_editor': 'Editor de mensajes a proveedores',
        'select_product': 'Selecciona producto',
        'message': 'Mensaje',
        'instruction_for_chatgpt': "Instrucción para ChatGPT (ej: 'Hazlo más formal, añade una firma profesional')",
        'save_message': 'Guardar mensaje',
        'send_message': 'Enviar mensaje',
        'improve_with_chatgpt': 'Mejorar con ChatGPT',
        'chatgpt_suggestion': 'Sugerencia de ChatGPT',
        'replace_with_suggestion': 'Reemplazar por sugerencia',
        'message_saved': 'Mensaje guardado.',
        'message_sent': 'Mensaje para {name} enviado (simulado).',
        'message_replaced': 'Mensaje reemplazado por sugerencia de ChatGPT.',
        'email_provider': 'Proveedor de email',
        'summary': 'Resumen',
        'step_log': 'Log del paso',
        'log': 'Log',
        'supplier_messages': 'Mensajes a proveedores',
        'editable': 'editable',
        'email_template_example': 'Ejemplo de plantilla de email',
        'no_product_selected': 'Ningún producto seleccionado.',
        'reset_pipeline_confirm': 'Reiniciar Pipeline (eliminar todos los datos generados)',
        'env_setup_log': 'Log de instalación del entorno',
        'amazon_fba_ai_agent': 'Amazon FBA AI Agent',
        'running_full_pipeline': 'Ejecutando toda la pipeline...',
        'demand_analysis': 'Análisis de demanda',
        'estimated_demand': 'Demanda estimada',
        'real_demand': 'Demanda real (unidades vendidas)',
        'forecast_error': 'Error de previsión',
        'correction_factor': 'Factor de corrección',
        'suggested_next_forecast': 'Siguiente previsión sugerida',
        'select_forecasting_method': 'Selecciona método de forecasting',
        'correction_factor_method': 'Método de factor de corrección:',
        'not_enough_data': 'No hay suficientes datos para ajustar la demanda.',
        'exp_smoothing': 'Suavizado exponencial simple (α=0.5):',
        'holt_winters_forecast': 'Previsión Holt-Winters (estacional):',
        'prophet_forecast': 'Previsión Prophet (IA):',
        'no_sales_history': 'No hay historial de ventas para este producto.',
        'not_enough_data_hw': 'No hay suficientes datos para Holt-Winters (mínimo 6 periodos).',
        'not_enough_data_prophet': 'No hay suficientes datos para Prophet (mínimo 6 periodos).',
        'description': 'Descripción:',
        'when_to_use': 'Cuándo usar:',
        'select_method': 'Selecciona método de forecasting',
        'correction_desc': 'Ajusta la previsión multiplicando por el ratio entre demanda real y estimada. Útil para correcciones rápidas cuando no hay tendencia ni estacionalidad.',
        'correction_rec': 'Recomendado si tienes pocos datos históricos o la demanda es estable.',
        'exp_smoothing_desc': 'Suavizado exponencial simple: combina la última demanda real y la última previsión. Útil para series sin tendencia ni estacionalidad.',
        'exp_smoothing_rec': 'Recomendado para productos con demanda estable y sin patrones estacionales.',
        'holt_winters_desc': 'Holt-Winters: modelo avanzado que ajusta previsiones considerando tendencia y estacionalidad. Requiere varios periodos de datos.',
        'holt_winters_rec': 'Recomendado si detectas picos estacionales o tendencias claras en las ventas.',
        'prophet_desc': 'Prophet (Meta): modelo de IA para series temporales, robusto ante estacionalidad y outliers. Fácil de usar y muy interpretativo.',
        'prophet_rec': 'Recomendado para comparar con métodos clásicos y validar la robustez del forecast.',
    }
}

CONFIG_PATH = "config.json"
CONFIG_EXAMPLE_PATH = "config.example.json"
API_KEYS = [
    ("serpapi_key", "SerpAPI Key"),
    ("keepa_key", "Keepa Key"),
    ("helium10_key", "Helium 10 Key"),
    ("openai_key", "OpenAI Key"),
    ("gmail_key", "Gmail Key"),
    ("amazon_key", "Amazon Key"),
]
EMAIL_PROVIDERS = ["gmail", "outlook", "custom_smtp"]

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
    st.subheader(t('supplier_messages'))
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
            st.success(t('message_saved'))


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
    st.metric(t('total_profit'), f"${total_profit:,.2f}")
    # --- NUEVO: Comprobar si plotly está instalado antes de graficar ---
    try:
        if "roi" in df.columns and "asin" in df.columns:
            fig = px.bar(df, x="asin", y="roi", title=t('roi_per_product'))
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
    # Inicialización universal para evitar errores de variable no definida
    stock_in = 0
    stock_out = 0
    stock_actual = 0
    st.title(t('amazon_fba_ai_agent'))
    # --- Selector de idioma en la parte superior derecha ---
    if 'lang' not in st.session_state:
        st.session_state['lang'] = 'en'
    lang = st.sidebar.selectbox('Language', options=[('en', 'English'), ('es', 'Español')], format_func=lambda x: x[1], index=0 if st.session_state['lang']=='en' else 1)
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

    # --- Configuración de alertas en la sidebar ---
    with st.sidebar.expander(t('configuration'), expanded=True):
        # Cargar config actual
        config = load_config()
        # Developer mode y budget
        dev_mode = st.checkbox(t('dev_mode'), value=st.session_state.dev_mode)
        budget = st.number_input(
        t('budget'), min_value=100.0, value=st.session_state.budget, step=100.0
    )
        # API Keys
        st.markdown('**API Keys**')
        api_key_values = {}
        for key, label in API_KEYS:
            is_sensitive = 'key' in key or 'password' in key
            api_key_values[key] = st.text_input(label, value=config.get(key, ''), type='password' if is_sensitive else 'default', key=f'api_{key}')
        # Email provider
        st.markdown('**Email Provider**')
        email_provider = st.selectbox(t('email_provider'), EMAIL_PROVIDERS, index=EMAIL_PROVIDERS.index(config.get('email_provider', 'gmail')) if config.get('email_provider', 'gmail') in EMAIL_PROVIDERS else 0, key='email_provider')
        email_address = st.text_input(t('email_address'), value=config.get('email_address', ''), key='email_address')
        email_password = st.text_input(t('email_password'), value=config.get('email_password', ''), type='password', key='email_password')
        smtp_server = st.text_input(t('smtp_server'), value=config.get('smtp_server', 'smtp.gmail.com'), key='smtp_server')
        smtp_port = st.number_input(t('smtp_port'), min_value=1, max_value=65535, value=int(config.get('smtp_port', 587)), step=1, key='smtp_port')
        imap_server = st.text_input(t('imap_server'), value=config.get('imap_server', 'imap.gmail.com'), key='imap_server')
        # Botón guardar
        if st.button(t('save_api_keys')):
            # Actualizar config
            config['dev_mode'] = dev_mode
            config['budget'] = budget
            for key in api_key_values:
                config[key] = api_key_values[key]
            config['email_provider'] = email_provider
            config['email_address'] = email_address
            config['email_password'] = email_password
            config['smtp_server'] = smtp_server
            config['smtp_port'] = smtp_port
            config['imap_server'] = imap_server
            save_config(config)
            # Actualizar session_state
            st.session_state.dev_mode = dev_mode
            st.session_state.budget = budget
            for key in api_key_values:
                st.session_state[key] = api_key_values[key]
            st.session_state.email_provider = email_provider
            st.session_state.email_address = email_address
            st.session_state.email_password = email_password
            st.session_state.smtp_server = smtp_server
            st.session_state.smtp_port = smtp_port
            st.session_state.imap_server = imap_server
            st.success(t('api_keys_saved'))
    # --- NUEVO: Tabs principales ---
    tabs = st.tabs(["FBA", "Product Selection", "Product Tracker", "E-mail Management", "KDP"])
    with tabs[0]:
        # --- Botones principales arriba y en horizontal ---
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button(t('run_tests')):
                with st.spinner(t('running_tests')):
                    out, code = run_test_all()
                with st.expander(t('test_output'), expanded=code != 0):
                    st.code(out)
                st.session_state.tests_ok = code == 0
                if st.session_state.tests_ok:
                    st.success(t('tests_passed'))
                else:
                    st.error(t('tests_failed'))
        with col2:
            if st.button(t('validate_pipeline')):
                with st.spinner(t('validating_pipeline')):
                    vout, vcode = run_validate_all()
                with st.expander(t('validation_output'), expanded=vcode != 0):
                    st.code(vout)
                st.session_state.validation_ok = vcode == 0
                if st.session_state.validation_ok:
                    st.success(t('validation_passed'))
                else:
                    st.error(t('validation_failed'))
        with col3:
            if st.button(t('run_all')):
                with st.spinner(t('running_full_pipeline')):
                    run_headless(auto=True)
                st.success(t('pipeline_completed'))
        st.divider()
        # --- SOLO aquí va el bucle de los módulos y la pipeline ---
        lang = st.session_state.get('lang', 'en')
        disabled = not (st.session_state.tests_ok and st.session_state.validation_ok)
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
            friendly_label = FRIENDLY_LABELS[lang].get(label, label)
            with st.expander(friendly_label, expanded=False):
                is_step_disabled = disabled or not prereqs_met
                if st.button(friendly_label, key=f"btn_fba_{script}_{idx}", disabled=is_step_disabled):
                    run_step_ui(label, script, st.session_state.budget, st.session_state.dev_mode)
                if st.session_state.dev_mode and st.session_state.logs[label]:
                    st.text_area(t('step_log'), st.session_state.logs[label], height=150)
                # --- SIEMPRE mostrar el editor de mensajes a proveedores en el panel correspondiente ---
                if label == "Generate Supplier Emails":
                    supplier_messages_dir = "supplier_messages"
                    product_files = [f for f in sorted(os.listdir(supplier_messages_dir)) if f.endswith('.txt')] if os.path.exists(supplier_messages_dir) else []
                    product_options = [(f, f) for f in product_files]
                    st.subheader(t('supplier_message_editor'))
                    selected_product = st.selectbox(
                        t('select_product'), options=product_options, format_func=lambda x: x[0] if x else "",
                        index=0 if product_options else None, key="product_selector"
                    ) if product_options else None
                    if selected_product:
                        msg_path = os.path.join(supplier_messages_dir, selected_product[0])
                        try:
                            with open(msg_path, "r", encoding="utf-8") as f:
                                content = f.read()
                        except Exception:
                            content = ""
                    else:
                        content = "ASIN: B0EXAMPLE\nTitle: Example Product\n\nDear Supplier,\nPlease provide your best quote for 100 units of Example Product."
                    editor_key = f"editor_{selected_product[0]}" if selected_product else "editor_template"
                    edited_msg = st.text_area(t('message'), content, height=200, key=editor_key, disabled=not selected_product)
                    instruction_key = f"instruction_{selected_product[0]}" if selected_product else "instruction_template"
                    instruction = st.text_input(t('instruction_for_chatgpt'), key=instruction_key, disabled=not selected_product)
                    col_btn1, col_btn2, col_btn3 = st.columns([1,1,1])
                    with col_btn1:
                        if st.button(t('save_message'), key=f"save_{selected_product[0]}" if selected_product else "save_template", disabled=not selected_product):
                            with open(msg_path, "w", encoding="utf-8") as f:
                                f.write(st.session_state[editor_key])
                            st.success(t('message_saved'))
                    with col_btn2:
                        if st.button(t('send_message'), key=f"send_{selected_product[0]}" if selected_product else "send_template", disabled=not selected_product):
                            st.success(t('message_sent', name=selected_product[0]) if selected_product else t('no_product_selected'))
                    with col_btn3:
                        if st.button(t('improve_with_chatgpt'), key=f"improve_{selected_product[0]}" if selected_product else "improve_template", disabled=not selected_product):
                            import openai
                            client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
                            asin = selected_product[0] if selected_product else "B0EXAMPLE"
                            title = ""
                            for line in content.splitlines():
                                if line.lower().startswith("title:"):
                                    title = line.split(":",1)[-1].strip()
                                    break
                            prompt = f"Product ASIN: {asin}\nProduct Title: {title}\n\nOriginal message:\n{edited_msg}\n\nInstruction: {instruction}\n\nRewrite the message accordingly, making sure it is appropriate for the product."
                            improved = None
                            try:
                                response = client.chat.completions.create(
                                    model="gpt-3.5-turbo",
                                    messages=[
                                        {"role": "system", "content": "You are an expert in writing professional supplier emails for Amazon FBA sourcing. Always include a suitable signature and adapt the message to the product."},
                                        {"role": "user", "content": prompt}
                                    ]
                                )
                                improved = response.choices[0].message.content.strip()
                                st.session_state[f"improved_{selected_product[0]}"] = improved
                                st.success(t('chatgpt_suggestion'))
                            except Exception as e:
                                st.error(str(e))
                            if improved:
                                st.text_area(t('chatgpt_suggestion'), improved, height=200, key=f"suggestion_{selected_product[0]}" if selected_product else "suggestion_template")
                                if st.button(t('replace_with_suggestion'), key=f"replace_{selected_product[0]}" if selected_product else "replace_template"):
                                    st.session_state[editor_key] = improved
                                    st.success(t('message_replaced'))
                # --- FIN bloque editor SIEMPRE visible ---
                if idx < len(output_files):
                    out_title, out_path = output_files[idx]
                    if label == "Run Supplier Selection":
                        if os.path.exists(out_path) and file_has_content(out_path):
                            display_supplier_selection()
                    elif label not in ("Generate Supplier Emails",):
                        if os.path.exists(out_path) and file_has_content(out_path):
                            display_csv(out_path, out_title)
                        else:
                            prereqs_met = False
                else:
                    prereqs_met = False
        # Mostrar solo el resumen al final (los mensajes ya están en el nuevo bloque)
        st.header(t('summary'))
        summary_screen()
    with tabs[1]:
        st.header("Product Selection")
        # Cargar productos investigados
        import pandas as pd
        products_path = "data/discovery_results.csv"
        if not os.path.exists(products_path):
            products_path = "data/product_results.csv"
        if os.path.exists(products_path):
            df_products = pd.read_csv(products_path)
            if 'ASIN' not in df_products.columns and 'asin' in df_products.columns:
                df_products['ASIN'] = df_products['asin']
            if 'Title' not in df_products.columns and 'title' in df_products.columns:
                df_products['Title'] = df_products['title']
            st.markdown("**Investigated Products:**")
            # Inicializar selección en session_state
            if 'selected_products' not in st.session_state:
                st.session_state['selected_products'] = set(df_products['ASIN'].tolist())
            # Mostrar tabla con checkboxes
            selected = []
            for i, row in df_products.iterrows():
                asin = row['ASIN']
                title = row.get('Title', asin)
                checked = asin in st.session_state['selected_products']
                if st.checkbox(f"{title} ({asin})", value=checked, key=f"select_{asin}"):
                    selected.append(asin)
            st.session_state['selected_products'] = set(selected)
            st.success(f"Selected products: {', '.join(st.session_state['selected_products'])}")
        else:
            st.info("No investigated products found. Run the pipeline or generate mock data.")
    with tabs[2]:
        st.header("Product Tracker")
        # --- Inicializar stock_in, stock_out y stock_actual a 0 al principio del bloque Product Tracker ---
        stock_in = 0
        stock_out = 0
        stock_actual = 0
        # --- Generación automática de pedidos sugeridos para todos los productos ---
        st.header("Bulk Order Suggestions")
        selected_asins = list(st.session_state.get('selected_products', []))
        if not selected_asins:
            st.warning("No products selected. Please select products in the 'Product Selection' tab.")
        else:
            if st.button("Generate suggested orders for all products", key="generate_bulk_orders"):
                # Cargar productos desde el histórico de ventas
                sales_path = "data/sales_history.csv"
                if os.path.exists(sales_path):
                    df_sales_hist = pd.read_csv(sales_path)
                    all_asins = [asin for asin in df_sales_hist['ASIN'].unique() if asin in selected_asins]
                else:
                    all_asins = selected_asins
                # Cargar datos de productos
                try:
                    df_products = pd.read_csv("data/discovery_results.csv")
                except Exception:
                    df_products = pd.DataFrame()
                # Para cada producto seleccionado, calcular sugerencia de pedido y preparar borrador de email
                for asin in all_asins:
                    # Buscar datos del producto
                    product_data = df_products[df_products['ASIN'] == asin].iloc[0].to_dict() if not df_products.empty and asin in df_products['ASIN'].values else {'ASIN': asin, 'Title': asin}
                    # Cargar movimientos de inventario
                    save_movements_path = "data/inventory_movements_saved.csv"
                    if os.path.exists(save_movements_path):
                        try:
                            df_mov = pd.read_csv(save_movements_path)
                            movs = df_mov[df_mov['ASIN'] == asin].copy()
                            stock_in = 0
                            stock_out = 0
                            stock_actual = 0
                            if 'movs' in locals() and hasattr(movs, 'empty') and not movs.empty:
                                stock_in = movs[movs['Type']=='IN']['Quantity'].sum()
                                stock_out = movs[movs['Type']=='OUT']['Quantity'].sum()
                                stock_actual = stock_in - stock_out
                        except Exception:
                            movs = pd.DataFrame(columns=['ASIN','Date','Type','Quantity','Note'])
                            stock_in = 0
                            stock_out = 0
                            stock_actual = 0
                            if 'movs' in locals() and hasattr(movs, 'empty') and not movs.empty:
                                stock_in = movs[movs['Type']=='IN']['Quantity'].sum()
                                stock_out = movs[movs['Type']=='OUT']['Quantity'].sum()
                                stock_actual = stock_in - stock_out
                    else:
                        movs = pd.DataFrame(columns=['ASIN','Date','Type','Quantity','Note'])
                        stock_in = 0
                        stock_out = 0
                        stock_actual = 0
                        if 'movs' in locals() and hasattr(movs, 'empty') and not movs.empty:
                            stock_in = movs[movs['Type']=='IN']['Quantity'].sum()
                            stock_out = movs[movs['Type']=='OUT']['Quantity'].sum()
                            stock_actual = stock_in - stock_out
                    # --- Inicializar stock_in, stock_out y stock_actual a 0 de forma universal (scope externo del bloque de detalles del producto) ---
                    stock_in = 0
                    stock_out = 0
                    stock_actual = 0
                    if 'movs' in locals() and hasattr(movs, 'empty') and not movs.empty:
                        stock_in = movs[movs['Type']=='IN']['Quantity'].sum()
                        stock_out = movs[movs['Type']=='OUT']['Quantity'].sum()
                        stock_actual = stock_in - stock_out
                    # Demanda estimada
                    df_sales_prod = pd.read_csv(sales_path)
                    df_sales_prod = df_sales_prod[df_sales_prod['ASIN'] == asin]
                    if not df_sales_prod.empty:
                        last_month = df_sales_prod['Date'].max()[:7]
                        estimated_demand = df_sales_prod[df_sales_prod['Date'].str.startswith(last_month)]['Units_Sold'].sum()
                    else:
                        estimated_demand = 0
                    daily_demand = estimated_demand / 30 if estimated_demand else 0.1
                    # Lead time y margen (usar valores por defecto o de session_state)
                    lead_time = 21
                    safety_margin = 5
                    # Fecha de agotamiento
                    days_until_oos = int(stock_actual / daily_demand) if daily_demand > 0 else 0
                    today = pd.Timestamp.today().normalize()
                    date_oos = today + pd.Timedelta(days=days_until_oos) if days_until_oos else today
                    date_order = date_oos - pd.Timedelta(days=lead_time + safety_margin)
                    qty_suggested = int(daily_demand * lead_time * 1.5)
                    # Solo sugerir pedido si la fecha de pedido es hoy o pasada y la cantidad es positiva
                    if qty_suggested > 0 and date_order <= today:
                        email_key = f'order_email_{asin}_bulk'
                        supplier = product_data.get('Supplier', 'Supplier')
                        product_title = product_data.get('Title', asin)
                        supplier_emails = []
                        if 'Supplier_Emails' in product_data and product_data['Supplier_Emails']:
                            supplier_emails = [e.strip() for e in str(product_data['Supplier_Emails']).split(',') if e.strip()]
                        elif 'Supplier_Email' in product_data and product_data['Supplier_Email']:
                            supplier_emails = [product_data['Supplier_Email']]
                        to_email = supplier_emails[0] if supplier_emails else ''
                        subject = f"Purchase Order for {product_title} (ASIN: {asin})"
                        body = (
                            f"Dear {supplier},\n\n"
                            f"We would like to place a new order for the following product:\n"
                            f"- Product: {product_title}\n"
                            f"- ASIN: {asin}\n"
                            f"- Quantity: {qty_suggested} units\n"
                            f"- Expected arrival: before {date_oos.date()}\n\n"
                            f"Please confirm availability, lead time, and provide a proforma invoice.\n\n"
                            f"Best regards,\nAmazon FBA Team"
                        )
                        st.session_state[email_key] = {
                            'subject': subject,
                            'body': body,
                            'to_email': to_email,
                            'date_order': str(date_order.date()),
                            'qty_suggested': qty_suggested,
                            'asin': asin,
                            'product_title': product_title
                        }
            st.success("Bulk order suggestions generated.")
        # Mostrar tabla resumen de pedidos sugeridos
        bulk_emails = [v for k,v in st.session_state.items() if k.startswith('order_email_') and '_bulk' in k]
        if bulk_emails:
            st.subheader("Suggested Orders Table")
            import pandas as pd
            df_bulk = pd.DataFrame(bulk_emails)
            st.dataframe(df_bulk[['asin','product_title','qty_suggested','date_order','to_email']])
            for order_email in bulk_emails:
                st.markdown(f"---\n**Product:** {order_email['product_title']} ({order_email['asin']})\n**Quantity:** {order_email['qty_suggested']}\n**Order date:** {order_email['date_order']}\n**To:** {order_email['to_email']}")
                subject = st.text_input("Subject", value=order_email['subject'], key=f"bulk_subject_{order_email['asin']}")
                body = st.text_area("Body", value=order_email['body'], height=150, key=f"bulk_body_{order_email['asin']}")
                to_email = st.text_input("To (supplier email)", value=order_email['to_email'], key=f"bulk_to_{order_email['asin']}")
                today_str = str(pd.Timestamp.today().date())
                if order_email['date_order'] <= today_str:
                    if st.button("Send Order Email", key=f"bulk_send_{order_email['asin']}"):
                        import smtplib
                        from email.message import EmailMessage
                        config = load_config()
                        smtp_server = config.get('smtp_server', 'smtp.gmail.com')
                        smtp_port = int(config.get('smtp_port', 587))
                        smtp_user = config.get('email_address', '')
                        smtp_pass = config.get('email_password', '')
                        msg = EmailMessage()
                        msg['Subject'] = subject
                        msg['From'] = smtp_user
                        msg['To'] = to_email
                        msg.set_content(body)
                        try:
                            with smtplib.SMTP(smtp_server, smtp_port) as server:
                                server.starttls()
                                server.login(smtp_user, smtp_pass)
                                server.send_message(msg)
                            st.success(f"Order email sent to {to_email}.")
                        except Exception as e:
                            st.error(f"Error sending email: {e}")
                else:
                    st.info(f"Order email scheduled for {order_email['date_order']}. It will be ready to send on that date.")
        # Solo usar mock data en modo desarrollador
        if st.session_state.get('dev_mode', False):
            # 1. Selector de producto
            product_options = []
            product_data = None
            try:
                df_products = pd.read_csv("data/discovery_results.csv")
                if not df_products.empty:
                    # Filtrar solo productos seleccionados
                    selected_asins = list(st.session_state.get('selected_products', []))
                    product_options = [(row['ASIN'], row['Title']) for _, row in df_products.iterrows() if 'ASIN' in row and 'Title' in row and row['ASIN'] in selected_asins]
            except Exception:
                pass
            selected_product = None
            if product_options:
                selected_product = st.selectbox("Select product", options=product_options, format_func=lambda x: f"{x[1]} ({x[0]})", key="tracker_product_selector")
                product_data = next((row for row in df_products.to_dict('records') if row['ASIN'] == selected_product[0]), None)
            else:
                st.info("No products available. Select products in the 'Product Selection' tab.")
            if selected_product and product_data:
                # 2. Panel resumen general
                st.subheader("Product Summary")
                st.markdown(f"**ASIN:** {product_data['ASIN']}")
                st.markdown(f"**Title:** {product_data['Title']}")
                st.markdown(f"**Category:** {product_data.get('Category','')}")
                st.markdown(f"**Supplier:** {product_data.get('Supplier','')}")
                st.markdown(f"**Status:** {product_data.get('Status','')}")
                st.markdown(f"**Arrival Date:** {product_data.get('Arrival_Date','')}")
                # 3. Correos relacionados
                st.subheader("Related Emails")
                try:
                    df_emails = pd.read_csv("data/emails_mock.csv")
                    emails = df_emails[df_emails['ASIN'] == product_data['ASIN']]
                    if not emails.empty:
                        for _, email in emails.iterrows():
                            with st.expander(f"{email['Date']} - {email['Subject']}"):
                                st.markdown(f"**From:** {email['From']}")
                                st.markdown(f"**To:** {email['To']}")
                                st.markdown(f"**Type:** {email['Type']}")
                                st.markdown(f"**Body:**\n{email['Body']}")
                    else:
                        st.info("No related emails found.")
                except Exception:
                    st.info("No email data available.")
                # 4. Costes y rentabilidad
                st.subheader("Costs & Profitability")
                st.markdown(f"**Cost per unit:** ${product_data.get('Cost','')}")
                st.markdown(f"**Price per unit:** ${product_data.get('Price','')}")
                st.markdown(f"**ROI:** {product_data.get('ROI','')}%")
                st.markdown(f"**Profit:** ${product_data.get('Profit','')}")
                # 5. Inventario
                st.subheader("Inventory")
                # --- Estado para mostrar formularios ---
                if 'show_stock_arrival_form' not in st.session_state:
                    st.session_state['show_stock_arrival_form'] = False
                if 'show_manual_sale_form' not in st.session_state:
                    st.session_state['show_manual_sale_form'] = False
                if 'manual_movements' not in st.session_state:
                    st.session_state['manual_movements'] = {}
                asin = product_data['ASIN']
                manual_movements_path = 'data/manual_inventory_movements.csv'
                # --- Cargar movimientos manuales persistentes ---
                if 'manual_movements_loaded' not in st.session_state:
                    if os.path.exists(manual_movements_path):
                        df_manual_persist = pd.read_csv(manual_movements_path)
                        for _, row in df_manual_persist.iterrows():
                            st.session_state['manual_movements'].setdefault(row['ASIN'], []).append(row.to_dict())
                    st.session_state['manual_movements_loaded'] = True
                # --- Guardar movimiento manual en disco ---
                def save_manual_movement(new_mov):
                    if os.path.exists(manual_movements_path):
                        df = pd.read_csv(manual_movements_path)
                        df = pd.concat([df, pd.DataFrame([new_mov])], ignore_index=True)
                    else:
                        df = pd.DataFrame([new_mov])
                    df.to_csv(manual_movements_path, index=False)
                # --- Botón y formulario para entrada de stock ---
                if st.button("Register Stock Arrival", key=f"register_stock_btn_{asin}"):
                    st.session_state['show_stock_arrival_form'] = not st.session_state['show_stock_arrival_form']
                    st.session_state['show_manual_sale_form'] = False
                if st.session_state['show_stock_arrival_form']:
                    with st.form(key=f"stock_arrival_form_{asin}"):
                        qty_in = st.number_input("Quantity received", min_value=1, value=10, step=1, key=f"qty_in_{asin}")
                        date_in = st.date_input("Date", value=datetime.date.today(), key=f"date_in_{asin}")
                        note_in = st.text_input("Note", value="Manual stock arrival", key=f"note_in_{asin}")
                        submitted_in = st.form_submit_button("Add Stock Arrival", key=f"submit_in_{asin}")
                        cancel_in = st.form_submit_button("Cancel", type="secondary", key=f"cancel_in_{asin}")
                        if submitted_in:
                            new_mov = {
                                'ASIN': asin,
                                'Date': str(date_in),
                                'Type': 'IN',
                                'Quantity': qty_in,
                                'Note': note_in
                            }
                            st.session_state['manual_movements'].setdefault(asin, []).append(new_mov)
                            save_manual_movement(new_mov)
                            st.session_state['show_stock_arrival_form'] = False
                            st.success(f"Stock arrival of {qty_in} units registered.")
                        elif cancel_in:
                            st.session_state['show_stock_arrival_form'] = False
                # --- Botón y formulario para venta manual ---
                if st.button("Register Manual Sale", key=f"register_sale_btn_{asin}"):
                    st.session_state['show_manual_sale_form'] = not st.session_state['show_manual_sale_form']
                    st.session_state['show_stock_arrival_form'] = False
                if st.session_state['show_manual_sale_form']:
                    with st.form(key=f"manual_sale_form_{asin}"):
                        qty_out = st.number_input("Quantity sold", min_value=1, value=1, step=1, key=f"qty_out_{asin}")
                        date_out = st.date_input("Date", value=datetime.date.today(), key=f"date_out_{asin}")
                        note_out = st.text_input("Note", value="Manual sale", key=f"note_out_{asin}")
                        submitted_out = st.form_submit_button("Add Manual Sale", key=f"submit_out_{asin}")
                        cancel_out = st.form_submit_button("Cancel", type="secondary", key=f"cancel_out_{asin}")
                        if submitted_out:
                            new_mov = {
                                'ASIN': asin,
                                'Date': str(date_out),
                                'Type': 'OUT',
                                'Quantity': qty_out,
                                'Note': note_out
                            }
                            st.session_state['manual_movements'].setdefault(asin, []).append(new_mov)
                            save_manual_movement(new_mov)
                            st.session_state['show_manual_sale_form'] = False
                            st.success(f"Manual sale of {qty_out} units registered.")
                        elif cancel_out:
                            st.session_state['show_manual_sale_form'] = False
                # --- Unir movimientos mock + manuales para mostrar ---
                try:
                    df_mov = pd.read_csv("data/inventory_movements_mock.csv")
                    movs = df_mov[df_mov['ASIN'] == asin].copy()
                except Exception:
                    movs = pd.DataFrame(columns=['ASIN','Date','Type','Quantity','Note'])
                manual_movs = st.session_state['manual_movements'].get(asin, [])
                if manual_movs:
                    df_manual = pd.DataFrame(manual_movs)
                    movs = pd.concat([movs, df_manual], ignore_index=True)
                if not movs.empty:
                    movs = movs.sort_values('Date')
                    st.markdown("**Inventory Movements:**")
                    st.dataframe(movs[['Date','Type','Quantity','Note']])
                else:
                    st.info("No inventory movements found.")
                # --- Recalcular stock mostrado ---
                stock_in = movs[movs['Type']=='IN']['Quantity'].sum() if not movs.empty else 0
                stock_out = movs[movs['Type']=='OUT']['Quantity'].sum() if not movs.empty else 0
                stock_actual = stock_in - stock_out
                st.markdown(f"**Stock in Amazon (calculated):** {stock_actual}")
                # --- ALERTA de stock bajo ---
                threshold = st.session_state.get('stock_threshold', 10)
                alert_email = st.session_state.get('alert_email', '')
                enable_alerts = st.session_state.get('enable_alerts', True)
                lang = st.session_state.get('lang', 'en')
                if enable_alerts and stock_actual < threshold:
                    st.error(f"{'¡Stock bajo!' if lang=='es' else 'Low stock!'} {product_data['Title']} (ASIN: {asin}) has only {stock_actual} units (threshold: {threshold})")
                    if alert_email:
                        context = {
                            'product': product_data['Title'],
                            'asin': asin,
                            'stock_actual': stock_actual,
                            'threshold': threshold,
                            'from_email': alert_email
                        }
                        if 'last_alert_sent' not in st.session_state:
                            st.session_state['last_alert_sent'] = {}
                        last_sent = st.session_state['last_alert_sent'].get(asin, 0)
                        import time
                        now = time.time()
                        # Solo enviar una alerta por producto cada 10 minutos
                        if now - last_sent > 600:
                            ok, err = send_alert_email('low_stock', lang, alert_email, context)
                            if ok:
                                st.info(f"Alert email sent to {alert_email}")
                                st.session_state['last_alert_sent'][asin] = now
                            else:
                                st.warning(f"Could not send alert email: {err}")
                # --- Botón para exportar historial ---
                if not movs.empty:
                    csv_buffer = io.StringIO()
                    movs.to_csv(csv_buffer, index=False)
                    st.download_button(
                        label="Export Inventory Movements (CSV)",
                        data=csv_buffer.getvalue(),
                        file_name=f"inventory_movements_{asin}.csv",
                        mime="text/csv",
                        key=f"export_movements_{asin}"
                    )
                # 6. Historial de acciones
                st.subheader("Action History")
                if 'movs' in locals() and not movs.empty:
                    for _, row in movs.iterrows():
                        st.markdown(f"- {row['Date']}: {row['Type']} {row['Quantity']} units ({row['Note']})")
                if 'emails' in locals() and not emails.empty:
                    for _, email in emails.iterrows():
                        st.markdown(f"- {email['Date']}: Email '{email['Subject']}' [{email['Type']}] to {email['To']}")
                # 7. Botones de acción
                st.subheader("Actions")
                st.button("Send Email to Supplier", key="send_email_btn")
                st.button("Register Stock Arrival", key="register_stock_btn")
                st.button("Register Manual Sale", key="register_sale_btn")
                # 8. Análisis de demanda
                st.subheader(t('demand_analysis'))
                estimated_demand = None
                if product_data.get('Demand', None) is not None:
                    estimated_demand = product_data.get('Demand', None)
                else:
                    try:
                        estimated_demand = int(product_data.get('Units_Sold', 0)) + int(product_data.get('Stock', 0))
                    except Exception:
                        estimated_demand = None
                st.markdown(f"**{t('estimated_demand')}:** {estimated_demand if estimated_demand is not None else 'N/A'}")
                real_demand = None
                if 'movs' in locals() and not movs.empty:
                    real_demand = movs[movs['Type'] == 'OUT']['Quantity'].sum()
                else:
                    try:
                        real_demand = int(product_data.get('Units_Sold', 0))
                    except Exception:
                        real_demand = None
                st.markdown(f"**{t('real_demand')}:** {real_demand if real_demand is not None else 'N/A'}")
                if estimated_demand is not None and real_demand is not None:
                    error = real_demand - int(estimated_demand)
                    abs_error = abs(error)
                    st.markdown(f"**{t('forecast_error')}:** {error} (Absolute: {abs_error})")
                    if int(estimated_demand) > 0:
                        correction_factor = real_demand / int(estimated_demand)
                        next_forecast = round(int(estimated_demand) * correction_factor)
                        st.markdown(f"**{t('correction_factor')}:** {correction_factor:.2f}")
                        st.markdown(f"**{t('suggested_next_forecast')}:** {next_forecast}")
                    else:
                        st.info(t('not_enough_data'))
                else:
                    st.info(t('not_enough_data'))
                method_options = [
                    ("correction", t("correction_factor_method")),
                    ("exp_smoothing", t("exp_smoothing")),
                    ("holt_winters", t("holt_winters_forecast")),
                    ("prophet", t("prophet_forecast"))
                ]
                method_dict = {
                    "correction": {
                        "desc": t("correction_desc"),
                        "rec": t("correction_rec")
                    },
                    "exp_smoothing": {
                        "desc": t("exp_smoothing_desc"),
                        "rec": t("exp_smoothing_rec")
                    },
                    "holt_winters": {
                        "desc": t("holt_winters_desc"),
                        "rec": t("holt_winters_rec")
                    },
                    "prophet": {
                        "desc": t("prophet_desc"),
                        "rec": t("prophet_rec")
                    }
                }
                col_sel, col_info = st.columns([8,1])
                with col_sel:
                    selected_method = st.selectbox(
                        t('select_method'),
                        options=method_options,
                        format_func=lambda x: x[1],
                        key="forecast_method_selector"
                    )[0]
                with col_info:
                    if st.button('ℹ️', key='show_desc_btn'):
                        st.session_state['show_desc'] = not st.session_state.get('show_desc', False)
                if st.session_state.get('show_desc', False):
                    st.info(method_dict[selected_method]['desc'])
                # Solo mostrar la recomendación como texto visible
                st.markdown(f"**{t('when_to_use')}** {method_dict[selected_method]['rec']}")

                # --- Forecast según método seleccionado ---
                # Calcular métricas de error para cada método si hay datos históricos suficientes
                sales_history_path = f"data/sales_history_{product_data['ASIN']}.csv"
                y_true, y_pred_correction, y_pred_exp, y_pred_hw, y_pred_prophet = [], [], [], [], []
                metrics_table = []
                anomalies = []  # <-- Inicialización añadida aquí
                if os.path.exists(sales_history_path):
                    df_sales = pd.read_csv(sales_history_path)
                    df_sales['Date'] = pd.to_datetime(df_sales['Date'])
                    df_sales = df_sales.sort_values('Date')
                    if len(df_sales) >= 6:
                        y_true = df_sales['Units_Sold'].values[-6:]
                        est = int(product_data.get('Demand', 0)) or (int(product_data.get('Units_Sold', 0)) + int(product_data.get('Stock', 0)))
                        y_pred_correction = [est] * 6
                        alpha = 0.5
                        F_t = est
                        y_pred_exp = []
                        for D_t in y_true:
                            F_t = round(alpha * D_t + (1 - alpha) * F_t)
                            y_pred_exp.append(F_t)
                        import numpy as np
                        try:
                            from statsmodels.tsa.holtwinters import ExponentialSmoothing
                            y = df_sales['Units_Sold'].values
                            max_period = max(2, len(y)//2)
                            period = min(12, max_period)
                            if len(y) >= 2*period:
                                model = ExponentialSmoothing(y, trend='add', seasonal='add', seasonal_periods=period)
                                fit = model.fit()
                                y_pred_hw = fit.fittedvalues.values[-6:]
                                if len(y_pred_hw) < 6:
                                    y_pred_hw = list(y_pred_hw) + [np.nan]*(6-len(y_pred_hw))
                            else:
                                y_pred_hw = [np.nan]*6
                                st.info(f"Holt-Winters needs at least {2*period} data points (current: {len(y)}).")
                        except Exception as e:
                            y_pred_hw = [np.nan]*6
                            st.info(f"Holt-Winters could not be fitted: {e}")
                        try:
                            forecast_val, forecast_df = forecast_prophet(df_sales[['Date','Units_Sold']])
                            y_pred_prophet = forecast_df['yhat'].values[-6:]
                        except Exception:
                            y_pred_prophet = []
                        # Detección de anomalías con Prophet
                        try:
                            forecast_val, forecast_df = forecast_prophet(df_sales[['Date','Units_Sold']])
                            last6 = forecast_df.iloc[-6:]
                            real_last6 = df_sales['Units_Sold'].values[-6:]
                            for i, row in last6.iterrows():
                                real = real_last6[i - last6.index[0]]
                                if real < row['yhat_lower'] or real > row['yhat_upper']:
                                    anomalies.append({
                                        'date': row['ds'].strftime('%Y-%m-%d') if hasattr(row['ds'], 'strftime') else str(row['ds']),
                                        'real': real,
                                        'expected_range': f"{row['yhat_lower']:.1f} - {row['yhat_upper']:.1f}",
                                        'yhat': row['yhat']
                                    })
                        except Exception:
                            pass
                # Mostrar tabla comparativa de métricas
                if metrics_table:
                    st.markdown('**Forecasting error comparison (last 6 periods):**')
                    st.dataframe(metrics_table, use_container_width=True)
                    # Gráfico comparativo
                    try:
                        # Fechas para los últimos 6 periodos
                        if len(df_sales) >= 6:
                            dates = df_sales['Date'].dt.strftime('%Y-%m-%d').values[-6:]
                            fig = go.Figure()
                            fig.add_trace(go.Scatter(x=dates, y=y_true, mode='lines+markers', name='Actual'))
                            if len(y_pred_correction) == 6:
                                fig.add_trace(go.Scatter(x=dates, y=y_pred_correction, mode='lines+markers', name='Correction Factor'))
                            if len(y_pred_exp) == 6:
                                fig.add_trace(go.Scatter(x=dates, y=y_pred_exp, mode='lines+markers', name='Exp. Smoothing'))
                            if len(y_pred_hw) == 6:
                                fig.add_trace(go.Scatter(x=dates, y=y_pred_hw, mode='lines+markers', name='Holt-Winters'))
                            if len(y_pred_prophet) == 6:
                                fig.add_trace(go.Scatter(x=dates, y=y_pred_prophet, mode='lines+markers', name='Prophet'))
                            # Añadir anomalías si existen
                            if anomalies:
                                anomaly_dates = [a['date'] for a in anomalies]
                                anomaly_vals = [a['real'] for a in anomalies]
                                fig.add_trace(go.Scatter(
                                    x=anomaly_dates, y=anomaly_vals,
                                    mode='markers',
                                    marker=dict(color='red', size=14, symbol='x'),
                                    name='Anomaly',
                                    showlegend=True
                                ))
                            fig.update_layout(title='Forecasting comparison (last 6 periods)', xaxis_title='Date', yaxis_title='Units Sold')
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.info(f"Could not display comparison chart: {e}")
                else:
                    st.info('Not enough data to compare forecasting methods.')
                if anomalies:
                    for anomaly in anomalies:
                        st.warning(f"⚠️ Anomaly detected in sales on {anomaly['date']}! Real: {anomaly['real']}, Expected: {anomaly['expected_range']}. Consider reviewing inventory or contacting your supplier.")
        else:
            st.info("Product tracking is only available in developer mode. Please enable developer mode to use mock data, or import real product data.")
    with tabs[3]:
        # --- SOLO aquí va la UI de gestión de emails ---
        st.header(t('email_agent_instructions'))
        if st.session_state.get("email_address") and st.session_state.get("email_password"):
            try:
                provider = st.session_state.get("email_provider", "gmail")
                if provider == "gmail":
                    imap_server = "imap.gmail.com"
                elif provider == "outlook":
                    imap_server = "imap-mail.outlook.com"
                else:
                    imap_server = st.text_input(t('imap_server'), value="imap.gmail.com")
                imap = imaplib.IMAP4_SSL(imap_server)
                imap.login(st.session_state.get("email_address", ""), st.session_state.get("email_password", ""))
                imap.select("INBOX")
                status, messages = imap.search(None, "ALL")
                if status == "OK":
                    mail_ids = messages[0].split()[-50:]  # Leer los últimos 50
                    emails = []
                    for num in reversed(mail_ids):
                        status, msg_data = imap.fetch(num, "(RFC822)")
                        if status != "OK":
                            continue
                        msg = email.message_from_bytes(msg_data[0][1])
                        # --- Parseo avanzado (con adjuntos) ---
                        parts = decode_header(msg.get("Subject", ""))
                        subject = "".join([(p[0].decode(p[1] or 'utf-8') if isinstance(p[0], bytes) else str(p[0])) for p in parts])
                        sender = parseaddr(msg.get("From", ""))[1]
                        date_ = msg.get("Date", "")
                        try:
                            date_obj = email.utils.parsedate_to_datetime(date_)
                        except Exception:
                            date_obj = None
                        body = ""
                        attachments = []
                        if msg.is_multipart():
                            for part in msg.walk():
                                disp = part.get("Content-Disposition", "")
                                if part.get_content_type() == "text/plain" and "attachment" not in disp:
                                    body_bytes = part.get_payload(decode=True)
                                    body += body_bytes.decode(errors="ignore") if body_bytes else ""
                                elif "attachment" in disp:
                                    filename = part.get_filename()
                                    if filename:
                                        payload = part.get_payload(decode=True)
                                        attachments.append((filename, payload))
                        else:
                            payload = msg.get_payload(decode=True)
                            body = payload.decode(errors="ignore") if payload else ""
                        emails.append({
                            "subject": subject,
                            "sender": sender,
                            "date": date_obj or date_,
                            "body": body,
                            "attachments": attachments
                        })
                    # --- Filtros ---
                    st.subheader(t('last_emails'))
                    filter_sender = st.text_input("Filtrar por remitente")
                    filter_subject = st.text_input("Filtrar por asunto")
                    filter_date = st.date_input("Filtrar por fecha", value=None, key="filter_date", disabled=False)
                    filtered_emails = emails
                    if filter_sender:
                        filtered_emails = [e for e in filtered_emails if filter_sender.lower() in e["sender"].lower()]
                    if filter_subject:
                        filtered_emails = [e for e in filtered_emails if filter_subject.lower() in e["subject"].lower()]
                    if filter_date:
                        filtered_emails = [e for e in filtered_emails if isinstance(e["date"], datetime.datetime) and e["date"].date() == filter_date]
                    # --- Tabla de emails ---
                    table_data = [{
                        t('from'): e['sender'],
                        t('subject'): e['subject'],
                        t('date'): e['date'].strftime('%Y-%m-%d %H:%M') if isinstance(e['date'], datetime.datetime) else str(e['date']),
                        'body': e['body'],
                        'attachments': e['attachments']
                    } for e in filtered_emails]
                    if table_data:
                        df = pd.DataFrame(table_data)
                        st.dataframe(df[[t('from'), t('subject'), t('date')]], use_container_width=True)
                        for idx, row in df.iterrows():
                            with st.expander(f"{row[t('subject')]} | {row[t('from')]} | {row[t('date')]}"):
                                st.markdown(f"**{t('from')}:** {row[t('from')]}  ")
                                st.markdown(f"**{t('subject')}:** {row[t('subject')]}  ")
                                st.markdown(f"**{t('date')}:** {row[t('date')]}  ")
                                st.markdown(f"**Cuerpo:**\n\n{row['body']}")
                                if row['attachments']:
                                    st.markdown("**Adjuntos:**")
                                    for fname, payload in row['attachments']:
                                        if payload:
                                            st.download_button(f"Descargar {fname}", data=payload, file_name=fname)
                    else:
                        st.info("No hay emails que coincidan con los filtros.")
                imap.logout()
            except Exception as e:
                st.error(f"{t('test_email_error', error=e)}")
            st.markdown("---")
            # --- Envío manual de emails ---
            st.subheader("Enviar email manualmente")
            with st.form("manual_email_form"):
                to_addr = st.text_input("Para (destinatario)")
                subject = st.text_input("Asunto")
                body = st.text_area("Cuerpo del mensaje")
                file = st.file_uploader("Adjuntar archivo (opcional)", type=None)
                submitted = st.form_submit_button("Enviar email")
                if submitted:
                    try:
                        msg = EmailMessage()
                        msg["Subject"] = subject
                        msg["From"] = st.session_state.get("email_address", "")
                        msg["To"] = to_addr
                        msg.set_content(body)
                        if file is not None:
                            file_bytes = file.read()
                            msg.add_attachment(file_bytes, maintype="application", subtype="octet-stream", filename=file.name)
                        provider = st.session_state.get("email_provider", "gmail")
                        smtp_server = "smtp.gmail.com" if provider == "gmail" else ("smtp-mail.outlook.com" if provider == "outlook" else st.text_input(t('smtp_server'), value="smtp.gmail.com"))
                        smtp_port = 587
                        try:
                            with smtplib.SMTP(smtp_server, smtp_port, timeout=15) as server:
                                server.starttls()
                                server.login(st.session_state.get("email_address", ""), st.session_state.get("email_password", ""))
                                server.send_message(msg)
                            st.success("Email enviado correctamente.")
                        except Exception as e1:
                            try:
                                with smtplib.SMTP_SSL(smtp_server, 465, timeout=15) as server:
                                    server.login(st.session_state.get("email_address", ""), st.session_state.get("email_password", ""))
                                    server.send_message(msg)
                                st.success("Email enviado correctamente (SSL/465).")
                            except Exception as e2:
                                st.error(f"Error enviando email: 587: {e1} | 465: {e2}")
                    except Exception as e:
                        st.error(f"Error enviando email: {e}")
        else:
            st.warning(t('email_address') + "/" + t('email_password') + " " + t('not_configured'))
    with tabs[4]:
        # --- NUEVO: Pestaña KDP ---
        st.header("KDP (Kindle Direct Publishing)")
        st.info("Aquí podrás gestionar el pipeline de KDP. Próximamente podrás descubrir nichos, analizar competencia, generar portadas y gestionar publicaciones de libros en Amazon KDP.")
        # Esqueleto de pasos típicos del pipeline KDP:
        st.subheader("1. Descubrimiento de Nichos")
        st.write("Funcionalidad para buscar nichos rentables en KDP. [Por implementar]")
        st.subheader("2. Análisis de Competencia")
        st.write("Analiza la competencia en los nichos seleccionados. [Por implementar]")
        st.subheader("3. Generación de Portadas y Descripciones")
        st.write("Herramientas para crear portadas y descripciones atractivas. [Por implementar]")
        st.subheader("4. Publicación y Seguimiento de Ventas")
        st.write("Gestiona la publicación y monitoriza ventas de tus libros KDP. [Por implementar]")
        # Aquí puedes ir añadiendo formularios, tablas, botones, etc. según avances.
        # Ejemplo de botón futuro:
        # if st.button("Descubrir Nichos KDP"):
        #     st.success("Funcionalidad en desarrollo.")

        # 1. Descubrimiento de Nichos
        st.subheader("1. Descubrimiento de Nichos")
        if st.button("Descubrir nichos rentables"):
            df_nichos = kdp_module.discover_niches()
            st.session_state['df_nichos'] = df_nichos  # Guardar en session_state

        # Mostrar la tabla si existe en session_state
        if 'df_nichos' in st.session_state:
            st.dataframe(st.session_state['df_nichos'])

        # 2. Análisis de Competencia
        nicho = st.text_input("Introduce un nicho para analizar la competencia")
        if st.button("Analizar competencia") and nicho:
            comp = kdp_module.analyze_competition(nicho)
            st.session_state['comp_result'] = comp  # Guardar en session_state

        if 'comp_result' in st.session_state:
            comp = st.session_state['comp_result']
            st.markdown(f"### Análisis de competencia para: **{comp['niche']}**")
            col1, col2, col3 = st.columns(3)
            col1.metric("Top Sellers", comp["top_sellers"])
            col2.metric("Precio medio", f"${comp['avg_price']:.2f}")
            col3.metric("Reviews medias", comp["avg_reviews"])
            st.info(f"**Barreras de entrada:** {comp['barrier_to_entry']}")

        # 3. Generación de Título, Portada y Contenido con IA
        st.subheader("3. Generación de Título, Portada y Contenido con IA")
        book_format = st.text_input("Formato del libro (ej: diario, planner, cuaderno)")
        if st.button("Generar libro con IA") and nicho and book_format:
            with st.spinner("Generando título, descripción y contenido con IA..."):
                ai_result = kdp_module.generate_kdp_book_ai(nicho, book_format)
            st.markdown(f"**Título sugerido:** {ai_result['titulo']}")
            st.markdown(f"**Descripción:** {ai_result['descripcion']}")
            st.markdown(f"**Ejemplo de contenido:**\n\n{ai_result['contenido']}")
            # Portada con IA
            if st.button("Generar portada con IA"):
                with st.spinner("Generando portada con IA..."):
                    cover_url = kdp_module.generate_kdp_cover_ai(ai_result['titulo'], nicho)
                st.image(cover_url, caption="Portada generada por IA")

        # 4. Publicación y Seguimiento
        st.subheader("4. Publicación y Seguimiento de Ventas")
        book_asin = st.text_input("ASIN del libro para seguimiento")
        if st.button("Simular publicación"):
            book_data = {"title": title, "niche": nicho, "author": author}
            pub = kdp_module.publish_book(book_data)
            st.success(pub["message"])
        if st.button("Ver ventas simuladas") and book_asin:
            df_sales = kdp_module.track_sales(book_asin)
            st.dataframe(df_sales)

        # Buscar tendencias en Pinterest
        st.subheader("Buscar tendencias en Pinterest")
        pinterest_query = st.text_input("Palabra clave para buscar en Pinterest", value="journal ideas", key="pinterest_query")
        if st.button("Buscar en Pinterest"):
            with st.spinner("Buscando en Pinterest..."):
                df_pins = kdp_module.search_pinterest_trends(pinterest_query)
                st.session_state['df_pins'] = df_pins  # Guardar resultados en session_state
        # Mostrar la tabla si existe en session_state
        if 'df_pins' in st.session_state:
            st.dataframe(st.session_state['df_pins'])


def run_step_ui(label: str, script: str, budget: float, dev_mode: bool) -> None:
    """Execute a module and display the results in the UI."""
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
            subprocess.run(['python', 'mock_data_generator.py'], check=True)
    # --- Aviso si los archivos de resultados existen antes de correr módulos ---
    output_path = None
    for mod_label, mod_script in MODULES:
        if mod_label == label:
            idx = MODULES.index((mod_label, mod_script))
            if idx < len(fba_agent.OUTPUTS):
                output_path = list(fba_agent.OUTPUTS.values())[idx]
            break
    if output_path and os.path.exists(output_path):
        st.info(t('results_file_exists', output_path=output_path))
        if st.button(t('reset_pipeline_confirm')):
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
    # Ejecutar el script con el flag --mock si corresponde, excepto para supplier_selection.py
    cmd = ['python', script]
    if dev_mode and script not in ('supplier_selection.py', 'supplier_contact_generator.py'):
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
    with st.expander(t('step_log'), expanded=returncode != 0 and dev_mode):
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
    st.subheader(t('supplier_selection_title'))
    # Métricas resumen
    total_cost = df["total_cost"].sum() if "total_cost" in df else 0
    total_profit = df["estimated_profit"].sum() if "estimated_profit" in df else 0
    st.metric(t('total_cost'), f"${total_cost:,.2f}")
    st.metric(t('total_profit'), f"${total_profit:,.2f}")
    st.dataframe(df)


def check_requirements_installed() -> bool:
    """Devuelve True si todos los paquetes de requirements.txt están instalados, False si falta alguno."""
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


def load_config():
    if not os.path.exists(CONFIG_PATH):
        if os.path.exists(CONFIG_EXAMPLE_PATH):
            with open(CONFIG_EXAMPLE_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
        else:
            config = {k: "" for k, _ in API_KEYS}
            config["email_provider"] = "gmail"
            with open(CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(config, f, indent=2)
    else:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
    return config


def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


# --- Plantillas de alertas (ES/EN) ---
ALERT_TEMPLATES = {
    'low_stock': {
        'es': {
            'subject': '[ALERTA] Stock bajo para {product}',
            'body': (
                'Hola,\n\nEl stock del producto {product} (ASIN: {asin}) ha bajado a {stock_actual} unidades, por debajo del umbral de {threshold}.\nTe recomendamos reponer inventario lo antes posible.\n\nSaludos,\nAmazon FBA AI Agent'
            )
        },
        'en': {
            'subject': '[ALERT] Low stock for {product}',
            'body': (
                'Hello,\n\nThe stock for product {product} (ASIN: {asin}) has dropped to {stock_actual} units, below the threshold of {threshold}.\nWe recommend restocking as soon as possible.\n\nBest regards,\nAmazon FBA AI Agent'
            )
        }
    },
    'sales_anomaly': {
        'es': {
            'subject': '[ALERTA] Anomalía detectada en ventas de {product}',
            'body': (
                'Hola,\n\nSe ha detectado una anomalía en las ventas del producto {product} (ASIN: {asin}):\n{anomaly_desc}\n\nPor favor, revisa la situación para tomar las acciones necesarias.\n\nSaludos,\nAmazon FBA AI Agent'
            )
        },
        'en': {
            'subject': '[ALERT] Sales anomaly detected for {product}',
            'body': (
                'Hello,\n\nA sales anomaly has been detected for product {product} (ASIN: {asin}):\n{anomaly_desc}\n\nPlease review the situation and take necessary action.\n\nBest regards,\nAmazon FBA AI Agent'
            )
        }
    }
}

def send_alert_email(alert_type, lang, to_email, context):
    import smtplib
    from email.message import EmailMessage
    tpl = ALERT_TEMPLATES[alert_type][lang]
    subject = tpl['subject'].format(**context)
    body = tpl['body'].format(**context)
    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = context.get('from_email', 'fba-agent@example.com')
    msg['To'] = to_email
    msg.set_content(body)
    # Configuración SMTP desde config
    config = load_config()
    smtp_server = config.get('smtp_server', 'smtp.gmail.com')
    smtp_port = int(config.get('smtp_port', 587))
    smtp_user = config.get('email_address', '')
    smtp_pass = config.get('email_password', '')
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_pass)
            server.send_message(msg)
        return True, None
    except Exception as e:
        return False, str(e)

# --- ToDo file helpers ---
TODO_FILE = 'todos.txt'

def add_todo(task: str):
    with open(TODO_FILE, 'a', encoding='utf-8') as f:
        f.write(task.strip() + '\n')

def complete_todo(task: str):
    if not os.path.exists(TODO_FILE):
        return
    with open(TODO_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    with open(TODO_FILE, 'w', encoding='utf-8') as f:
        for line in lines:
            if line.strip() == task.strip() or line.strip() == task.strip() + 'OK':
                f.write(task.strip() + 'OK\n')
            else:
                f.write(line)

def load_todos():
    if not os.path.exists(TODO_FILE):
        return []
    with open(TODO_FILE, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def forecast_prophet(df_sales):
    df = df_sales.rename(columns={'Date': 'ds', 'Units_Sold': 'y'})
    model = Prophet()
    model.fit(df)
    future = model.make_future_dataframe(periods=1, freq='M')
    forecast = model.predict(future)
    return forecast.iloc[-1]['yhat'], forecast

if __name__ == "__main__":
    args = parse_cli()
    if args.headless:
        run_headless(auto=args.auto)
    else:
        pipeline_ui()
