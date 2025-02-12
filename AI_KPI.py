import os
import json
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

def read_and_combine_pdfs(pdf_dir: str, prefix: str) -> str:
    """ Leser og kombinerer tekst fra alle PDF-er med gitt prefiks. """
    combined_text = ""
    for filename in os.listdir(pdf_dir):
        if filename.startswith(prefix) and filename.endswith(".pdf"):
            file_path = os.path.join(pdf_dir, filename)
            pdf_text = extract_text_from_pdf(file_path)
            combined_text += f"\n--- Innhold fra {filename} ---\n"
            combined_text += pdf_text
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


    # 2) Les PDF-filer i katalogen 'pdf' som starter med selskapets navn.
    pdf_dir = "pdf"
    all_pdf_text = read_and_combine_pdfs(pdf_dir, prefix=company)

    # 3) Opprett OpenAI-modellen.
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
    run_analysis_for_company("Nekkar")
