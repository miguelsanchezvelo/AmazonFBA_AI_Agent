# 1. Visión general del proyecto

Este repositorio implementa un agente de inteligencia artificial que automatiza por completo el modelo de negocio de Amazon FBA. El sistema busca productos potencialmente rentables, analiza el mercado y las reseñas, estima márgenes, predice la demanda, selecciona proveedores y gestiona la comunicación con ellos. Finalmente planifica el inventario y ayuda a colocar los pedidos. El objetivo final es empaquetar esta solución como un producto SaaS.

# 2. Estructura modular y responsabilidades

- `product_discovery.py`: busca productos rentables en Amazon usando SerpAPI y calcula métricas básicas.
- `market_analysis.py`: analiza competencia y demanda mediante SerpAPI y Keepa (o datos simulados).
- `review_analysis.py`: resume opiniones de clientes con OpenAI u obtiene reseñas por SerpAPI.
- `profitability_estimation.py`: estima ROI, margen y beneficio combinando precios con datos de proveedor.
- `demand_forecast.py`: predice demanda mensual aproximada a partir de Best Seller Rank.
- `supplier_selection.py`: decide qué productos pedir y cantidades óptimas según ROI y demanda.
- `supplier_contact_generator.py`: genera mensajes automáticos para proveedores con plantillas y OpenAI.
- `pricing_simulator.py`: simula cambios de precio y su efecto en ROI.
- `inventory_management.py`: propone cantidades de stock e inversiones necesarias.
- `order_placement_agent.py`: facilita al usuario enviar pedidos a proveedores por email.
- `fba_agent.py`: orquesta todo el pipeline ejecutando cada módulo y gestionando errores.
- `validate_all.py`: valida coherencia de archivos y scripts, reportando problemas.
- `mock_data_generator.py`: genera datos ficticios de todos los pasos para pruebas offline.
- `test_all.py`: verifica que cada script compila, muestra `--help` y acepta modo `--auto`.
- `ui.py`: interfaz Streamlit que permite ejecutar cada paso y visualizar resultados.

# 3. Flujo general de ejecución

Los módulos se ejecutan de forma secuencial y se comunican mediante archivos `.csv` guardados en la carpeta `data/`. El orquestador `fba_agent.py` (o la interfaz `ui.py`) llama a cada script, detecta si existen resultados previos y opcionalmente los reutiliza. En modo automático (`fba_agent.py --auto`) la pipeline se ejecuta sin intervención. Si faltan servicios externos se recurre a los archivos mock generados previamente.

# 4. Variables importantes y archivos generados

Los archivos principales que se generan son:

- `data/product_results.csv`
- `data/market_analysis_results.csv`
- `data/profitability_estimation_results.csv`
- `data/demand_forecast_results.csv`
- `data/supplier_selection_results.csv`
- `data/pricing_suggestions.csv`
- `data/inventory_management_results.csv`
- `data/review_analysis_results.csv`

Además se crean registros en `log.txt`, ficheros de control dentro de `logs/` y mensajes para proveedores en `supplier_messages/`. Las claves API y credenciales se guardan en `.env` o `config.json`.

# 5. Requisitos y dependencias externas

El proyecto usa `pandas`, `serpapi`, `keepa`, `openai`, `streamlit`, `colorama` y otras bibliotecas estándar. Los servicios externos que requieren clave son SerpAPI, Keepa y OpenAI. Si alguna clave no está disponible, los módulos afectados trabajan con datos simulados cuando es posible.

# 6. Estrategia de mock data y validación

Cada módulo puede funcionar en modo ficticio si no hay API keys o si faltan archivos de entrada. `mock_data_generator.py` crea todos los `.csv` mínimos y ejemplos de mensajes para permitir probar el pipeline completo sin conexión externa. El script `validate_all.py` comprueba la integridad de los datos y la corrección de los scripts, indicando cómo regenerar los archivos en caso de fallo.

# 7. Convenciones de diseño

- Todos los scripts se ejecutan desde la línea de comandos con `argparse` y muestran `--help`.
- Son compatibles con `test_all.py`, que comprueba su modo `--auto`.
- Se procura manejar los errores de forma robusta mostrando mensajes claros.
- Los datos entre módulos se intercambian siempre por CSV en la carpeta `data/`.
- Los logs y la consola usan un formato unificado con `colorama` y se registra la hora de cada evento.

# 8. Ideas futuras

- Integración completa con email para lectura y escritura automática.
- Agente de negociación autónomo con seguimiento de hilos.
- Puntuación compuesta de productos según ROI, demanda y reseñas.
- Selección automática de proveedor y simulador interactivo de escenarios.
- Integración con GitHub Actions para auto-reparación utilizando Codex.
- Agente de aprendizaje continuo que corrija errores y mejore el código tras cada validación.
