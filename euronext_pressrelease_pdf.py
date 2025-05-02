"""
euronext_pressrelease_pdf.py

Laster ned PDF-vedlegg fra én eller flere Euronext-pressemeldinger ved å
parses __NEXT_DATA__ JSON-bloben som ligger inne i HTML-en.
"""
import re, json, time, requests
from pathlib import Path
from typing import Iterable

HEADERS = {
    "User-Agent": "Mozilla/5.0 (PDFBot/1.0; +https://github.com/your-repo)"
}
NEXT_RE = re.compile(
    r'<script[^>]+id="__NEXT_DATA__"[^>]*>\s*({.*?})\s*</script>', re.S
)

PDF_RE  = re.compile(r"\.pdf$", re.I)


class EuronextPressPDF:
    BASE = "https://live.euronext.com/nb/listview/company-press-release/{id}"

    def __init__(self, outdir: str = "euronext_reports", delay: float = 1.0):
        self.outdir = Path(outdir)
        self.delay  = delay
        self.outdir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------ #

    def fetch_one(self, pr_id: int) -> list[str]:
        """Returnerer liste med PDF-URL-er fra én pressemelding-ID."""
        url = self.BASE.format(id=pr_id)
        print(f"↳ Henter {url}")
        html = requests.get(url, headers=HEADERS, timeout=30).text

        m = NEXT_RE.search(html)
        if not m:
            print("   ⚠️  Fant ikke __NEXT_DATA__; kanskje Cloudflare blokkerte oss?")
            return []

        data = json.loads(m.group(1))
        # JSON-stien har variert litt; prøv begge:
        try:
            attach = (
                data["props"]["pageProps"]["companyPressRelease"]["attachments"]
            )
        except KeyError:
            attach = (
                data["props"]["pageProps"]["pressRelease"]["attachments"]
            )

        pdfs = [a["url"] for a in attach if PDF_RE.search(a["url"])]
        print(f"   → fant {len(pdfs)} PDF-er")
        return pdfs

    # ------------------------------------------------------------------ #

    def download(self, urls: Iterable[str]):
        for i, link in enumerate(urls, 1):
            name = Path(link.split("?")[0]).name  # beholder originalt filnavn
            dest = self.outdir / name
            if dest.exists():
                print(f"[{i}] Skipper (finnes): {name}")
                continue
            print(f"[{i}] Laster ned {name}")
            try:
                r = requests.get(link, headers=HEADERS, timeout=60)
                r.raise_for_status()
                dest.write_bytes(r.content)
            except Exception as e:
                print(f"   ⚠️  Feil: {e}")
            time.sleep(self.delay)

    # ------------------------------------------------------------------ #

    def fetch_and_save(self, *ids: int):
        pdf_set: set[str] = set()
        for pid in ids:
            pdf_set |= set(self.fetch_one(pid))
            time.sleep(self.delay)
        self.download(pdf_set)


# ---------------------------- EKSEMPEL ---------------------------- #

if __name__ == "__main__":
    grabber = EuronextPressPDF(outdir="euronext_reports", delay=0.8)

    # === Manuell liste med Q-rapport-ID-er ===
    grabber.fetch_and_save(
        12622683,   # ← Q-rapporten du pekte på
        12548732,   # ← legg inn flere ID-er her
        12234567,
    )
