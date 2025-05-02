from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import urllib.parse

def fetch_news(industry_list, languages, page_size=10):
    base_url = "https://www.globenewswire.com/en/search/"
    industry_param = ",".join(industry_list)
    lang_param = ",".join(languages)
    params = f"industry/{industry_param}/lang/{lang_param}?pageSize={page_size}"
    url = urllib.parse.urljoin(base_url, params)

    # Setup headless Chrome
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(5)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    rows = soup.select("ul > li.row")

    print(f"Latest GlobeNewswire News [Industries: {industry_param}] [Langs: {lang_param}]:\n")
    if not rows:
        print("No news entries found.")
        return

    for row in rows[:page_size]:
        title_tag = row.select_one(".mainLink")
        link_tag = title_tag.find("a") if title_tag else None

        if title_tag and link_tag:
            title = title_tag.get_text(strip=True)
            link = "https://www.globenewswire.com" + link_tag["href"]
            print(f"- {title}\n  {link}\n")

# Example usage:
fetch_news(industry_list=["Industrials", "Forestry"], languages=["no", "nb", "nn", "en"], page_size=10)
