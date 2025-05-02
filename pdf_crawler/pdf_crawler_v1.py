import os
import re
import time
import urllib.parse
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def build_search_url(industry_list, languages, keyword=None, page_size=10):
    """
    Compose the GlobeNewswire search URL with your chosen filters.
    """
    base = "https://www.globenewswire.com/en/search/"
    industry_param = ",".join(industry_list)
    lang_param = ",".join(languages)

    path = f"industry/{industry_param}/lang/{lang_param}"
    if keyword:
        path += f"/keyword/{keyword}"

    return urllib.parse.urljoin(base, path) + f"?pageSize={page_size}"

def fetch_press_release_links(search_url, wait=5):
    """
    Use headless Chrome to render the search page and pull all result links.
    """
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=opts)
    driver.get(search_url)
    time.sleep(wait)  # let JS populate the list

    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()

    links = []
    for row in soup.select("ul > li.row"):
        a = row.select_one(".mainLink a")
        if a and a.get("href"):
            links.append("https://www.globenewswire.com" + a["href"])
    return links

def extract_pdf_links(html):
    """
    Return *all* PDF-style URLs found in a press-release page.
    – Classic .pdf endings
    – GlobeNewswire’s /Resource/Download/... attachments
    """
    soup = BeautifulSoup(html, "html.parser")
    pdf_urls = []

    # 1️⃣ Classic .pdf endings
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            full = href if href.startswith("http") else "https://www.globenewswire.com" + href
            if full not in pdf_urls:
                pdf_urls.append(full)

    # 2️⃣ GlobeNewswire attachments area
    for a in soup.select("a[href*='/Resource/Download/']"):
        href = a["href"]
        full = href if href.startswith("http") else "https://www.globenewswire.com" + href
        if full not in pdf_urls:
            pdf_urls.append(full)

    return pdf_urls

def download_pdf(pdf_url, dest_folder, filename_hint):
    """
    Stream-download the PDF into dest_folder. Returns saved filepath.
    """
    os.makedirs(dest_folder, exist_ok=True)
    # Sanitize filename
    safe = re.sub(r"[^A-Za-z0-9\-_.]+", "_", filename_hint)[:60] or "file"
    filename = f"{safe}.pdf"
    path = os.path.join(dest_folder, filename)

    print(f"  ↳ downloading {pdf_url}")
    resp = requests.get(pdf_url, stream=True, timeout=20)
    resp.raise_for_status()
    with open(path, "wb") as f:
        for chunk in resp.iter_content(8192):
            f.write(chunk)
    return path

def main():
    # —— customize these filters ——
    industries = ["Industrials", "Forestry"]
    languages  = ["no", "nb", "nn", "en"]
    keyword    = "pdf"
    page_size  = 10
    # ————————————————————

    search_url = build_search_url(industries, languages, keyword, page_size)
    print(f"Search URL: {search_url}\n")

    links = fetch_press_release_links(search_url)
    print(f"Found {len(links)} press-release pages.\n")

    for url in links:
        print(f"- {url}")
        html = requests.get(url, timeout=20).text
        pdfs = extract_pdf_links(html)

        if not pdfs:
            print("    ✗ no PDF links found.\n")
            continue

        for idx, pdf in enumerate(pdfs, start=1):
            hint = os.path.basename(url) + f"_{idx}"
            saved = download_pdf(pdf, "gnw_pdfs", hint)
            print(f"    ✓ saved {saved}")
        print()

if __name__ == "__main__":
    main()
