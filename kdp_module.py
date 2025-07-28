import pandas as pd
import requests
from bs4 import BeautifulSoup
import openai
import os

def discover_niches(keywords=None):
    """
    Descubre nichos rentables para KDP.
    :param keywords: Lista de palabras clave opcional para enfocar la búsqueda.
    :return: DataFrame con nichos sugeridos.
    """
    # TODO: Implementar lógica real (web scraping, API, heurística, etc.)
    data = [
        {"Nicho": "Diarios de gratitud", "Demanda": "Alta", "Competencia": "Media"},
        {"Nicho": "Cuadernos de caligrafía", "Demanda": "Media", "Competencia": "Baja"},
    ]
    return pd.DataFrame(data)

def analyze_competition(niche):
    """
    Analiza la competencia en un nicho KDP.
    :param niche: Nombre del nicho a analizar.
    :return: Dict con métricas de competencia.
    """
    # TODO: Implementar análisis real (búsqueda Amazon, scraping, etc.)
    return {
        "niche": niche,
        "top_sellers": 12,
        "avg_price": 7.99,
        "avg_reviews": 120,
        "barrier_to_entry": "Media"
    }

def generate_cover_and_description(niche, title, author):
    """
    Genera una portada y una descripción atractiva para un libro KDP.
    :param niche: Nicho del libro.
    :param title: Título del libro.
    :param author: Autor.
    :return: Dict con portada (mock) y descripción.
    """
    # TODO: Integrar IA para generación de portadas y copywriting
    return {
        "cover_url": "https://placehold.co/200x300?text=Portada+Mock",
        "description": f"Descubre el nuevo libro '{title}' de {author}, ideal para el nicho de {niche}. ¡Perfecto para tu público objetivo!"
    }

def publish_book(book_data):
    """
    Simula la publicación de un libro en KDP.
    :param book_data: Dict con los datos del libro.
    :return: Dict con resultado de la publicación.
    """
    # TODO: Integrar con la API de KDP o automatizar el proceso
    return {
        "status": "success",
        "message": f"Libro '{book_data.get('title')}' publicado correctamente (simulado)."
    }

def track_sales(book_asin):
    """
    Simula el seguimiento de ventas de un libro KDP.
    :param book_asin: ASIN del libro.
    :return: DataFrame con ventas simuladas.
    """
    # TODO: Integrar con reportes reales de KDP
    data = [
        {"Fecha": "2024-06-01", "Unidades Vendidas": 3},
        {"Fecha": "2024-06-02", "Unidades Vendidas": 5},
        {"Fecha": "2024-06-03", "Unidades Vendidas": 2},
    ]
    return pd.DataFrame(data)

def search_pinterest_trends(query, max_results=20):
    """
    Busca tendencias en Pinterest para una palabra clave.
    :param query: Palabra clave a buscar.
    :param max_results: Máximo número de resultados a devolver.
    :return: DataFrame con títulos y enlaces de los pines.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    url = f"https://www.pinterest.com/search/pins/?q={requests.utils.quote(query)}"
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return pd.DataFrame([{"error": f"HTTP {response.status_code}"}])

    soup = BeautifulSoup(response.text, "html.parser")
    results = []
    # Buscar todos los <a> que apunten a /pin/...
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/pin/"):
            text = a.get_text(strip=True)
            # Si no hay texto, intenta buscar alt de una imagen dentro
            if not text:
                img = a.find("img", alt=True)
                text = img["alt"] if img else ""
            link = "https://www.pinterest.com" + href
            if text or link:
                results.append({"title": text, "link": link})
        if len(results) >= max_results:
            break
    return pd.DataFrame(results)

def generate_kdp_book_ai(niche, book_format, openai_key=None):
    """
    Usa IA para generar título, descripción y contenido de un libro KDP.
    :param niche: Temática del libro.
    :param book_format: Formato (diario, planner, etc.).
    :param openai_key: API Key de OpenAI (opcional, si no está en variable de entorno).
    :return: dict con título, descripción, contenido.
    """
    openai.api_key = openai_key or os.getenv("OPENAI_API_KEY")
    prompt = (
        f"Quiero crear un libro para Amazon KDP.\n"
        f"Temática: {niche}\n"
        f"Formato: {book_format}\n"
        f"1. Sugiere un título atractivo para el libro.\n"
        f"2. Escribe una descripción de venta persuasiva (máx 400 caracteres).\n"
        f"3. Genera un ejemplo de contenido interior adecuado para este formato y temática (puede ser una estructura de página, prompts, frases, etc.).\n"
        f"Devuelve la respuesta en formato JSON con las claves: titulo, descripcion, contenido."
    )
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
        max_tokens=700
    )
    import json
    # Intentar extraer el JSON de la respuesta
    import re
    text = response.choices[0].message.content
    try:
        # Buscar bloque JSON en la respuesta
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
        else:
            # Si no hay JSON, intentar parsear como dict
            data = eval(text)
    except Exception:
        data = {"titulo": "Error", "descripcion": text, "contenido": ""}
    return data

def generate_kdp_cover_ai(title, niche, openai_key=None):
    """
    Usa IA (DALL·E) para generar una portada para el libro.
    :param title: Título del libro.
    :param niche: Temática.
    :param openai_key: API Key de OpenAI (opcional).
    :return: URL de la imagen generada.
    """
    openai.api_key = openai_key or os.getenv("OPENAI_API_KEY")
    prompt = f"Book cover for a KDP book titled '{title}' about {niche}, professional, eye-catching, suitable for Amazon."
    response = openai.Image.create(
        prompt=prompt,
        n=1,
        size="512x768"
    )
    return response['data'][0]['url'] 