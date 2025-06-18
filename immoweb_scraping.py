from patchright.sync_api import sync_playwright
from bs4 import BeautifulSoup


with sync_playwright() as p:
    # Démarre Chromium avec interface visible (non headless)
    # browser = p.chromium.launch(headless=False)
    browser = p.chromium.launch_persistent_context(
        user_data_dir=r"C:\playwright",
        channel="chrome",
        headless=False,
        no_viewport=True,
    )
    page = browser.new_page()


    url = "https://www.immoweb.be/fr/recherche/maison-et-appartement/a-vendre?countries=BE&page=1&orderBy=newest"

    page.goto(url)


    html = page.content()
    soup = BeautifulSoup(html, "html.parser")
    search_results = soup.find("div", id="searchResults").find("ul", id="main-content").find("div").find_all('li')

    links = []
    for result in search_results:
        link = result.find("a", class_= "card__title-link")
        if link:
            links.append(link['href'])
    browser.close()