import os
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path

class MFNReportScraper:
    def __init__(self, company_slug: str, output_dir: str = "mfn_reports", delay: float = 5.0):
        self.company_slug = company_slug.lower()
        self.base_url = f"https://mfn.se/all/a/{self.company_slug}"
        self.output_dir = Path(output_dir) / self.company_slug
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.delay = delay  # delay between requests to avoid suspicion

    def get_pdf_links(self):
        print(f"Fetching PDF links for '{self.company_slug}' from MFN...")
        response = requests.get(self.base_url)
        soup = BeautifulSoup(response.text, "html.parser")
        links = []

        for article in soup.select("article"):
            link_tag = article.find("a")
            if not link_tag:
                continue

            href = link_tag.get("href")
            if href and href.endswith(".pdf"):
                full_url = urljoin("https://mfn.se", href)
                title = article.text.strip().split("\n")[0][:80].replace(" ", "_").replace("/", "_")
                filename = f"{title}.pdf"
                links.append((full_url, filename))

        print(f"Found {len(links)} PDF reports.")
        return links

    def download_pdfs(self):
        links = self.get_pdf_links()
        for idx, (url, filename) in enumerate(links):
            path = self.output_dir / filename
            if path.exists():
                print(f"[{idx+1}/{len(links)}] Skipping already downloaded: {filename}")
                continue

            print(f"[{idx+1}/{len(links)}] Downloading: {filename}")
            response = requests.get(url)
            with open(path, "wb") as f:
                f.write(response.content)
            time.sleep(self.delay)

        print("✅ Done downloading all available PDFs.")

# Example usage
if __name__ == "__main__":
    scraper = MFNReportScraper("axfood", delay=8.0)  # Change 'axfood' to any company slug from MFN
    scraper.download_pdfs()
