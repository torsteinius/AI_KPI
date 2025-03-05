import os
import csv
import PyPDF2
import requests
from urllib.parse import urlparse
from settings import Settings


class PDFHandler:
    def __init__(self, ticker: str):
        self.__ticker = ticker
        self.__settings = Settings()
        self.__ticker_path = os.path.join(self.__settings.pdf_root, self.__ticker)
        self.__read_files_csv = self.__settings.read_files_csv
        
        # Ensure the CSV directory exists
        os.makedirs(os.path.dirname(self.__read_files_csv), exist_ok=True)

    def read_one_unread_pdf(self) -> str:
        """
        Reads and returns text from the first unread PDF in self.__ticker_path.
        Logs filenames in read_files_csv to avoid duplicate readings.
        """
        read_files = self._get_read_files()
        all_files = [f for f in os.listdir(self.__ticker_path) if f.endswith(".pdf")]

        for filename in all_files:
            if filename not in read_files:
                file_path = os.path.join(self.__ticker_path, filename)
                pdf_text = self.extract_text_from_pdf(file_path)
                read_files.add(filename)
                self._update_read_files(read_files)
                return pdf_text

        print("Ingen nye PDF-filer funnet.")
        return ""

    def read_and_combine_pdfs(self) -> str:
        """
        Reads and combines text from all unread PDFs in self.__ticker_path.
        Logs filenames in read_files_csv to avoid duplicate readings.
        """
        read_files = self._get_read_files()
        all_files = [f for f in os.listdir(self.__ticker_path) if f.endswith(".pdf")]

        combined_text = ""
        newly_read_files = []

        for filename in all_files:
            if filename not in read_files:
                file_path = os.path.join(self.__ticker_path, filename)
                pdf_text = self.extract_text_from_pdf(file_path)
                combined_text += f"\n--- Innhold fra {filename} ---\n" + pdf_text
                newly_read_files.append(filename)
                read_files.add(filename)

        self._update_read_files(read_files)

        already_read_files = [f for f in all_files if f not in newly_read_files]
        if already_read_files:
            print("Følgende filer ble ikke lest (allerede behandlet tidligere):")
            for f in already_read_files:
                print(f)

        return combined_text

    def extract_text_from_pdf(self, pdf_file: str) -> str:
        """Extracts text from a PDF file using PyPDF2."""
        text = ""
        with open(pdf_file, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text

    def _extract_filename_from_url(self, url: str) -> str:
        """Extracts the filename from a URL."""
        return os.path.basename(urlparse(url).path)

    def download_pdf(self, url: str, filename: str=None) -> bool:
        """
        Downloads a PDF from a given URL and saves it in self.__ticker_path with the specified filename.
        Returns True if successful, otherwise False.
        """
        if filename is None:
            filename = self._extract_filename_from_url(url)

        os.makedirs(self.__ticker_path, exist_ok=True)
        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            file_path = os.path.join(self.__ticker_path, filename)
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"Lastet ned PDF: {file_path}")
            return True
        except Exception as e:
            print(f"Kunne ikke laste ned {url}: {e}")
            return False

    def is_pdf_downloaded(self, filename: str) -> bool:
        """Checks if a PDF file has already been downloaded."""
        return os.path.exists(os.path.join(self.__ticker_path, filename))

    def list_downloaded_pdfs(self) -> list:
        """
        Returns a list of dictionaries, each representing a PDF in the ticker folder.
        Each dict has 'filename', 'full_path', and 'processed' (bool indicating if it's in read_files_csv).
        """
        read_files = self._get_read_files()
        pdf_files = [f for f in os.listdir(self.__ticker_path) if f.endswith(".pdf")]

        result = []
        for pdf in pdf_files:
            full_path = os.path.join(self.__ticker_path, pdf)
            processed = pdf in read_files
            result.append({
                "filename": pdf,
                "full_path": full_path,
                "processed": processed
            })
        return result

    def _get_read_files(self) -> set:
        """Retrieves the set of already processed files from read_files_csv."""
        read_files = set()
        if os.path.exists(self.__read_files_csv):
            with open(self.__read_files_csv, "r", newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if row:
                        read_files.add(row[0])
        return read_files

    def _update_read_files(self, read_files: set):
        """Updates the CSV file with the processed filenames."""
        with open(self.__read_files_csv, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            for f in sorted(read_files):
                writer.writerow([f])

    def test_functions(self):
        """
        Må teste flg:
          - generere neste pdf-url dersom man er i neste kvartal
          - finne ut hvilke filer som ikke er lastet ned basert på URL liste og filer
          - sette sammen pdfer
          - lese en og en pdf og generere json for dem separat
          - sette sammen jsons i et bestemt format
        """

        # Mock paths for test
        pdf1 = "pdf/tickers/elab/elliptic-labs-report-2023-q4.pdf"
        pdf2 = "pdf/tickers/elab/elliptic-labs-report-2023-q4.pdf"

        # Example usage:
        text = self.extract_text_from_pdf(pdf1)
        assert text.strip() == "Elliptic Labs"

        # Mock the method for subsequent tests
        self.extract_text_from_pdf = lambda x: "PDF Content"
        result = self.read_one_unread_pdf()  # no argument now
        assert result == "PDF Content"

        # Another mock scenario
        self.extract_text_from_pdf = lambda x: "Content 1" if x == pdf1 else "Content 2"
        result = self.read_and_combine_pdfs()
        assert "Content 1" in result
        assert "Content 2" in result

        # Download test (mocked)
        old_download = self.download_pdf
        self.download_pdf = lambda x, y: True
        success = self.download_pdf("http://example.com/sample.pdf")
        assert success
        self.download_pdf = old_download  # restore

        # Finally, check if the read files are as expected (this might fail in real usage if your CSV is empty)
        read_files = self._get_read_files()
        assert read_files == {pdf1, pdf2}

        # Test listing of PDFs
        pdf_list = self.list_downloaded_pdfs()
        print("Liste over nedlastede PDF-er med status:")
        for p in pdf_list:
            print(p)

        print("All tests passed.")


if __name__ == "__main__":
    pdf_handler = PDFHandler("test_ticker")
    pdf_handler.test_functions()
