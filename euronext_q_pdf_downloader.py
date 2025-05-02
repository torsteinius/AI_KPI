"""
euronext_q_pdf_downloader.py
----------------------------
Hent Q-rapporter (PDF) for ett gitt issuerId og lagre til lokal mappe.
"""
import json, re, time, requests
from pathlib import Path
from typing  import List

HEAD = {
    "User-Agent": "Mozilla/5.0 (QReportBot/1.0; +https://github.com/…)",
    "x-api-key": "live-streaming-private",
}
GQL = "https://gateway.euronext.com/graphql?locale=nb"
ATT_RE = re.compile(r"\.pdf$", re.I)

def query_press_releases(issuer: int, lang="nb", page=0, size=250):
    payload = {
        "query": """
query companyNews($q: CompanyNewsSearchInput!) {
  companyNewsSearch(query: $q) {
    edges { node { id title publishedDate } }
    pageInfo { hasNextPage }
  }
}
""",
        "variables": {
            "q": {
                "issuerId": issuer,
                "language": lang,
                "page": page,
                "pageSize": size,
            }
        },
    }
    r = requests.post(GQL, json=payload, headers=HEAD, timeout=30)
    r.raise_for_status()
    data = r.json()["data"]["companyNewsSearch"]
    return data["edges"], data["pageInfo"]["hasNextPage"]

def fetch_q_ids(issuer: int) -> List[int]:
    ids = []
    page = 0
    while True:
        edges, has_next = query_press_releases(issuer, page=page)
        for n in edges:
            title = n["node"]["title"].lower()
            if any(tok in title for tok in ("q1", "q2", "q3", "q4", "quarter")):
                ids.append(int(n["node"]["id"]))
        if not has_next:
            break
        page += 1
        time.sleep(0.3)
    return ids

def pdfs_from_press(id_: int):
    url = f"https://live.euronext.com/nb/listview/company-press-release/{id_}"
    html = requests.get(url, headers=HEAD, timeout=30).text
    m = re.search(r"__NEXT_DATA__\s*=\s*({.*?})</script>", html, re.S)
    if not m:
        return []
    data = json.loads(m.group(1))
    paths = (
        ("props","pageProps","companyPressRelease","attachments"),
        ("props","pageProps","pressRelease","attachments"),
    )
    for p in paths:
        try:
            attachments = data
            for key in p:
                attachments = attachments[key]
            return [a["url"] for a in attachments if ATT_RE.search(a["url"])]
        except KeyError:
            continue
    return []

def download(urls, outdir="euronext_reports", delay=0.5):
    Path(outdir).mkdir(exist_ok=True, parents=True)
    for i,u in enumerate(urls,1):
        name = Path(u.split("?")[0]).name
        dest = Path(outdir)/name
        if dest.exists():
            print(f"[{i}] finnes: {name}")
            continue
        print(f"[{i}] henter {name}")
        try:
            r = requests.get(u, headers=HEAD, timeout=60)
            r.raise_for_status()
            dest.write_bytes(r.content)
            time.sleep(delay)
        except Exception as e:
            print(f"   ⚠️  {e}")

if __name__ == "__main__":
    ISSUER = 118710          # ← Nekkar ASA – bytt til selskapet ditt
    ids = fetch_q_ids(ISSUER)
    print(f"Fant {len(ids)} Q-pressemeldinger: {ids}")

    pdf_set = set()
    for pid in ids:
        pdf_set |= set(pdfs_from_press(pid))
        time.sleep(0.3)

    print(f"Totalt {len(pdf_set)} PDF-er")
    download(pdf_set, outdir=f"euronext_reports/{ISSUER}")
