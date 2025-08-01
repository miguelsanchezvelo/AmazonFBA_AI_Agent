import argparse
import time
import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import logging
import sys
import os

# Configure logging to file and console
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("discovery.log", mode="a"),
        logging.StreamHandler(sys.stdout)
    ],
)


def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("user-agent=Mozilla/5.0")
    return webdriver.Chrome(options=chrome_options)


def get_suggestions(driver, base_keyword):
    driver.get("https://www.amazon.es/")
    time.sleep(2)
    search_box = driver.find_element(By.ID, "twotabsearchtextbox")
    search_box.send_keys(base_keyword)
    time.sleep(2)
    suggestions = driver.find_elements(By.CSS_SELECTOR, ".s-suggestion")
    return [s.text.strip() for s in suggestions if base_keyword.lower() in s.text.lower()]


def get_competition_and_bsr(driver, keyword):
    driver.get("https://www.amazon.es/")
    time.sleep(2)
    search_box = driver.find_element(By.ID, "twotabsearchtextbox")
    search_box.clear()
    search_box.send_keys(keyword)
    search_box.send_keys(Keys.RETURN)
    time.sleep(2)

    try:
        results_text = driver.find_element(By.XPATH, "//span[contains(text(),'resultados')]").text
        competition = int(''.join(filter(str.isdigit, results_text.split()[0])))
    except Exception:
        competition = 0

    bsr_list = []
    books = driver.find_elements(By.CSS_SELECTOR, "div.s-main-slot div[data-asin]")[:10]
    for book in books:
        try:
            bsr_text = book.find_element(By.XPATH, ".//span[contains(text(),'n.º')]").text
            bsr = int(''.join(filter(str.isdigit, bsr_text)))
            bsr_list.append(bsr)
        except Exception:
            continue

    avg_bsr = round(sum(bsr_list) / len(bsr_list), 2) if bsr_list else 999999
    return competition, avg_bsr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--keyword", required=True, help="Seed keyword (e.g. diario, planner)")
    args = parser.parse_args()

    try:
        logging.info(f"🔍 Starting discovery for keyword: {args.keyword}")
        driver = get_driver()

        suggestions = get_suggestions(driver, args.keyword)
        if not suggestions:
            raise ValueError("No suggestions found.")

        results = []
        for niche in suggestions:
            logging.info(f"Analyzing niche: {niche}")
            competition, avg_bsr = get_competition_and_bsr(driver, niche)
            saturation = round(competition / avg_bsr, 4) if avg_bsr else 9999
            results.append({
                "niche": niche,
                "search_volume": "N/A",
                "competition": competition,
                "avg_bsr": avg_bsr,
                "saturation": saturation
            })
            time.sleep(2)

        df = pd.DataFrame(results)
        safe_keyword = args.keyword.lower().replace(" ", "_")
        output_file = f"niches_{safe_keyword}.csv"
        df.to_csv(output_file, index=False)
        logging.info(f"✅ Discovery completed successfully. Saved to {output_file}")
        driver.quit()
        sys.exit(0)

    except Exception as e:
        logging.exception("❌ An error occurred during discovery.")
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
