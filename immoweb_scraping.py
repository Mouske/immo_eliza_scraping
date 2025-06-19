from bs4 import BeautifulSoup
from patchright.sync_api import sync_playwright
from property_parser import PropertyParser
import pandas as pd
import os
from tqdm import tqdm
from concurrent.futures import ThreadPoolExecutor, as_completed

class ImmoElizaScraper:
    def __init__(self):
        self.base_url = "https://www.immoweb.be/fr/recherche/maison-et-appartement/a-vendre?"
        self.parser = PropertyParser()

    def __str__(self) -> str:
        return "ImmoElizaScraper"

    def save_to_csv(self, data: list[dict], filename: str = "immoweb_data.csv"):
        df = pd.DataFrame(data)
        file_exists = os.path.exists(filename)
        df.to_csv(filename, mode="a", index=False, header=not file_exists, na_rep="None")

    def collect_basic_infos(self, page, nb_page: int) -> list[dict]:
        all_basic_info = []
        page.goto(self.base_url + f"countries=BE&page={nb_page}&orderBy=newest")
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        search_results = soup.find("div", id="searchResults").find("ul", id="main-content").find("div").find_all('li')
        properties = [result for result in search_results if result.find("a", class_="card__title-link")]
        for prop in properties:  # limite à 3 par page pour test
            basic_info = self.parser.extract_card_basic_info(prop)
            all_basic_info.append(basic_info)
        return all_basic_info


    def enrich_property(self, info: dict) -> dict:
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                detailed = self.parser.extract_detailed_property_info(page, info["url"])
                browser.close()
                return info | detailed
        except Exception as e:
            print(f"Error processing {info['url']}: {e}")
            return info  # Retourne au moins les infos de base

    def load_data(self, nb_pages: int = 10):
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()

            for nb_page in tqdm(range(1, nb_pages + 1), desc="Scraping pages"):
                basic_infos = self.collect_basic_infos(page, nb_page)

                with ThreadPoolExecutor(max_workers=5) as executor:
                    futures = [executor.submit(self.enrich_property, info) for info in basic_infos]

                    for future in as_completed(futures):
                        enriched = future.result()
                        self.save_to_csv([enriched])  

            browser.close()