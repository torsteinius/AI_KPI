import os
import json
import csv
import re
from datetime import datetime
from urllib.parse import urlparse
from openai_model import OpenAIModel

class QuarterlyURLGuesser:
    def __init__(self, url_data):
        """
        url_data: List of tuples (company, url)
        """
        self.url_dict = {}
        self.current_quarter, self.current_year = self.get_current_quarter()
        self.parse_urls(url_data)

    def get_current_quarter(self):
        """Determine the current quarter and year."""
        month = datetime.now().month
        year = datetime.now().year
        quarter = (month - 1) // 3 + 1
        return quarter, year

    def parse_urls(self, url_data):
        """Organize URLs by company."""
        for company, url in url_data:
            if company not in self.url_dict:
                self.url_dict[company] = []
            self.url_dict[company].append(url)
        print("Parsed URL Data:", self.url_dict)

    def load_instructions(filename: str) -> str:
        """Leser instruksjoner fra en .txt-fil."""
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()

    def guess_next_urls(self):
        """Generate possible URLs for the current quarter using LLM."""
        guessed_urls = {}
        model = OpenAIModel(instructions="Return only URLs, one per line.")

        
        # Last inn instruksjoner 
        instructions_file = "LLMText/predict_url_instructions.txt"
        if os.path.exists(instructions_file):
            instructions = self.load_instructions(instructions_file)
        else:
            raise FileNotFoundError(f"Instruksjonsfilen '{instructions_file}' ble ikke funnet.")
                    
        response = model.run(instructions)
        print(f"Response from model for {company}:\n{response}")
        guessed_urls[company] = re.findall(r'(https?://[^\s]+)', response)
        
        return guessed_urls

# Example usage:
data = [
    ("Kitron", "https://kitron.com/storage/files/Quarterly%20reports/Kitron%202024%20Q4%20Presentation.pdf"),
    ("Kitron", "https://kitron.com/storage/files/Quarterly%20reports/Kitron%202024%20Q4%20Report.pdf"),
    ("Kitron", "https://kitron.com/storage/files/Quarterly%20reports/Kitron%202024%20Q3%20Presentation.pdf"),
    ("Nekkar", "https://kommunikasjon.ntb.no/ir-files/17847326/18420756/5619/Nekkar%20ASA_Q4%202024_presentation.pdf"),
]

url_guesser = QuarterlyURLGuesser(data)
guessed_urls = url_guesser.guess_next_urls()
for company, urls in guessed_urls.items():
    print(f"{company}:")
    for url in urls:
        print(f"  {url}")