import os
import json
import PyPDF2
from datetime import datetime
from openai_model import OpenAIModel

def extract_text_from_pdf(pdf_file: str) -> str:
    """
    Leser tekst fra en PDF-fil ved hjelp av PyPDF2.
    Returnerer all tekst som én streng.
    """
    text = ""
    with open(pdf_file, "rb") as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def read_and_combine_pdfs(pdf_dir: str, prefix: str) -> str:
    """
    Går gjennom alle PDF-filer i pdf_dir som starter med `prefix`,
    henter ut tekst, og setter dem sammen til én streng.
    """
    combined_text = ""
    for filename in os.listdir(pdf_dir):
        if filename.startswith(prefix) and filename.endswith(".pdf"):
            file_path = os.path.join(pdf_dir, filename)
            pdf_text = extract_text_from_pdf(file_path)
            combined_text += f"\n--- Innhold fra {filename} ---\n"
            combined_text += pdf_text
    return combined_text

def run_analysis_for_company(company: str) -> None:
    """
    Kjører analyse for et gitt selskap. 
    Resultatet lagres i en fil: {company}_{YYYYMMDD}.json.
    Selskap, år, kvartal (og de øvrige feltene) hentes automatisk av LLM fra PDF-innholdet.
    """

    # 1) Definer instruksjoner (systemprompt).
    instructions = """
    Du er en dyktig finansanalytiker som returnerer data i JSON-format.
    Pass på å holde deg til JSON-struktur, uten ekstra tegn eller forklaring.
    """

    # 2) Les PDF-filer i katalogen 'pdf' som starter med selskapets navn.
    pdf_dir = "pdf"
    all_pdf_text = read_and_combine_pdfs(pdf_dir, prefix=company)

    # 3) Opprett OpenAI-modellen.
    openai_model = OpenAIModel(
        instructions=instructions,
        model_name="gpt-4o-mini"  # Sett til riktig modellnavn / ID
    )

    # 4) Bygg user-prompt: vi ber spesifikt om at LLM returnerer feltene
    #    "company", "year", "quarter" samt de ulike nøkkeltallene.
    user_text = f"""
        Du får nå innholdet fra én eller flere PDF-filer (for eksempel {company}-rapporter),
        samlet nedenfor:
        {all_pdf_text}

        Vennligst analyser denne teksten og returner et JSON-objekt med disse nøkler:

        {{
            "company": ...,
            "year": ...,
            "quarter": ...,

            "revenue": ...,
            "operating_income": ...,
            "profit_before_tax": ...,
            "profit_after_tax": ...,
            "ebitda": ...,
            "eps": ...,
            "backlog": ...,
            "fremtid1år": ...,
            "fremtid2år": ...,
            "fremtid3år": ...
        }}

        ### Slik skal feltverdiene tolkes:
        - **company**: Selskapets navn (slik det fremgår av PDF-en, eller {company} om usikkert).
        - **year**: Hvilket år tallene gjelder for. 
        - **quarter**: Hvilket kvartal tallene gjelder for (f.eks. "Q4"). 
        
        - **revenue**: Totale inntekter (i MSEK). Hvis tallet kun finnes i annen valuta, 
                      konverter så godt det lar seg gjøre, eller sett `null` hvis usikkert.

        - **operating_income**: Driftsresultat (i MSEK).
        - **profit_before_tax**: Resultat før skatt (i MSEK).
        - **profit_after_tax**: Resultat etter skatt (i MSEK).
        - **ebitda**: EBITDA (i MSEK).
        - **eps**: Fortjeneste per aksje (i SEK).
        - **backlog**: Hvor stor andel av fremtidig omsetning som allerede er sikret (i MSEK).
        - **fremtid1år**: Forventet vekstpotensiale om 1 år, skala 1–5 (5 = høyest), `null` hvis ukjent.
        - **fremtid2år**: Forventet vekstpotensiale om 2 år, skala 1–5, `null` hvis ukjent.
        - **fremtid3år**: Forventet vekstpotensiale om 3 år, skala 1–5, `null` hvis ukjent.

        ### Krav:
        1. Returner **kun** JSON-objektet, uten ekstra forklaringer eller symboler før/etter.
        2. Hvis et nøkkeltall ikke finnes i teksten, sett verdien til `null`.
        3. Bruk **kun numeriske verdier** (flyt- eller heltall) for tallfeltene.
        4. Bruk punktum (".") som desimaltegn (ikke komma).
        5. Hvis du ikke kan finne 'company', 'year' eller 'quarter' i teksten, sett dem til null.

        **Her er teksten som skal analyseres** (PDF-innhold etc.):
        {all_pdf_text}
        """

    # 5) Kjør modellen med user-teksten.
    raw_response = openai_model.run(user_text)

    # 6) Prøv å parse svaret til et dict (JSON).
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        data = {}

    # 7) Velg filnavn som inkluderer company og dagens dato.
    date_str = datetime.now().strftime("%Y%m%d")
    filename = f"{company}_{date_str}.json"

    # 8) Skriv ut og lagre resultatet.
    print("Resultat fra OpenAI (JSON):")
    print(json.dumps(data, indent=2, ensure_ascii=False))
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    # Eksempel på kjøring for "sdiptech"
    run_analysis_for_company("sdiptech")
