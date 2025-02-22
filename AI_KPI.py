import os
import json
import csv
import PyPDF2
from datetime import datetime
from openai_model import OpenAIModel

def extract_text_from_pdf(pdf_file: str) -> str:
    """ Leser tekst fra en PDF-fil ved hjelp av PyPDF2. """
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
    Skriver også ut filer som allerede er lest, for oversikt.
    """

    # Sørg for at katalogen 'operation' finnes, hvis ikke opprettes den.
    os.makedirs(os.path.dirname(read_files_csv), exist_ok=True)

    # 1) Les inn allerede behandlede filer fra CSV
    read_files = set()
    if os.path.exists(read_files_csv):
        with open(read_files_csv, "r", newline="", encoding="utf-8") as csvfile:
            reader = csv.reader(csvfile)
            for row in reader:
                if row:  # Hopp over tomme rader
                    read_files.add(row[0])

    # 2) Finn alle relevante PDF-filer
    all_files = [f for f in os.listdir(pdf_dir) if f.startswith(prefix) and f.endswith(".pdf")]

    combined_text = ""
    newly_read_files = []

    # 3) Les filer som ikke er lest tidligere, og bygg opp combined_text
    for filename in all_files:
        if filename not in read_files:
            file_path = os.path.join(pdf_dir, filename)
            pdf_text = extract_text_from_pdf(file_path)
            combined_text += f"\n--- Innhold fra {filename} ---\n"
            combined_text += pdf_text

            # Oppdater read_files med ny fil
            newly_read_files.append(filename)
            read_files.add(filename)

    # 4) Lagre hele settet med leste filer til CSV på nytt
    with open(read_files_csv, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        for f in sorted(read_files):
            writer.writerow([f])

    # 5) Identifiser filer som ikke ble lest (fordi de var lest før)
    already_read_files = [f for f in all_files if f not in newly_read_files]
    if already_read_files:
        print("Følgende filer ble ikke lest (allerede behandlet tidligere):")
        for f in already_read_files:
            print(f)

    return combined_text

def load_instructions(filename: str) -> str:
    """ Leser instruksjoner fra en .txt-fil. """
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()
    
def run_analysis_for_company(company: str) -> None:
    """ Kjører analyse for et gitt selskap. """

    # 1) Les instruksjoner fra fil
    instructions_file = "json_instructions.txt"
    if os.path.exists(instructions_file):
        instructions = load_instructions(instructions_file)
    else:
        raise FileNotFoundError(f"Instruksjonsfilen '{instructions_file}' ble ikke funnet.")

    # 2) Les og kombiner PDF-filer i katalogen 'pdf' som starter med selskapets navn
    pdf_dir = "pdf"
    all_pdf_text = read_and_combine_pdfs(pdf_dir, prefix=company, read_files_csv="operation/read_files.csv")

    # 3) Opprett OpenAI-modellen
    llm_model = OpenAIModel(
        instructions=instructions,
        model_name="gpt-4o-mini"
    )

    # 4) Bygg user-prompt
    user_text = all_pdf_text

    # 5) Lagre user-prompt til fil
    os.makedirs("prompt", exist_ok=True)
    with open(os.path.join("prompt", f"{company}_prompt.txt"), "w", encoding="utf-8") as f:
        f.write(user_text)

    # 6) Kjør modellen
    raw_response = llm_model.run(user_text)

    # 7) Prøv å parse svaret til JSON
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        data = {}

    # 8) Lagre resultatet
    os.makedirs("results", exist_ok=True)
    date_str = datetime.now().strftime("%Y%m%d")
    filename = os.path.join("results", f"{company}_{date_str}.json")

    print("Resultat fra OpenAI (JSON):")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    run_analysis_for_company("GRANGES")
