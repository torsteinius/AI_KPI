import os
import json
from datetime import datetime
from urllib.parse import urlparse
from openai_model import OpenAIModel
from url_handler import URLHandler
from pdf_handler import PDFHandler


def load_instructions(filename: str) -> str:
    """Leser instruksjoner fra en .txt-fil."""
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()

def run_analysis_for_company(company: str) -> None:
    """
    Kjører analyse på _hver_ PDF for 'company', én etter én.  
    Oppretter et JSON-resultat per PDF, med filnavn basert på PDF-ens navn.
    """
    instructions_file = "LLMText/json_instructions.txt"
    if not os.path.exists(instructions_file):
        raise FileNotFoundError(f"Instruksjonsfilen '{instructions_file}' ble ikke funnet.")

    instructions = load_instructions(instructions_file)

    # Lag PDFHandler for dette selskapet
    pdf_handler = PDFHandler(company)

    # 1) Hent liste over alle PDF-er i mappen, inkludert en processed-flag
    if not os.path.isdir(pdf_handler._PDFHandler__ticker_path):
        print(f"Ingen mappe funnet for selskapet '{company}'. Avbryter analyse.")
        return

    pdf_list = pdf_handler.list_downloaded_pdfs()
    if not pdf_list:
        print(f"Ingen PDF-filer funnet for selskapet '{company}'. Avbryter.")
        return

    # 2) Filtrer til kun de som IKKE er prosessert (processed=False)
    unread_list = [p for p in pdf_list if not p["processed"]]
    if not unread_list and False:
        print(f"Ingen nye (uleste) PDF-filer for '{company}'.")
        return

    # 3) Loop over hver ulest PDF
    for pdf_info in unread_list:
        pdf_filename = pdf_info["filename"]
        pdf_path = pdf_info["full_path"]

        print(f"\nBehandler PDF: {pdf_filename}")
        pdf_text = pdf_handler.extract_text_from_pdf(pdf_path)

        if not pdf_text.strip():
            print(f"PDF '{pdf_filename}' ser ut til å være tom. Hoppes over.")
            # Merk filen som lest i CSV, så vi ikke kjører den på nytt
            read_files = pdf_handler._get_read_files()
            read_files.add(pdf_filename)
            pdf_handler._update_read_files(read_files)
            continue

        # Kjør LLM med instruksjoner + PDF-tekst
        llm_model = OpenAIModel(
            instructions=instructions,
            model_name="gpt-4"
        )
        raw_response = llm_model.run(pdf_text)

        # Forsøk å parse JSON fra respons
        try:
            data = json.loads(raw_response)
        except json.JSONDecodeError:
            print("Kunne ikke parse JSON fra LLM-respons. Lagre rå respons i en fil.")
            data = {}
            # (Valgfritt) lagre den rå responsen
            os.makedirs("results", exist_ok=True)
            with open(os.path.join("results", f"{pdf_filename}_raw.txt"), "w", encoding="utf-8") as rf:
                rf.write(raw_response)

        # 4) Lagre JSON-resultat (ett per PDF)
        os.makedirs("results", exist_ok=True)
        date_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = os.path.splitext(pdf_filename)[0] + f"_{date_str}.json"
        json_path = os.path.join("results", json_filename)

        print("Resultat fra OpenAI (JSON):")
        print(json.dumps(data, indent=2, ensure_ascii=False))

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        # 5) Oppdater CSV med at vi har lest denne PDF-en
        read_files = pdf_handler._get_read_files()
        read_files.add(pdf_filename)
        pdf_handler._update_read_files(read_files)

    print("Alle uleste PDF-filer er nå behandlet.")



def download_pdfs_urls(company: str, report_urls: list) -> None:
    pdf_handler = PDFHandler(company)
    for url in report_urls:
        filename = os.path.basename(urlparse(url).path)
        if pdf_handler.is_pdf_downloaded(filename):
            print(f"PDF '{filename}' allerede lastet ned.")
        else:
            pdf_handler.download_pdf(url, filename)



if __name__ == "__main__":
    # Eksempel: Kjør for "Kitron"
    company = "Kitron"

    # 1) Hent URL-er for "Kitron"
    url_handler = URLHandler()
    kitron_urls = url_handler.get_urls_for_company(company)
    print(f"URL-er for {company}: {kitron_urls}")

    # 2) Last ned PDF-ene (om nødvendig)
    download_pdfs_urls(company, kitron_urls)

    # 3) Kjør analyse for hver ulest PDF individuelt
    run_analysis_for_company(company)
