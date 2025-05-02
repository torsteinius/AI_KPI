#!/usr/bin/env python3
"""
newsweb_report_downloader.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Last ned PDF-vedlegg fra NewsWeb/Euronext for ett selskap (issuerId eller ISIN).
Du kan filtrere på rapport-typer (kvartals-, års-, presentasjon, eller 'all').

Eksempler:
    python newsweb_report_downloader.py --issuer-id 118710 -t quarterly presentation
    python newsweb_report_downloader.py --isin NO0010890726 -t all -o reports
"""
from __future__ import annotations
import argparse, json, re, sys, time
from pathlib import Path, PurePosixPath
from typing import Iterable

try:
    import cloudscraper
except ImportError:
    cloudscraper = None

import requests

# -------------------------------------------------------------------
# Konfig: prøv disse GraphQL-endepunktene i rekkefølge om 404
GQL_ENDPOINTS = [
    "https://gateway.euronext.com/graphql?locale=nb",
    "https://gateway.euronext.com/graphql",
    "https://gateway.euronext.com/graphql?locale=en",
]
HEAD = {
    "User-Agent": "Mozilla/5.0 (NewsWebBot/2.0; +https://github.com/your-repo)",
    "x-api-key":  "live-streaming-private",
}
PAGE_SIZE = 250
PDF_RE    = re.compile(r"\.pdf$", re.I)

TYPE_PATTERNS = {
    "quarterly":    r"\b(q[1-4]|quarter|interim|half|h[12])\b",
    "annual":       r"\b(annual|årsrapport|årsregnskap|year[- ]?end)\b",
    "presentation": r"\b(presentation|presentasjon)\b",
}
TYPE_PATTERNS["all"] = r"."  # matcher alt


# ====================================================================
# GraphQL-hjelper med fallback (404-håndtering)
# ====================================================================
def _post(payload: dict) -> dict:
    session = cloudscraper.create_scraper() if cloudscraper else requests
    last_err = None
    for url in GQL_ENDPOINTS:
        try:
            r = session.post(url, json=payload, headers=HEAD, timeout=30)
        except Exception as e:
            last_err = e
            continue
        if r.status_code == 404:
            last_err = RuntimeError(f"404 fra {url}")
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"HTTP {r.status_code} fra {url}: {r.text[:120]}")
        return r.json()
    # hvis vi kommer hit, alle endepunkter feilet
    raise RuntimeError(f"Kunne ikke nå GraphQL (siste feil: {last_err})")


# ====================================================================
# ISIN → issuerId
# ====================================================================
def issuer_id_from_isin(isin: str) -> int | None:
    payload = {
        "query": """
query search($q: InstrumentSearchInput!) {
  instrumentSearch(query:$q){
    edges { node { issuer { id name } } }
  }
}
""",
        "variables": {
            "q": {"text": isin, "language": "en", "page": 0, "pageSize": 10}
        },
    }
    edges = _post(payload)["data"]["instrumentSearch"]["edges"]
    for e in edges:
        issuer = e["node"]["issuer"]
        if issuer:
            return int(issuer["id"])
    return None


# ====================================================================
# Hent pressemelding-IDer som matcher valgte typer
# ====================================================================
def relevant_press_ids(
    issuer_id: int, types: list[str], languages: list[str]
) -> list[int]:
    pat = re.compile("|".join(TYPE_PATTERNS[t] for t in types), re.I)
    ids: set[int] = set()

    for lang in languages:
        page = 0
        while True:
            payload = {
                "query": """
query news($q:CompanyNewsSearchInput!){
  companyNewsSearch(query:$q){
    edges{ node{ id title } }
    pageInfo{ hasNextPage }
  }
}
""",
                "variables": {
                    "q": {
                        "issuerId": issuer_id,
                        "language": lang,
                        "page": page,
                        "pageSize": PAGE_SIZE,
                    }
                },
            }
            data = _post(payload)["data"]["companyNewsSearch"]
            for edge in data["edges"]:
                title = edge["node"]["title"]
                if pat.search(title):
                    ids.add(int(edge["node"]["id"]))
            if not data["pageInfo"]["hasNextPage"]:
                break
            page += 1
            time.sleep(0.25)
    return sorted(ids)


# ====================================================================
# Hent PDF-URLer for én pressemelding
# ====================================================================
def pdf_urls_for_press(press_id: int) -> list[str]:
    payload = {
        "query": """
query one($id:Int!){
  companyPressRelease(id:$id){
    attachments { url }
  }
}
""",
        "variables": {"id": press_id},
    }
    atts = _post(payload)["data"]["companyPressRelease"]["attachments"]
    return [a["url"] for a in atts if PDF_RE.search(a["url"])]


# ====================================================================
# Last ned PDF-ene
# ====================================================================
def download(urls: Iterable[str], outdir: Path, delay: float = 0.4):
    outdir.mkdir(parents=True, exist_ok=True)
    ses = cloudscraper.create_scraper() if cloudscraper else requests
    for i, url in enumerate(urls, 1):
        fname = PurePosixPath(url.split("?")[0]).name
        dest  = outdir / fname
        if dest.exists():
            print(f"[{i}] hopper over (finnes): {fname}")
            continue
        print(f"[{i}] henter {fname}")
        try:
            r = ses.get(url, headers=HEAD, timeout=60)
            r.raise_for_status()
            dest.write_bytes(r.content)
        except Exception as e:
            print(f"   ⚠️ Feil ved {url}: {e}")
        time.sleep(delay)


# ====================================================================
# CLI
# ====================================================================
def parse_cli(argv=None):
    ap = argparse.ArgumentParser(
        description="Last ned PDF-vedlegg fra NewsWeb/Euronext."
    )
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--issuer-id", type=int, dest="issuer_id",
        help="Euronext issuerId (heltall), f.eks. 118710"
    )
    group.add_argument(
        "--isin", dest="isin",
        help="ISIN-kode for selskapet, f.eks. NO0010890726"
    )
    ap.add_argument(
        "-t", "--types", nargs="+", default=["quarterly"],
        choices=list(TYPE_PATTERNS.keys()),
        help="Typer rapporter å hente (kvartal, års, presentasjon, all)"
    )
    ap.add_argument(
        "-l", "--lang", nargs="+", default=["nb", "en"],
        help="Språk å søke i. Standard: nb en"
    )
    ap.add_argument(
        "-o", "--outdir", default="newsweb_reports",
        help="Rotmappe for nedlasting"
    )
    return ap.parse_args(argv)


def main(argv=None):
    args = parse_cli(argv)

    if args.issuer_id is not None:
        issuer = args.issuer_id
    else:
        print("↳ Slår opp issuerId for ISIN …")
        issuer = issuer_id_from_isin(args.isin)
        if issuer is None:
            print("❌ Fant ingen issuerId for ISIN:", args.isin)
            sys.exit(1)
        print("   issuerId funnet:", issuer)

    print(f"↳ Henter pressemeldinger for issuerId {issuer} …")
    press_ids = relevant_press_ids(issuer, args.types, args.lang)
    print(f"   fant {len(press_ids)} meldinger som matcher {args.types}: {press_ids}")

    pdfs: set[str] = set()
    for pid in press_ids:
        pdfs.update(pdf_urls_for_press(pid))
        time.sleep(0.25)

    print(f"   fant totalt {len(pdfs)} PDF-vedlegg")
    download(pdfs, Path(args.outdir) / str(issuer))


if __name__ == "__main__":
    # --------------------------------------------------------------------------
    # Legg inn dine ønskede parametre her når du kjører i VSCode:
    # --------------------------------------------------------------------------
    argv = [
        "--issuer-id", "118710",
        "-t", "quarterly", "presentation",
        "-l", "nb", "en",
        "-o", "my_reports"
    ]
    main(argv)
