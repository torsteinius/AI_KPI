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
    Resultatet lagres i en fil: results/{company}_{YYYYMMDD}.json.
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
    llm_model = OpenAIModel(
        instructions=instructions,
        model_name="gpt-4o-mini"  
    )

    # 4) Bygg user-prompt med utvidede KPI-felter:
    user_text = f"""
        Du får nå innholdet fra én eller flere PDF-filer (for eksempel {company}-rapporter),
        samlet nedenfor.

        Vennligst analyser denne teksten og returner et JSON-objekt med følgende nøkler:

        {{
            "company": ...,
            "year": ...,
            "quarter": ...,

            "revenue": ...,
            "gross_profit": ...,
            "gross_margin": ...,
            "operating_income": ...,
            "operating_margin": ...,
            "profit_before_tax": ...,
            "profit_after_tax": ...,
            "net_income": ...,
            "ebitda": ...,
            "ebitda_margin": ...,
            "eps": ...,

            "operating_cash_flow": ...,
            "free_cash_flow": ...,
            "debt_to_equity": ...,
            "roe": ...,
            "roa": ...,
            "dividend_yield": ...,

            "guidance": ...,
            "backlog": ...,
            "fremtid1år": ...,
            "fremtid2år": ...,
            "fremtid3år": ...
        }}

        ### Slik skal feltverdiene tolkes:
        - **company**: Selskapets navn (slik det fremgår av PDF-en, eller {company} om usikkert).
        - **year**: Hvilket år tallene gjelder.
        - **quarter**: Hvilket kvartal tallene gjelder (f.eks. "Q4").

        - **revenue**: Totale inntekter (f.eks. i MSEK).
        - **gross_profit**: Bruttofortjeneste (MSEK).
        - **gross_margin**: Bruttomargin i prosent (f.eks. 35.2 for 35,2%).
        - **operating_income**: Driftsresultat (MSEK).
        - **operating_margin**: Driftsmargin i prosent (f.eks. 12.5 for 12,5%).
        - **profit_before_tax**: Resultat før skatt (MSEK).
        - **profit_after_tax**: Resultat etter skatt (MSEK).
        - **net_income**: Kan være samme som "profit_after_tax" hvis PDF-en omtaler det slik.
        - **ebitda**: EBITDA (MSEK).
        - **ebitda_margin**: EBITDA-margin i prosent.
        - **eps**: Fortjeneste per aksje (SEK).

        - **operating_cash_flow**: Kontantstrøm fra drift (MSEK).
        - **free_cash_flow**: Fri kontantstrøm (MSEK).
        - **debt_to_equity**: Gjeldsgrad (numerisk verdi, f.eks. 1.2).
        - **roe**: Return on Equity, i prosent (f.eks. 15.3).
        - **roa**: Return on Assets, i prosent (f.eks. 8.1).
        - **dividend_yield**: Utbytteavkastning i prosent (f.eks. 4.5).

        - **guidance**: Tekstlig oppsummering av selskapets framtidige utsikter (hvis tilgjengelig).
        - **backlog**: Hvor stor ordre-/kontraktsreserve selskapet har (MSEK), om tilgjengelig.
        - **fremtid1år**, **fremtid2år**, **fremtid3år**: Forventet vekstpotensial (1–5), eller null hvis ukjent.

        ### Krav:
        1. Returner **kun** JSON-objektet, uten ekstra forklaringer eller symboler før/etter.
        2. Hvis et nøkkeltall ikke finnes i teksten, sett verdien til `null`.
        3. Bruk **kun numeriske verdier** (flyt- eller heltall) for tallfeltene, unntatt 'guidance' som kan være tekst.
        4. Bruk punktum (".") som desimaltegn (ikke komma).
        5. Hvis du ikke kan finne 'company', 'year' eller 'quarter' i teksten, sett dem til null.

        **Her er teksten som skal analyseres**:
        {all_pdf_text}
        """
    # 4) Lagre user-prompt til fil for inspeksjon under katalogen "prompt"
    if not os.path.exists("prompt"):
        os.makedirs("prompt")  # Opprett katalogen hvis den ikke finnes 

    with open(os.path.join("prompt", f"{company}_prompt.txt"), "w", encoding="utf-8") as f:
        f.write(user_text)

    # 5) Kjør modellen med user-teksten.
    raw_response = llm_model.run(user_text)

    # 6) Prøv å parse svaret til et dict (JSON).
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        data = {}

    # 7) Lag filnavn og sti til katalogen "results".
    date_str = datetime.now().strftime("%Y%m%d")
    if not os.path.exists("results"):
        os.makedirs("results")  # Opprett katalogen hvis den ikke finnes

    filename = os.path.join("results", f"{company}_{date_str}.json")

    # 8) Skriv ut og lagre resultatet.
    print("Resultat fra OpenAI (JSON):")
    print(json.dumps(data, indent=2, ensure_ascii=False))

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    run_analysis_for_company("Reach-Subsea")
