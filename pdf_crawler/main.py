"""
main.py – orchestration script for quarterly-report harvesting
──────────────────────────────────────────────────────────────
• Reads companies from CSV
• Uses Brave → Google fallback to discover investor-relations pages / PDFs
• If an IR-URL pattern is already known, lets the LLM guess the next report URL
• Validates, downloads, and stores metadata in Parquet via ReportStorage
"""

from pathlib import Path
from datetime import datetime
import logging
import pandas as pd

from models import Company, Report
from storage.report_storage import ReportStorage
from search.brave_engine import BraveSearchEngine
from search.google_engine import GoogleSearchEngine
from crawler.company_crawler import CompanyCrawler
from patterns.report_guesser import ReportPatternGuesser
from download.report_downloader import ReportDownloader

# ──────────────────────────────────────────────────────────────
#  CONFIG
# ──────────────────────────────────────────────────────────────
COMPANY_CSV = Path("data/companies.csv")
DATA_DIR     = Path("data")
REPORTS_PARQ = DATA_DIR / "reports.parquet"
COMP_PARQ    = DATA_DIR / "companies.parquet"
LOG_FILE     = "run.log"

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s"
)

# Search-engine chain: first Brave, then Google
SEARCH_ENGINES = [
    BraveSearchEngine(api_key="YOUR_BRAVE_API_KEY"),
    GoogleSearchEngine(api_key="YOUR_GOOGLE_API_KEY", cse_id="YOUR_CSE_ID")
]

# ──────────────────────────────────────────────────────────────
#  INITIALISE STORAGE
# ──────────────────────────────────────────────────────────────
storage = ReportStorage(
    reports_path=REPORTS_PARQ,
    companies_path=COMP_PARQ
)

# Create directories / parquet files on first run
DATA_DIR.mkdir(exist_ok=True, parents=True)
storage.init_empty_if_missing()

# ──────────────────────────────────────────────────────────────
#  LOAD COMPANY LIST
# ──────────────────────────────────────────────────────────────
companies_df = pd.read_csv(COMPANY_CSV)
companies = [
    Company(
        name=row["name"],
        ticker=row.get("ticker"),
        domain=row.get("domain")          # may be NaN
    )
    for _, row in companies_df.iterrows()
]

# Persist companies (avoids duplicates thanks to ReportStorage logic)
storage.add_companies(companies)

# ──────────────────────────────────────────────────────────────
#  MAIN LOOP
# ──────────────────────────────────────────────────────────────
def main(target_year: int, target_quarter: str = None):
    """
    Parameters
    ----------
    target_year     : int   – e.g. 2024
    target_quarter  : str   – e.g. "Q1"; if None, try to infer latest
    """
    for company in companies:
        try:
            logging.info(f"Processing {company.name}")

            # 1️⃣  Try existing pattern  (LLM-assisted guessing)
            pdf_url = None
            pattern = storage.get_pattern(company)
            if pattern:
                pdf_url = ReportPatternGuesser.next_url(
                    pattern=pattern,
                    year=target_year,
                    quarter=target_quarter
                )

            # 2️⃣  If pattern guess failed, search via engines
            if not pdf_url:
                for engine in SEARCH_ENGINES:
                    result = engine.search_report(
                        company_name=company.name,
                        year=target_year,
                        quarter=target_quarter
                    )
                    if result:
                        pdf_url = result
                        break

            if not pdf_url:
                logging.warning(f"No PDF found for {company.name}")
                continue

            # 3️⃣  Validate / download
            if not ReportDownloader.is_pdf(pdf_url):
                # Sometimes IR page returned – crawl inside it
                pdf_url = CompanyCrawler.find_pdf_inside(pdf_url)

            if not pdf_url:
                logging.warning(f"Still no PDF for {company.name}")
                continue

            file_path = ReportDownloader.fetch(pdf_url, DATA_DIR / company.ticker)
            logging.info(f"Downloaded {file_path}")

            # 4️⃣  Store metadata + maybe update pattern
            report = Report(
                company=company.name,
                ticker=company.ticker,
                year=target_year,
                quarter=target_quarter,
                url=pdf_url,
                local_path=str(file_path),
                downloaded=datetime.utcnow(),
            )
            storage.add_report(report)

            # Guess pattern from successful URL (if we did not already have one)
            if not pattern:
                guessed = ReportPatternGuesser.infer_pattern(pdf_url)
                if guessed:
                    storage.save_pattern(company, guessed)

        except Exception as e:
            logging.exception(f"Unexpected error for {company.name}: {e}")


# ──────────────────────────────────────────────────────────────
#  ENTRY POINT
# ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Example: harvest Q1-2025 reports
    main(target_year=2025, target_quarter="Q1")
