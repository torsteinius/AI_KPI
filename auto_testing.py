import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import csv
import PyPDF2
import requests
from pdf_handler import PDFHandler  # Assuming your class is in pdf_handler.py

class TestPDFHandler(unittest.TestCase):
    
    @patch("builtins.open", new_callable=mock_open, read_data="mock pdf data")
    @patch("PyPDF2.PdfReader")
    def test_extract_text_from_pdf(self, mock_pdf_reader, mock_file):
        mock_reader_instance = mock_pdf_reader.return_value
        mock_page = MagicMock()
        mock_page.extract_text.return_value = "Sample PDF text"
        mock_reader_instance.pages = [mock_page]

        pdf_handler = PDFHandler("test_ticker")
        text = pdf_handler.extract_text_from_pdf("dummy.pdf")
        self.assertEqual(text.strip(), "Sample PDF text")

    @patch("os.listdir", return_value=["file1.pdf", "file2.pdf"])
    @patch("builtins.open", new_callable=mock_open)
    @patch("csv.reader", return_value=[["file1.pdf"]])
    def test_read_one_unread_pdf(self, mock_csv_reader, mock_file, mock_listdir):
        pdf_handler = PDFHandler("test_ticker")
        pdf_handler.extract_text_from_pdf = MagicMock(return_value="PDF Content")
        result = pdf_handler.read_one_unread_pdf("test_folder")
        self.assertEqual(result, "PDF Content")

    @patch("os.listdir", return_value=["file1.pdf", "file2.pdf"])
    @patch("builtins.open", new_callable=mock_open)
    @patch("csv.reader", return_value=[["file1.pdf"]])
    def test_read_and_combine_pdfs(self, mock_csv_reader, mock_file, mock_listdir):
        pdf_handler = PDFHandler("test_ticker")
        pdf_handler.extract_text_from_pdf = MagicMock(side_effect=["Content 1", "Content 2"])
        result = pdf_handler.read_and_combine_pdfs("test_folder")
        self.assertIn("Content 1", result)
        self.assertIn("Content 2", result)

    @patch("requests.get")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.makedirs")
    def test_download_pdf(self, mock_makedirs, mock_open, mock_requests_get):
        mock_response = MagicMock()
        mock_response.iter_content = MagicMock(return_value=[b"chunk1", b"chunk2"])
        mock_response.raise_for_status = MagicMock()
        mock_requests_get.return_value = mock_response

        pdf_handler = PDFHandler("test_ticker")
        success = pdf_handler.download_pdf("http://example.com/sample.pdf")
        self.assertTrue(success)
        mock_open.assert_called_once()

    @patch("os.path.exists", return_value=True)
    @patch("builtins.open", new_callable=mock_open, read_data="file1.pdf\nfile2.pdf\n")
    def test_get_read_files(self, mock_file, mock_exists):
        pdf_handler = PDFHandler("test_ticker")
        read_files = pdf_handler._get_read_files()
        self.assertEqual(read_files, {"file1.pdf", "file2.pdf"})

if __name__ == "__main__":
    unittest.main()
