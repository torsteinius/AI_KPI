import os
import json
import csv
import re
from datetime import datetime
from urllib.parse import urlparse
from openai_model import OpenAIModel

class URLHandler:
    def __init__(self, url_data="operation/ReportURLs.csv"):
        """
        url_data: CSV-fil med kolonnene "company" og "url"
        """
        self.url_dict = {}
        self.read_urls(url_data)

    def read_urls(self, url_csv="operation/ReportURLs.csv"):
        """Leser URL-er fra en CSV-fil med følgende format:
        company;url
        URL-ene lagres i en ordbok med selskapsnavn som nøkkel.
        """
        if not os.path.exists(url_csv):
            raise FileNotFoundError(f"URL-filen '{url_csv}' ble ikke funnet.")
        
        self.url_dict = {}
        with open(url_csv, "r", newline="", encoding="utf-8") as csvfile:
            # Setter delimiter til semikolon
            reader = csv.DictReader(csvfile, delimiter=";")
            for row in reader:
                company = row.get("company", "").strip()
                url = row.get("url", "").strip()
                if company and url:
                    if company not in self.url_dict:
                        self.url_dict[company] = set()  # Bruker set for å unngå duplikater
                    self.url_dict[company].add(url)
        
        # Konverterer sett til lister
        self.url_dict = {company: list(urls) for company, urls in self.url_dict.items()}
        print("Read URL Data:", self.url_dict)

    def get_urls_for_company(self, company):
        """Returnerer URL-er for et spesifikt selskap."""
        return self.url_dict.get(company, [])

    def get_current_quarter(self):
        """Bestemmer nåværende kvartal og år."""
        month = datetime.now().month
        year = datetime.now().year
        quarter = (month - 1) // 3 + 1
        return quarter, year

    def parse_urls(self, url_data):
        """Organiserer URL-er etter selskap fra en liste av (company, url)-tupler."""
        for company, url in url_data:
            if company not in self.url_dict:
                self.url_dict[company] = []
            self.url_dict[company].append(url)
        print("Parsed URL Data:", self.url_dict)

    def load_instructions(self, filename: str) -> str:
        """Leser instruksjoner fra en .txt-fil."""
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()

    def guess_next_urls(self, company):
        """Genererer mulige URL-er for nåværende kvartal ved hjelp av LLM."""
        guessed_urls = {}
        model = OpenAIModel(instructions="Return only URLs, one per line.")
        instructions_file = "LLMText/predict_url_instructions.txt"
        if os.path.exists(instructions_file):
            instructions = self.load_instructions(instructions_file)
        else:
            raise FileNotFoundError(f"Instruksjonsfilen '{instructions_file}' ble ikke funnet.")
                    
        response = model.run(instructions)
        print(f"Response from model for {company}:\n{response}")
        guessed_urls[company] = re.findall(r'(https?://[^\s]+)', response)
        return guessed_urls

if __name__ == "__main__":
    # Eksempelbruk:
    url_handler = URLHandler()
    company = "Kitron"
    urls = url_handler.get_urls_for_company(company)
    print(f"URLs for {company}: {urls}")
