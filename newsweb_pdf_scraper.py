#!/usr/bin/env python3
"""
newsweb_pdf_scraper.py

Henter PDF-vedlegg fra NewsWeb (newsweb.oslobors.no) for ett gitt ticker-symbol.
Bruker det interne JSON-API-et på query.jsp?action=3 for å få liste over meldinger,
og deretter parser hver melding for .pdf-lenker.
"""
import re, time, argparse
from pathlib import Path
from typing import List

try:
    import cloudscraper
    Session = cloudscraper.create_scraper
except ImportError:
    import requests
    Session = requests.Session

from bs4 import BeautifulSoup

# --------------------------------------------------------------------
def get_announcements(symbol: str, language_id: int = 1) -> List[dict]:
    """
    Henter JSON-liste over meldinger fra NewsWeb for gitt ticker.
    """
    session = Session()
    url = "https://newsweb.oslobors.no/query.jsp"
    r = session.get(
        url,
        params={"action": 3, "languageID": language_id, "symbol": symbol.upper()},
        timeout=30,
    )
    r.raise_for_status()
    return r.json()  # antatt å være liste av dicts med bl.a. 'MsgNo' eller 'msgNo'

def get_pdf_links_from_message(message_id: str) -> List[str]:
    """
    Går inn på meldingssiden og finner alle <a href="*.pdf">-lenker.
    """
    session = Session()
    url = f"https://newsweb.oslobors.no/message/{message_id}"
    r = session.get(url, timeout=30)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.lower().endswith(".pdf"):
            if href.startswith("/"):
                href = "https://newsweb.oslobors.no" + href
            links.append(href)
    return links

def download_pdfs(urls: List[str], outdir: Path, delay: float = 0.5):
    """
    Laster ned alle PDF-lenkene til outdir. Gjør ingen dobbeltnedlasting.
    """
    outdir.mkdir(parents=True, exist_ok=True)
    session = Session()
    for i, url in enumerate(sorted(set(urls)), 1):
        fname = Path(url.split("?")[0]).name
        dest = outdir / fname
        if dest.exists():
            print(f"[{i}] hopper over (finnes): {fname}")
            continue
        print(f"[{i}] laster ned: {fname}")
        r = session.get(url, timeout=60)
        r.raise_for_status()
        dest.write_bytes(r.content)
        time.sleep(delay)

def main():
    ap = argparse.ArgumentParser(
        description="Scraper for NewsWeb PDF-vedlegg (ticker symbol)."
    )
    ap.add_argument("symbol", help="Ticker-symbol (f.eks. AXFOOD)")
    ap.add_argument(
        "-l", "--language", type=int, default=1,
        help="languageID for API (1=nb, 2=en). Standard=1"
    )
    ap.add_argument(
        "-o", "--outdir", default="newsweb_pdfs",
        help="Mappe hvor PDF-ene lagres"
    )
    args = ap.parse_args()

    print(f"↳ Henter meldingsliste for {args.symbol} …")
    ann = get_announcements(args.symbol, args.language)
    print(f"   fant {len(ann)} meldinger")

    pdf_links: List[str] = []
    for rec in ann:
        # prøv flere mulige nøkler
        msgno = rec.get("MsgNo") or rec.get("msgNo") or rec.get("messageNumber")
        if msgno:
            pdf_links += get_pdf_links_from_message(str(msgno))
            time.sleep(0.2)

    print(f"↳ fant {len(pdf_links)} PDF-lenker totalt")
    download_pdfs(pdf_links, Path(args.outdir) / args.symbol.upper())

if __name__ == "__main__":
    main()
