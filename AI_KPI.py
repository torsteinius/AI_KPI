import os
import json
import PyPDF2
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

def read_and_combine_pdfs(pdf_dir: str, prefix: str = "sdiptech") -> str:
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

def main():
    # 1) Definer instruksjoner (systemprompt) 
    #    Dette sendes til konstruktøren i OpenAIModel.
    instructions = """
    Du er en dyktig finansanalytiker som returnerer data i JSON-format.
    Pass på å holde deg til JSON-struktur, uten ekstra tegn eller forklaring.
    """

    # 2) Les og sammenstill innholdet fra PDF-filer i katalogen "./pdf"
    #    som starter med "sdiptech"
    pdf_dir = "pdf"
    all_pdf_text = read_and_combine_pdfs(pdf_dir, prefix="sdiptech")

    # 3) Opprett OpenAI-modellen (GPT 3.5)
    #    (API-nøkkelen kan du legge inn her eller håndtere via miljøvariabler)
    openai_model = OpenAIModel(
        instructions=instructions,
        model_name="gpt-4o-mini"  
    )

    # 4) Bygg en user-prompt / brukertekst som forteller hva du ønsker.
    #    Her kan du legge inn mer spesifikk instruks om hvilke nøkler du vil ha i JSON.

    user_text = f"""
        Du får nå innholdet fra én eller flere PDF-filer (for eksempel Sdiptech-rapporter), samlet nedenfor:
        {all_pdf_text}

        Vennligst analyser denne teksten og returner et JSON-objekt med følgende nøkler og tilhørende verdier:

        {{
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

        - **revenue**: Totale inntekter (i MSEK). 
        - Hvis tallet kun finnes i andre valuta, konverter så godt det lar seg gjøre, eller sett `null` hvis usikkert.

        - **operating_income**: Driftsresultat (i MSEK).

        - **profit_before_tax**: Resultat før skatt (i MSEK).

        - **profit_after_tax**: Resultat etter skatt (i MSEK).

        - **ebitda**: EBITDA (i MSEK).

        - **eps**: Fortjeneste per aksje (i SEK).

        - **backlog**: Hvor stor andel av fremtidig omsetning som allerede er sikret (i MSEK).

        - **fremtid1år**: Forventet vekstpotensiale om 1 år, på en skala fra 1 til 5 (hvor 5 er høyest). 
        - Hvis dette ikke kan vurderes ut fra teksten, bruk `null`.

        - **fremtid2år**: Forventet vekstpotensiale om 2 år, skala 1–5, `null` hvis ukjent.

        - **fremtid3år**: Forventet vekstpotensiale om 3 år, skala 1–5, `null` hvis ukjent.

        ### Krav:
        1. Returner **kun** JSON-objektet, uten ekstra forklaringer, symboler eller tekst før/etter.  
        2. Hvis et nøkkeltall ikke finnes i teksten, sett verdien til `null`.  
        3. Bruk **kun numeriske verdier** (flyt- eller heltall).  
        4. Bruk punktum (".") som desimaltegn (ikke komma).  

        **Her er teksten som skal analyseres** (PDF-innhold etc.):
        {all_pdf_text}
        """


    # 5) Kjør modellen med user-teksten
    raw_response = openai_model.run(user_text)

    # 6) Prøv å parse svaret til et dict (JSON)
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        data = {}

    # 7) Skriv ut (eller lagre) resultatet
    print("Resultat fra OpenAI (JSON):")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    # 8) Lagre resultatet til en fil
    with open("resultat.json", "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()




