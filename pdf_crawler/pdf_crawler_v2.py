import os, re, time, json, urllib.parse, sqlite3, requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# ───────────────────────────────────────────────────────────────────────────────
# helpers
# ───────────────────────────────────────────────────────────────────────────────
def _ensure_dir(path: str):
    os.makedirs(path, exist_ok=True)
    return path


class _SQLiteIndex:
    """url->local-path de-duplication"""
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        cur = self.conn.cursor()
        cur.execute(
            "CREATE TABLE IF NOT EXISTS store "
            "(url TEXT PRIMARY KEY, path TEXT, meta TEXT)"
        )
        self.conn.commit()

    def has(self, url: str) -> bool:
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM store WHERE url=? LIMIT 1", (url,))
        return cur.fetchone() is not None

    def add(self, url: str, path: str, meta: str = ""):
        cur = self.conn.cursor()
        cur.execute(
            "INSERT OR IGNORE INTO store (url,path,meta) VALUES (?,?,?)",
            (url, path, meta),
        )
        self.conn.commit()


# ───────────────────────────────────────────────────────────────────────────────
# PDF store
# ───────────────────────────────────────────────────────────────────────────────
class PDFStore:
    def __init__(self, base_dir: str = "Data"):
        self.pdf_dir = _ensure_dir(os.path.join(base_dir, "pdfs"))
        self.db      = _SQLiteIndex(os.path.join(base_dir, "pdf_index.db"))

    def get_or_download(self, url: str, filename_hint: str):
        if self.db.has(url):
            print(f"    ⚠️ PDF already stored for {url}")
            return None
        path = self._download(url, filename_hint)
        if path:
            self.db.add(url, path)
        return path

    # ---------------------
    def _download(self, pdf_url: str, hint: str):
        safe = re.sub(r"[^A-Za-z0-9\-_.]+", "_", hint)[:100] or "file"
        path = os.path.join(self.pdf_dir, f"{safe}.pdf")

        print(f"      ↳ downloading {pdf_url}")
        try:
            r = requests.get(pdf_url, stream=True, timeout=20)
            r.raise_for_status()
        except Exception as e:
            print(f"        download failed: {e}")
            return None

        # verify PDF
        ct    = r.headers.get("Content-Type", "")
        first = next(r.iter_content(8192), b"")
        if "pdf" not in ct.lower() and not first.startswith(b"%PDF"):
            print("        ⚠️ not a PDF; skipped")
            return None

        with open(path, "wb") as f:
            f.write(first)
            for chunk in r.iter_content(8192):
                f.write(chunk)

        print(f"        ✓ saved {path}")
        return path


# ───────────────────────────────────────────────────────────────────────────────
# News store
# ───────────────────────────────────────────────────────────────────────────────
class NewsStore:
    def __init__(self, base_dir: str = "Data"):
        # 🔽 change "news" → "metadata"
        self.meta_dir = _ensure_dir(os.path.join(base_dir, "metadata"))
        self.db       = _SQLiteIndex(os.path.join(base_dir, "news_index.db"))

    def store(self, pr_dict: dict):
        url = pr_dict["url"]
        if self.db.has(url):
            print("    ⚠️ metadata already stored")
            return None

        safe  = re.sub(r"[^A-Za-z0-9\\-_.]+", "_", pr_dict["title"])[:80]
        fname = f"{pr_dict['date']}_{safe}.json"
        path  = os.path.join(self.meta_dir, fname)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(pr_dict, f, ensure_ascii=False, indent=2)

        self.db.add(url, path, pr_dict.get("ticker", ""))
        print(f"    📝 metadata saved {path}")
        return path


# ───────────────────────────────────────────────────────────────────────────────
# Crawler
# ───────────────────────────────────────────────────────────────────────────────
class GlobeNewswireCrawler:
    def __init__(
        self,
        industries,
        languages,
        keyword="pdf",
        page_size=30,
        wait=5,
        base_dir="Data",
    ):
        self.industries = industries
        self.languages  = languages
        self.keyword    = keyword
        self.page_size  = page_size
        self.wait       = wait

        self.pdf_store  = PDFStore(base_dir)
        self.news_store = NewsStore(base_dir)

    # ---------------- run -----------------
    def run(self):
        url = self._search_url()
        print("Search URL:", url, "\n")

        links = self._fetch_links(url)
        print(f"Found {len(links)} press releases\n")

        for pr_link in links:
            print("•", pr_link)
            html      = requests.get(pr_link, timeout=20).text
            pdf_urls  = self._extract_pdfs(html)
            saved_pdfs = []

            for idx, pdf in enumerate(pdf_urls, 1):
                hint = os.path.basename(pr_link) + f"_{idx}"
                path = self.pdf_store.get_or_download(pdf, hint)
                if path:
                    saved_pdfs.append(path)

            pr_meta = self._make_metadata(pr_link, html, saved_pdfs)
            self.news_store.store(pr_meta)
            print()

    # ---------------- helpers --------------
    def _search_url(self):
        base = "https://www.globenewswire.com/en/search/"
        ind  = ",".join(self.industries)
        lng  = ",".join(self.languages)
        path = f"industry/{ind}/lang/{lng}"
        if self.keyword:
            path += f"/keyword/{self.keyword}"
        return urllib.parse.urljoin(base, path) + f"?pageSize={self.page_size}"

    def _fetch_links(self, search_url):
        opts = Options()
        opts.add_argument("--headless")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--no-sandbox")

        drv = webdriver.Chrome(options=opts)
        drv.get(search_url)
        time.sleep(self.wait)

        soup = BeautifulSoup(drv.page_source, "html.parser")
        drv.quit()
        return [
            "https://www.globenewswire.com" + a["href"]
            for a in soup.select("ul > li.row .mainLink a[href]")
        ]

    @staticmethod
    def _extract_pdfs(html):
        soup = BeautifulSoup(html, "html.parser")
        urls = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.lower().endswith(".pdf") or "/Resource/Download/" in href:
                full = href if href.startswith("http") else "https://www.globenewswire.com" + href
                if full not in urls:
                    urls.append(full)
        return urls

    def _make_metadata(self, url, html, pdf_paths):
        soup  = BeautifulSoup(html, "html.parser")
        title = soup.find("title").get_text(strip=True)

        dm   = re.search(r"/news-release/(\\d{4})/(\\d{2})/(\\d{2})", url)
        date = "-".join(dm.groups()) if dm else "unknown"
        lang = "sv" if "/sv/" in url else "no" if "/no/" in url else "en"

        body_tag = soup.find("div", class_="article-body") or soup
        text = body_tag.get_text(" ", strip=True)[:2000]        # first 2 k chars

        return {
            "title": title,
            "url":   url,
            "date":  date,
            "language": lang,
            "ticker": "UNKNOWN",
            "sector": ",".join(self.industries),
            "country": {"sv": "SE", "no": "NO"}.get(lang, "INTL"),
            "text": text,
            "pdf_files": pdf_paths,
        }


# ───────────────────────────────────────────────────────────────────────────────
# main
# ───────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    crawler = GlobeNewswireCrawler(
        industries=["Industrials", "Forestry", "Financials"],
        languages=["no", "nb", "nn", "sv"],
        keyword="pdf",
        page_size=50,
        base_dir="Data"
    )
    crawler.run()
