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
        Initialiserer URLHandler med en standard CSV-fil som inneholder URL-data.
        
        Parameter:
        - url_data: Stien til CSV-filen som forventes å ha kolonnene "company" og "url".
        
        Oppgave:
        - Initialiserer en tom ordbok for URL-er.
        - Leser og lagrer URL-data fra den spesifiserte CSV-filen.
        """
        self.url_dict = {}  # Ordbok for å lagre URL-er knyttet til hvert selskap.
        self.read_urls(url_data)  # Kaller metoden for å lese URL-er fra filen.

    def read_urls(self, url_csv="operation/ReportURLs.csv"):
        """
        Leser URL-er fra en CSV-fil og organiserer dem i en dictionary.
        
        CSV-format:
        - Forventet format: "company;url" med semikolon som feltseparator.
        
        Prosess:
        1. Sjekker om filen finnes; hvis ikke, hever en FileNotFoundError.
        2. Åpner filen med UTF-8-koding for å støtte spesialtegn.
        3. Bruker csv.DictReader for å lese hver rad som en dictionary.
        4. Henter ut og striper "company" og "url" fra hver rad.
        5. Bruker et sett for å lagre URL-er for hvert selskap for å unngå duplikater.
        6. Konverterer settene til lister for ensartet struktur i ordboken.
        7. Skriver ut den leste URL-dataen for å verifisere innlesningen.
        """
        if not os.path.exists(url_csv):
            raise FileNotFoundError(f"URL-filen '{url_csv}' ble ikke funnet.")
        
        self.url_dict = {}
        with open(url_csv, "r", newline="", encoding="utf-8") as csvfile:
            # Setter semikolon som feltseparator siden CSV-filen bruker dette som delimiter
            reader = csv.DictReader(csvfile, delimiter=";")
            for row in reader:
                # Henter selskapets navn og URL, og fjerner eventuelle overflødige mellomrom
                company = row.get("company", "").strip()
                url = row.get("url", "").strip()
                # Legger bare til raden dersom både selskap og URL er oppgitt
                if company and url:
                    # Initialiserer et nytt sett for selskapet dersom det ikke allerede eksisterer
                    if company not in self.url_dict:
                        self.url_dict[company] = set()  # Set brukes for å unngå duplikater
                    self.url_dict[company].add(url)
        
        # Konverterer hvert sett med URL-er til en liste for enklere videre bruk
        self.url_dict = {company: list(urls) for company, urls in self.url_dict.items()}
        print("Read URL Data:", self.url_dict)

    def get_urls_for_company(self, company):
        """
        Henter URL-er for et spesifikt selskap.
        
        Parameter:
        - company: Navnet på selskapet man ønsker URL-er for.
        
        Returnerer:
        - En liste med URL-er. Hvis selskapet ikke finnes i ordboken, returneres en tom liste.
        """
        return self.url_dict.get(company, [])

    def get_current_quarter(self):
        """
        Beregner og returnerer det nåværende kvartalet og året.
        
        Prosess:
        1. Henter den nåværende måneden og året via datetime.now().
        2. Beregner kvartalet med formelen: (måned - 1) // 3 + 1.
        
        Returnerer:
        - Et tuple bestående av (kvartal, år).
        """
        month = datetime.now().month
        year = datetime.now().year
        quarter = (month - 1) // 3 + 1
        return quarter, year

    def parse_urls(self, url_data):
        """
        Organiserer en liste av (company, url)-tupler og oppdaterer URL-dictionaryen.
        
        Parameter:
        - url_data: En liste med tuples, der hvert tuple består av (company, url).
        
        Prosess:
        1. Itererer gjennom hvert tuple i listen.
        2. Hvis selskapet ikke finnes i ordboken, opprettes en ny liste for det.
        3. Legger URL-en til selskapets liste.
        4. Skriver ut den oppdaterte ordboken for å bekrefte parsing.
        """
        for company, url in url_data:
            if company not in self.url_dict:
                self.url_dict[company] = []
            self.url_dict[company].append(url)
        print("Parsed URL Data:", self.url_dict)

    def load_instructions(self, filename: str) -> str:
        """
        Leser instruksjoner fra en tekstfil og returnerer innholdet.
        
        Parameter:
        - filename: Filstien til .txt-filen med instruksjoner.
        
        Returnerer:
        - En streng som inneholder filens innhold.
        """
        with open(filename, "r", encoding="utf-8") as f:
            return f.read()

    def guess_next_urls(self, company):
        """
        Genererer mulige URL-er for et gitt selskap ved hjelp av en stor språkmodell (LLM).
        
        Prosess:
        1. Oppretter en tom dictionary for gjetninger.
        2. Initialiserer OpenAIModel med en instruksjon som ber om å returnere kun URL-er, en per linje.
        3. Sjekker om en fil med instruksjoner for prediksjon eksisterer.
           - Hvis filen finnes, lastes innholdet.
           - Hvis ikke, heves en FileNotFoundError.
        4. Kjører modellen med de lastede instruksjonene for å generere en respons.
        5. Skriver ut responsen for logging og feilsøking.
        6. Bruker regex for å identifisere og trekke ut alle URL-er fra modellens respons.
        7. Returnerer en dictionary med selskapet som nøkkel og listen med URL-er som verdi.
        
        Parameter:
        - company: Navnet på selskapet for hvilket URL-gjetninger skal genereres.
        
        Returnerer:
        - Dictionary med selskapets navn som nøkkel og en liste over URL-er som verdi.
        """
        guessed_urls = {}
        # Oppretter en instans av OpenAIModel med en spesifikk instruksjon for output-format
        model = OpenAIModel(instructions="Return only URLs, one per line.")
        instructions_file = "LLMText/predict_url_instructions.txt"
        if os.path.exists(instructions_file):
            # Leser inn instruksjonstekst fra filen
            instructions = self.load_instructions(instructions_file)
        else:
            raise FileNotFoundError(f"Instruksjonsfilen '{instructions_file}' ble ikke funnet.")
                    
        # Kjører modellen med de innlastede instruksjonene og mottar responsen
        response = model.run(instructions)
        print(f"Response from model for {company}:\n{response}")
        # Bruker regex for å finne alle URL-er i responsen (matcher http:// eller https:// etterfulgt av ikke-whitespace tegn)
        guessed_urls[company] = re.findall(r'(https?://[^\s]+)', response)
        return guessed_urls

if __name__ == "__main__":
    # Hovedprogram: Demonstrasjon av hvordan URLHandler-klassen kan benyttes
    url_handler = URLHandler()  # Oppretter en instans av URLHandler som automatisk leser inn URL-data fra standardfilen
    company = "Kitron"  # Eksempel på et selskap
    urls = url_handler.get_urls_for_company(company)  # Henter URL-er for det angitte selskapet
    print(f"URLs for {company}: {urls}")  # Skriver ut URL-ene for selskapet
