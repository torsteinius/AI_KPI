import os
import json
import csv
import re
import PyPDF2
import requests
from datetime import datetime
from urllib.parse import urlparse
from openai_model import OpenAIModel

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

def fetch_pdf_urls(company: str) -> list:  # This does not work at the current time
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

def process_report_urls(report_urls_csv: str, pdf_dir: str, read_files_csv: str) -> None:
    """
    Leser ReportURLs.csv (én URL per linje, uten header) og laster ned PDF-er
    som ikke allerede er behandlet (basert på filnavn i read_files_csv).
    """
    if not os.path.exists(report_urls_csv):
        print(f"Finner ikke {report_urls_csv}.")
        return
    
    # Les URL-er fra ReportURLs.csv
    with open(report_urls_csv, "r", newline="", encoding="utf-8") as csvfile:
        reader = csv.reader(csvfile)
        urls = [row[0].strip() for row in reader if row and row[0].strip() != ""]
    
    # Les allerede behandlede filer fra read_files_csv
    processed_files = set()
    if os.path.exists(read_files_csv):
        with open(read_files_csv, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row:
                    processed_files.add(row[0])
    
    for url in urls:
        filename = os.path.basename(urlparse(url).path)
        if filename in processed_files:
            print(f"Filen {filename} er allerede behandlet, hopper over.")
            continue
        success = download_pdf(url, pdf_dir, filename)
        if success:
            processed_files.add(filename)
    
    # Oppdater read_files_csv med alle behandlede filnavn
    os.makedirs(os.path.dirname(read_files_csv), exist_ok=True)
    with open(read_files_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        for f in sorted(processed_files):
            writer.writerow([f])

def run_analysis_for_company(company: str) -> None:
    """Kjører analyse for et gitt selskap basert på nedlastede PDF-er."""
    # Last inn instruksjoner for analyse
    instructions_file = "LLMText/json_instructions.txt"
    if os.path.exists(instructions_file):
        instructions = load_instructions(instructions_file)
    else:
        raise FileNotFoundError(f"Instruksjonsfilen '{instructions_file}' ble ikke funnet.")

    # Les og kombiner PDF-filer med prefiks som selskapets navn
    pdf_dir = "pdf"
    all_pdf_text = read_and_combine_pdfs(pdf_dir, prefix=company, read_files_csv="operation/read_files.csv")

    # Opprett modellen for analyse
    llm_model = OpenAIModel(
        instructions=instructions,
        model_name="gpt-4"
    )

    user_text = all_pdf_text

    # Lagre prompt til fil for oversikt
    os.makedirs("prompt", exist_ok=True)
    with open(os.path.join("prompt", f"{company}_prompt.txt"), "w", encoding="utf-8") as f:
        f.write(user_text)

    # Kjør modellen og hent rå respons
    raw_response = llm_model.run(user_text)

    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        data = {}

    # Lagre resultatet til fil
    os.makedirs("results", exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    result_filename = os.path.join("results", f"{company}_{date_str}.json")

    print("Resultat fra OpenAI (JSON):")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    with open(result_filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    # Definer selskapet for analysen
    #company = "YourCompanyName"  # Erstatt med ønsket selskapsnavn

    # 1) Hent URL-er fra ReportURLs.csv som ikke er behandlet tidligere
    process_report_urls("ReportURLs.csv", pdf_dir="pdf", read_files_csv="operation/read_files.csv") 
    

    # Run through PDFs that have not been read yet
    # 3) Kjør analyse basert på de nedlastede PDF-ene
    run_analysis_for_company(company)
