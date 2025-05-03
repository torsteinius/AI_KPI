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
    time.sleep(wait)  # allow JS to populate the list

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
    Return all PDF-style URLs found in a press-release page:
    - Classic .pdf endings
    - GlobeNewswire’s /Resource/Download/... attachments
    """
    soup = BeautifulSoup(html, "html.parser")
    pdf_urls = []

    # Classic .pdf endings
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            full = href if href.startswith("http") else "https://www.globenewswire.com" + href
            if full not in pdf_urls:
                pdf_urls.append(full)

    # GlobeNewswire attachment links
    for a in soup.select("a[href*='/Resource/Download/']"):
        href = a["href"]
        full = href if href.startswith("http") else "https://www.globenewswire.com" + href
        if full not in pdf_urls:
            pdf_urls.append(full)

    return pdf_urls


def get_filepath(dest_folder, filename_hint):
    """
    Generate a safe filepath in dest_folder for filename_hint.
    """
    os.makedirs(dest_folder, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9\-_.]+", "_", filename_hint)[:100] or "file"
    return os.path.join(dest_folder, f"{safe}.pdf")


def file_exists(dest_folder, filename_hint):
    """
    Check if a file with the given filename_hint already exists in dest_folder.
    """
    path = get_filepath(dest_folder, filename_hint)
    return os.path.exists(path)


def download_pdf(pdf_url, filepath):
    """
    Stream-download the PDF at pdf_url into filepath, verifying:
      1) Content-Type header contains 'pdf'
      2) File starts with '%PDF'
    Returns True if saved, False otherwise.
    """
    print(f"  ↳ fetching {pdf_url}")
    try:
        resp = requests.get(pdf_url, stream=True, timeout=20)
        resp.raise_for_status()
    except Exception as e:
        print(f"    ⚠️ failed to fetch: {e}")
        return False

    # 1) Check Content-Type header
    ct = resp.headers.get("Content-Type", "")
    if "pdf" not in ct.lower():
        print(f"    ⚠️ skipped: Content-Type is '{ct}', not PDF")
        return False

    # 2) Check magic number in first chunk
    chunks = resp.iter_content(chunk_size=8192)
    try:
        first = next(chunks)
    except StopIteration:
        print("    ⚠️ skipped: no data received")
        return False

    if not first.startswith(b"%PDF"):
        print("    ⚠️ skipped: file does not start with '%PDF'")
        return False

    # Write the PDF to disk
    with open(filepath, "wb") as f:
        f.write(first)
        for chunk in chunks:
            f.write(chunk)

    print(f"    ✓ saved {filepath}")
    return True


def main():
    # Customize your filters here
    industries = ["Industrials", "Forestry", "Financials"]
    languages  = ["no", "nb", "nn", "sv"]  # include Swedish
    keyword    = "pdf"                       # only press releases linking PDFs
    page_size  = 30

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

        for idx, pdf_url in enumerate(pdfs, start=1):
            hint = f"{os.path.basename(url)}_{idx}"
            if file_exists("gnw_pdfs", hint):
                print(f"    ⚠️ already exists: {get_filepath('gnw_pdfs', hint)}")
                continue
            filepath = get_filepath("gnw_pdfs", hint)
            download_pdf(pdf_url, filepath)
        print()

if __name__ == "__main__":
    main()
