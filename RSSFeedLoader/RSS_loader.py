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
        self.feed_urls = [feed_urls] if isinstance(feed_urls, str) else feed_urls

    def fetch_entries(self):
        all_entries = []
        for url in self.feed_urls:
            print(f"Fetching RSS feed: {url}")
            feed = feedparser.parse(url)
            print(f"  Found {len(feed.entries)} entries")
            for entry in feed.entries:
                published = datetime.utcnow()
                if getattr(entry, 'published_parsed', None):
                    published = datetime(*entry.published_parsed[:6])
                all_entries.append({
                    'id': entry.get('id', entry.link),
                    'title': entry.get('title', ''),
                    'link': entry.link,
                    'published': published,
                    'summary': entry.get('summary', '')
                })
        # remove duplicates by 'id'
        unique_entries = list({e['id']: e for e in all_entries}.values())
        print(f"Total unique entries fetched: {len(unique_entries)}")
        return unique_entries


class PDFDownloader:
    """
    Downloads PDF files if not already downloaded.
    """
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.pdf_dir = base_dir / "pdfs"
        if self.pdf_dir.exists() and not self.pdf_dir.is_dir():
            raise NotADirectoryError(
                f"Expected a directory at {self.pdf_dir}, but found a file. "
                "Please remove or rename it before running the downloader."
            )
        self.pdf_dir.mkdir(parents=True, exist_ok=True)

    def download(self, entry: dict):
        url = entry['link']
        if not url.lower().endswith('.pdf'):
            return None
        date_str = entry['published'].strftime("%Y-%m-%d")
        filename = f"{entry['id'].split('/')[-1].replace('.', '_')}_{date_str}.pdf"
        filepath = self.pdf_dir / filename
        if filepath.exists():
            print(f"PDF already exists: {filepath}")
            return filepath
        print(f"Downloading PDF: {url}")
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
        print(f"Metadata written to {file_path} (total rows: {len(df)})")
        return file_path


def main():
    FEED_URLS = [
        "https://newsweb.oslobors.no/websearch-rss?identifierId=NHY",
        # Add more RSS feed URLs here
    ]

    base_dir = Path("data").resolve()
    subscriber = RSSFeedSubscriber(FEED_URLS)
    downloader = PDFDownloader(base_dir)
    store = MetadataStore(base_dir)

    entries = subscriber.fetch_entries()
    if not entries:
        print("No new RSS entries found. Check your feed URLs or network connectivity.")
        return

    meta_file = store.append(entries)
    for entry in entries:
        try:
            pdf_path = downloader.download(entry)
            if pdf_path:
                print(f"Saved PDF: {pdf_path}")
        except Exception as e:
            print(f"Error downloading {entry['link']}: {e}")


if __name__ == "__main__":
    main()

# Requirements:
# pip install feedparser requests pandas pyarrow
