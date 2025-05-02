import re, time, asyncio, aiohttp
from pathlib import Path
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright
from tqdm.asyncio import tqdm



START_URL = "https://live.euronext.com/nb/products/equities/company-news"
START_URL = "https://live.euronext.com/nb/listview/company-press-release/118710"
OUTPUT_DIR = Path("euronext_reports")
PDF_RE = re.compile(r"https?://[^\s\"']+?\.pdf", re.I)

def slugify(text, n=120):
    import re, unicodedata, pathlib
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^\w\s-]", " ", text).strip()
    text = re.sub(r"\s+", "_", text)
    return (text or "file")[:n] + ".pdf"

async def gather_pdfs():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print("↳ Laster siden …")
        await page.goto(START_URL, wait_until="domcontentloaded")

        # 1) lukk cookie/consent hvis den finnes
        try:
            await page.click("button#onetrust-accept-btn-handler", timeout=3000)
            print("   – cookie-banner lukket")
        except:
            pass  # ingen banner

        # 2) vent til trafikken har roet seg
        await page.wait_for_load_state("networkidle", timeout=20000)

        html = await page.content()
        await browser.close()

    return set(PDF_RE.findall(html))

async def download_all(links):
    OUTPUT_DIR.mkdir(exist_ok=True, parents=True)
    async with aiohttp.ClientSession(
        headers={"User-Agent": "Mozilla/5.0 (EuronextPDFBot/1.0)"}
    ) as sess:
        tasks = []
        for url in links:
            name = slugify(Path(urlparse(url).path).stem)
            dest = OUTPUT_DIR / name
            if dest.exists():
                continue
            tasks.append(_dl(sess, url, dest))
        for f in tqdm(asyncio.as_completed(tasks), total=len(tasks), desc="Nedlasting"):
            await f

async def _dl(sess, url, dest):
    try:
        async with sess.get(url, timeout=30) as r:
            if r.status == 200:
                dest.write_bytes(await r.read())
    except Exception as e:
        print(f"⚠️  kunne ikke hente {url}: {e}")

async def main():
    pdf_links = await gather_pdfs()
    print(f"Fant {len(pdf_links)} PDF-lenker")
    if pdf_links:
        await download_all(pdf_links)
    print("✅ ferdig")

if __name__ == "__main__":
    asyncio.run(main())
