import os
import feedparser
import requests
import pandas as pd
from datetime import datetime
from pathlib import Path


class RSSFeedSubscriber:
    """
    Fetches and parses RSS feeds and normalizes entries.
    """
    def __init__(self, feed_urls):
        if isinstance(feed_urls, str):
            self.feed_urls = [feed_urls]
        else:
            self.feed_urls = feed_urls

    def fetch_entries(self):
        all_entries = []
        for url in self.feed_urls:
            feed = feedparser.parse(url)
            for entry in feed.entries:
                published = None
                if hasattr(entry, 'published_parsed'):
                    published = datetime(*entry.published_parsed[:6])
                else:
                    published = datetime.utcnow()
                all_entries.append({
                    'id': entry.get('id', entry.link),
                    'title': entry.get('title', ''),
                    'link': entry.link,
                    'published': published,
                    'summary': entry.get('summary', '')
                })
        # remove duplicates by 'id'
        unique = {e['id']: e for e in all_entries}
        return list(unique.values())


class PDFDownloader:
    """
    Downloads PDF files if not already downloaded.
    """
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.pdf_dir = base_dir / "pdfs"
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def download(self, entry: dict):
        url = entry['link']
        if not url.lower().endswith('.pdf'):
            return None
        date_str = entry['published'].strftime("%Y-%m-%d")
        # sanitize filename
        filename = f"{entry['id'].split('/')[-1].replace('.', '_')}_{date_str}.pdf"
        filepath = self.pdf_dir / filename
        if filepath.exists():
            return filepath

        resp = requests.get(url)
        resp.raise_for_status()
        with open(filepath, 'wb') as f:
            f.write(resp.content)
        return filepath


class MetadataStore:
    """
    Appends RSS metadata entries into daily Parquet files.
    """
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.meta_dir = base_dir / "metadata"
        self.meta_dir.mkdir(parents=True, exist_ok=True)

    def append(self, entries: list):
        df = pd.DataFrame(entries)
        today = datetime.utcnow().strftime("%Y-%m-%d")
        file_path = self.meta_dir / f"rss_meta_{today}.parquet"
        if file_path.exists():
            existing = pd.read_parquet(file_path)
            df = pd.concat([existing, df]).drop_duplicates(subset=['id'])
        df.to_parquet(file_path, index=False)
        return file_path


def main():
    # Define your RSS feed URLs here
    FEED_URLS = [
        "https://newsweb.oslobors.no/websearch-rss?identifierId=NHY",
        # add more feeds as needed
    ]

    base_dir = Path("data").resolve()
    subscriber = RSSFeedSubscriber(FEED_URLS)
    downloader = PDFDownloader(base_dir)
    store = MetadataStore(base_dir)

    entries = subscriber.fetch_entries()
    if not entries:
        print("No new RSS entries found.")
        return

    # Save metadata
    meta_file = store.append(entries)
    print(f"Metadata saved to {meta_file}")

    # Download any new PDFs
    for entry in entries:
        pdf_path = downloader.download(entry)
        if pdf_path:
            print(f"Downloaded PDF: {pdf_path}")


if __name__ == "__main__":
    main()

# Requirements:
# pip install feedparser requests pandas pyarrow
