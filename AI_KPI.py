import os
import json
import re
from datetime import datetime
from urllib.parse import urlparse
from openai_model import OpenAIModel
from url_handler import URLHandler
from pdf_handler import PDFHandler

def load_instructions(filename: str) -> str:
    """Leser instruksjoner fra en .txt-fil."""
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

def fetch_pdf_urls(company: str) -> list:
    """
    Ber en modell om å finne URL-er til de offisielle PDF-rapportene og presentasjonene 
    for siste kvartal for et gitt selskap. Modellen skal kun returnere URL-ene, én per linje.
    """
    query = (
        f"Gi meg URL-ene til de offisielle PDF-rapportene og presentasjonene for siste kvartal for selskapet {company}. "
        "Skriv ut kun URL-ene, én per linje, uten noen ekstra tegn eller tekst."
    )
    instructions = "Svar _kun_ med URL-er, én per linje. Ikke inkluder noe annet."
    
    model = OpenAIModel(instructions=instructions)
    response = model.run(query)
    print("Svar fra modell for PDF URL-er:")
    print(response)
    
    urls = re.findall(r'(https?://[^\s]+)', response)
    
    json_result = {"urls": urls}
    print("Ekstrahert JSON:")
    print(json.dumps(json_result, indent=2))
    
    return urls

def download_pdfs_urls(company: str, report_urls: list, pdf_dir: str) -> None:
    """
    Leser listen med rapport-URL-er og laster ned PDF-ene til den spesifiserte mappen.
    """
    pdf_handler = PDFHandler(f"pdf/tickers/{company}")
    for url in report_urls:
        filename = os.path.basename(urlparse(url).path)
        dest_folder = os.path.join(pdf_dir, company)
        if os.path.exists(os.path.join(dest_folder, filename)):
            print(f"PDF '{filename}' allerede lastet ned.")
            continue
        pdf_handler.download_pdf(url, filename)

def run_analysis_for_company(company: str) -> None:
    """Kjører analyse for et gitt selskap basert på nedlastede PDF-er."""
    instructions_file = "LLMText/json_instructions.txt"
    if os.path.exists(instructions_file):
        instructions = load_instructions(instructions_file)
    else:
        raise FileNotFoundError(f"Instruksjonsfilen '{instructions_file}' ble ikke funnet.")


    # Read all PDFs for the company one by one
    pdf_handler = PDFHandler()
    pdf_dir = "pdf"
    all_pdf_text = pdf_handler.read_and_combine_pdfs(os.path.join(pdf_dir, company), prefix=company)


#    pdf_handler = PDFHandler()
#    pdf_dir = "pdf"
#    all_pdf_text = pdf_handler.read_and_combine_pdfs(os.path.join(pdf_dir, company), prefix=company)

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
    company = "Kitron"
    url_handler = URLHandler()
    kitron_urls = url_handler.get_urls_for_company(company)
    print(f"URL-er for {company}: {kitron_urls}")
    download_pdfs_urls(company, kitron_urls, pdf_dir="pdf")
    run_analysis_for_company(company)