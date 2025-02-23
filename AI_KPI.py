import os
import json
import csv
import re
import PyPDF2
import requests
from datetime import datetime
from urllib.parse import urlparse
from openai_model import OpenAIModel
from url_handler import URLHandler

def extract_text_from_pdf(pdf_file: str) -> str:
    """Leser tekst fra en PDF-fil ved hjelp av PyPDF2."""
    text = ""
    with open(pdf_file, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def read_and_combine_pdfs(pdf_dir: str, prefix: str, read_files_csv: str = "operation/read_files.csv") -> str:
    """
    Leser og kombinerer tekst fra alle PDF-er med gitt prefiks.
    Logger filnavn i read_files_csv for å unngå duplikatlesing.
    """
    os.makedirs(os.path.dirname(read_files_csv), exist_ok=True)

    # Les inn allerede behandlede filer fra CSV
    read_files = set()
    if os.path.exists(read_files_csv):
        with open(read_files_csv, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row:
                    read_files.add(row[0])

    # Finn alle relevante PDF-filer
    all_files = [f for f in os.listdir(pdf_dir) if f.startswith(prefix) and f.endswith(".pdf")]

    combined_text = ""
    newly_read_files = []

    for filename in all_files:
        if filename not in read_files:
            file_path = os.path.join(pdf_dir, filename)
            pdf_text = extract_text_from_pdf(file_path)
            combined_text += f"\n--- Innhold fra {filename} ---\n" + pdf_text
            newly_read_files.append(filename)
            read_files.add(filename)

    # Lagre oppdatert liste over leste filer
    with open(read_files_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        for f in sorted(read_files):
            writer.writerow([f])

    already_read_files = [f for f in all_files if f not in newly_read_files]
    if already_read_files:
        print("Følgende filer ble ikke lest (allerede behandlet tidligere):")
        for f in already_read_files:
            print(f)

    return combined_text

def load_instructions(filename: str) -> str:
    """Leser instruksjoner fra en .txt-fil."""
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

def fetch_pdf_urls(company: str) -> list:  # Denne fungerer ikke for øyeblikket
    """
    Ber en modell om å finne URL-er til de offisielle PDF-rapportene og presentasjonene 
    for siste kvartal for et gitt selskap. Modellen skal kun returnere URL-ene, én per linje.
    Resultatet konverteres til JSON ved hjelp av regex.
    """
    query = (
        f"Gi meg URL-ene til de offisielle PDF-rapportene og presentasjonene for siste kvartal for selskapet {company}. "
        "Skriv ut kun URL-ene, én per linje, uten noen ekstra tegn eller tekst."
    )
    instructions = "Svar _kun_ med URL-er, én per linje. Ikke inkluder noe annet."
    
    # Bruk en modell (f.eks. GPT-4) som er i stand til å finne URL-er
    model = OpenAIModel(
        instructions=instructions
    )
    response = model.run(query)
    print("Svar fra modell for PDF URL-er:")
    print(response)
    
    # Bruk regex for å hente ut alle URL-er fra modellens svar
    urls = re.findall(r'(https?://[^\s]+)', response)
    
    # Konverter til en JSON-struktur (kun for logging/validering)
    json_result = {"urls": urls}
    print("Ekstrahert JSON:")
    print(json.dumps(json_result, indent=2))
    
    return urls

def download_pdf(url: str, dest_folder: str, filename: str) -> bool: 
    """
    Laster ned en PDF fra en gitt URL og lagrer den i dest_folder med angitt filename.
    Returnerer True hvis nedlasting var vellykket, ellers False.
    """
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

def download_pdfs_urls(company: str, report_urls: list, pdf_dir: str) -> None:
    """
    Leser listen med rapport-URL-er og laster ned PDF-ene til den spesifiserte mappen.
    """
    for url in report_urls:
        filename = os.path.basename(urlparse(url).path)
        dest_folder = os.path.join(pdf_dir, company)
        if os.path.exists(os.path.join(dest_folder, filename)):
            print(f"PDF '{filename}' allerede lastet ned.")
            continue
        download_pdf(url, dest_folder, filename)

def run_analysis_for_company(company: str) -> None:
    """Kjører analyse for et gitt selskap basert på nedlastede PDF-er."""
    instructions_file = "LLMText/json_instructions.txt"
    if os.path.exists(instructions_file):
        instructions = load_instructions(instructions_file)
    else:
        raise FileNotFoundError(f"Instruksjonsfilen '{instructions_file}' ble ikke funnet.")

    pdf_dir = "pdf"
    all_pdf_text = read_and_combine_pdfs(os.path.join(pdf_dir, company), prefix=company, read_files_csv="operation/read_files.csv")

    llm_model = OpenAIModel(
        instructions=instructions,
        model_name="gpt-4"
    )

    user_text = all_pdf_text

    os.makedirs("prompt", exist_ok=True)
    with open(os.path.join("prompt", f"{company}_prompt.txt"), "w", encoding="utf-8") as f:
        f.write(user_text)

    raw_response = llm_model.run(user_text)

    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        data = {}

    os.makedirs("results", exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    result_filename = os.path.join("results", f"{company}_{date_str}.json")

    print("Resultat fra OpenAI (JSON):")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    with open(result_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Definer selskapet for analysen
    company = "Kitron"  # Erstatt med ønsket selskapsnavn

    # 1) Hent URL-er for selskapet
    url_handler = URLHandler()
    kitron_urls = url_handler.get_urls_for_company(company)
    print(f"URL-er for {company}: {kitron_urls}")

    # 2) Last ned PDF-er fra URL-ene
    download_pdfs_urls(company, kitron_urls, pdf_dir="pdf")

    # 3) Kjør analyse basert på de nedlastede PDF-ene
    run_analysis_for_company(company)
