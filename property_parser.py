import re
from bs4 import BeautifulSoup

class PropertyParser:

    def extract_card_basic_info(self, li) -> dict:
        house_subtypes = {"Maison", "Bungalow", "Chalet", "Ferme", "Château", "Maison de campagne", "Bien exceptionnel",
                         "Immeuble à appartements", "Immeuble mixte", "Maison bel-étage", "Maison de maître",
                         "Villa", "Manoir", "Pavillon", "Autres biens"}

        basic_info = {
            "url": None, "price": None, "rooms": None, "area": None, "locality": None,
            "property_type": None, "sub_property_type": None
        }

        title_tag = li.find("a", class_="card__title-link")
        if title_tag:
            title_text = title_tag.get_text(strip=True)
            basic_info["url"] = title_tag.get("href")
            if title_text in house_subtypes:
                basic_info["property_type"] = "House"
                basic_info["sub_property_type"] = title_text
            else:
                basic_info["property_type"] = "Apartment"
                basic_info["sub_property_type"] = title_text

        price_tag = li.find("p", class_="card--result__price")
        if price_tag:
            price_text = price_tag.get_text(strip=True)
            match = re.search(r"\d[\d\s\u202f\u00a0]*", price_text)
            if match:
                price = match.group().replace("\u202f", "").replace("\xa0", "").replace(" ", "")
                basic_info["price"] = price

        info_block = li.find("div", class_="card__informations")
        if info_block:
            property_info = info_block.find("p", class_="card__information--property")
            if property_info:
                text = property_info.get_text(" ", strip=True)
                if "ch." in text:
                    basic_info["rooms"] = text.split("ch.")[0].strip()
                if "m²" in text:
                    basic_info["area"] = text.split("\u00b7")[-1].split("m²")[0].strip()

            locality_info = info_block.find("p", class_="card__information card--results__information--locality")
            if locality_info:
                basic_info["locality"] = locality_info.get_text(strip=True)

        return basic_info

    def get_general_infos(self, section: BeautifulSoup) -> dict:
        data = {"facades": None, "building_state": None}
        for row in section.find_all("tr", class_="classified-table__row"):
            header = row.find("th").get_text(strip=True).lower()
            value = row.find("td").get_text(strip=True)
            if "façade" in header and "nombre" in header:
                try:
                    data["facades"] = int(value)
                except ValueError:
                    data["facades"] = None
            elif "état du bâtiment" in header:
                data["building_state"] = value
        return data

    def get_interior_infos(self, section: BeautifulSoup) -> dict:
        data = {"furnished": None, "open_fire": None, "kitchen_type": None}
        for row in section.find_all("tr", class_="classified-table__row"):
            header = row.find("th").get_text(strip=True).lower()
            value = row.find("td").get_text(strip=True).lower()
            if "meublé" in header:
                data["furnished"] = 1 if "oui" in value else 0
            elif any(k in header for k in ["feu", "foyer", "cheminée"]):
                data["open_fire"] = 1 if "oui" in value or value.isdigit() else 0
            elif "cuisine" in header:
                if "semi" in value:
                    data["kitchen_type"] = "Semi-équipée"
                elif "équipée" in value:
                    data["kitchen_type"] = "Equipée"
                elif "pas" in value or "non" in value:
                    data["kitchen_type"] = "Pas équipée"
        return data

    def get_exterior_infos(self, section: BeautifulSoup) -> dict:
        data = {"terrace": None, "terrace_surface": None, "garden": None, "garden_surface": None}
        for row in section.find_all("tr"):
            header = row.find("th").get_text(strip=True).lower()
            value = row.find("td").get_text(strip=True).lower()

            if "terrasse" in header:
                data["terrace"] = 1 if "oui" in value else 0 if "non" in value else None
                match = re.search(r"\d+", value)
                data["terrace_surface"] = int(match.group()) if match else None

            elif "jardin" in header:
                data["garden"] = 1 if "oui" in value or re.search(r"\d+\s*m²", value) else 0 if "non" in value else None
                match = re.search(r"\d+", value)
                data["garden_surface"] = int(match.group()) if match else None

        return data

    def get_installations_infos(self, section: BeautifulSoup) -> dict:
        for row in section.find_all("tr"):
            header = row.find("th").get_text(strip=True).lower()
            value = row.find("td").get_text(strip=True).lower()
            if "piscine" in header:
                return {"swimming_pool": 1 if "oui" in value else 0}
        return {"swimming_pool": None}

    def get_overview_infos(self, section: BeautifulSoup) -> dict:
        total_surface = 0
        for item in section.find_all("div", class_="overview__item"):
            text = item.get_text(strip=True).lower()
            match = re.search(r"(\d+)\s*m²", text)
            if match and ("habitable" in text or "terrain" in text):
                total_surface += int(match.group(1))
        return {"land_surface": total_surface}

    def extract_detailed_property_info(self, page, url: str) -> dict:
        page.goto(url)
        page.wait_for_timeout(1000)
        html = page.content()
        soup = BeautifulSoup(html, "html.parser")
        print(soup.prettify())
        container = soup.find("div", class_="container container--body")
        if not container:
            raise ValueError("Section 'container--body' not found in HTML")

        sections = container.find_all('div', class_="text-block")

        infos = {
            "facades": None, "building_state": None,
            "furnished": None, "open_fire": None, "kitchen_type": None,
            "terrace": None, "terrace_surface": None,
            "garden": None, "garden_surface": None,
            "swimming_pool": None,
            "land_surface": None
        }

        for section in sections:
            title_tag = section.find("h2", class_="text-block__title")
            if not title_tag:
                continue
            subtitle = title_tag.get_text(strip=True)
            if subtitle == "Général":
                infos.update(self.get_general_infos(section))
            elif subtitle == "Intérieur":
                infos.update(self.get_interior_infos(section))
            elif subtitle == "Extérieur":
                infos.update(self.get_exterior_infos(section))
            elif subtitle == "Installations":
                infos.update(self.get_installations_infos(section))
            elif subtitle == "Aperçu":
                infos.update(self.get_overview_infos(section))

        return infos