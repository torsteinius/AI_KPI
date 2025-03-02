import os
import csv
import PyPDF2
import requests
from urllib.parse import urlparse
from settings import Settings


class PDFHandler:
    def __init__(self, ticker_path: str):
        self.__ticker_path = ticker_path
        self.__settings = Settings()
        self.__read_files_csv = self.__settings.read_files_csv
        os.makedirs(os.path.dirname(self.__read_files_csv), exist_ok=True)
        self.__ticker_root_path = self.__settings.pdf_root
        self.__full_ticker_path = f"{self.__ticker_root_path}/{self.__ticker_path}"

    def read_one_unread_pdf(self, pdf_dir: str) -> str:
        """
        Reads and returns text from the first unread PDF in the directory.
        Logs filenames in read_files_csv to avoid duplicate readings.
        """
        read_files = self._get_read_files()
        all_files = [f for f in os.listdir(f"{self.__full_ticker_path}") if f.endswith(".pdf")]

        for filename in all_files:
            if filename not in read_files:
                file_path = os.path.join(pdf_dir, filename)
                pdf_text = self.extract_text_from_pdf(file_path)
                read_files.add(filename)
                self._update_read_files(read_files)
                return pdf_text

        print("Ingen nye PDF-filer funnet.")
        return ""

    def read_and_combine_pdfs(self, pdf_dir: str) -> str:
        """
        Reads and combines text from all PDFs in the ticker_folder.
        Logs filenames in read_files_csv to avoid duplicate readings.
        """
        read_files = self._get_read_files()
        all_files = [f for f in os.listdir(f"{self.__full_ticker_path}") if f.endswith(".pdf")]

        combined_text = ""
        newly_read_files = []

        for filename in all_files:
            if filename not in read_files:
                file_path = os.path.join(pdf_dir, filename)
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
        Downloads a PDF from a given URL and saves it in dest_folder with the specified filename.
        Returns True if the download was successful, otherwise False.
        """

        if (filename is None):
            filename = self._extract_filename_from_url(url)

        dest_folder = f"{self.ticker_path}"
        os.makedirs(dest_folder, exist_ok=True)
        try:
            response = requests.get(url, stream=True, timeout=10)
            response.raise_for_status()
            file_path = os.path.join(dest_folder, filename)
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            print(f"Lastet ned PDF: {file_path}")
            return True
        except Exception as e:
            print(f"Kunne ikke laste ned {url}: {e}")
            return False

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
            generere neste pdf-url dersom man er  i neste kvartal
            finne ut hvilke filer som ikke er lastet ned basert på URL liste og filer
            sette sammen pdfer
            lese en og en pdf og generere json for dem seperat
            sette sammen jsons i et bestemt format
        
        """Test the PDFHandler class."""
        pdf1 = "pdf/tickers/elab/elliptic-labs-report-2023-q4.pdf"
        pdf2 = "pdf/tickers/elab/elliptic-labs-report-2023-q4.pdf"

        pdf_handler = PDFHandler("test_ticker")
        text = pdf_handler.extract_text_from_pdf(pdf1)
        assert text.strip() == "Elliptic Labs"

        pdf_handler.extract_text_from_pdf = lambda x: "PDF Content"
        result = pdf_handler.read_one_unread_pdf("test_folder")
        assert result == "PDF Content"

        pdf_handler.extract_text_from_pdf = lambda x: "Content 1" if x == pdf1 else "Content 2"
        result = pdf_handler.read_and_combine_pdfs("test_folder")
        assert "Content 1" in result
        assert "Content 2" in result

        pdf_handler.download_pdf = lambda x, y: True
        success = pdf_handler.download_pdf("http://example.com/sample.pdf")
        assert success

        read_files = pdf_handler._get_read_files()
        assert read_files == {pdf1, pdf2}

        print("All tests passed.")

if __name__ == "__main__":
    pdf_handler = PDFHandler("test_ticker")
    pdf_handler.test_functions()
