import openai
import json

# Sett din OpenAI API-nøkkel her
openai.api_key = "SK-DIN-API-NØKKEL-HER"

def extract_financials_from_report(report_text: str, presentation_text: str) -> dict:
    """
    Sender kvartalsrapport-tekst til en LLM for å hente ut nøkkeltall.
    Returnerer et JSON-lignende Python-dikt.
    """

    # Bygg prompten
    prompt = f"""
        Du får en kvartalsrapport, og din oppgave er å identifisere spesifikke økonomiske nøkkeltall og presentere dem som et JSON-objekt med følgende struktur:

        {{
        "revenue": REVENUE,  # Totale inntekter (MSEK)
        "operating_income": OPERATING_INCOME,  # Driftsresultat (MSEK)
        "profit_before_tax": PROFIT_BEFORE_TAX,  # Resultat før skatt (MSEK)
        "profit_after_tax": PROFIT_AFTER_TAX,  # Resultat etter skatt (MSEK)
        "ebitda": EBITDA,  # EBITDA (MSEK)
        "eps": EPS,  # Fortjeneste per aksje (SEK)
        "backlog": BACKLOG,  # Hvor stor andel av fremtidig omsetning som er sikret (MSEK)
        "fremtid1år": POTENSIALE_1ÅR,  # Forventet vekstpotensiale om 1 år (skala 1-5)
        "fremtid2år": POTENSIALE_2ÅR,  # Forventet vekstpotensiale om 2 år (skala 1-5)
        "fremtid3år": POTENSIALE_3ÅR  # Forventet vekstpotensiale om 3 år (skala 1-5)
        }}

        ### Krav:
        - Returner **kun** JSON-objektet, uten ekstra tekst, forklaringer eller symboler.
        - Hvis et nøkkeltall ikke finnes i teksten, sett verdien til `null`.
        - Bruk **kun numeriske verdier** (flyttall).
        - Bruk **punktum** (`.`) som desimaltegn.

        Her er teksten som skal analyseres:
        \"\"\"{report_text}\"\"\"
        \"\"\"{presentation_text}\"\"\"
    """

    
    # Kall OpenAI ChatCompletion (GPT 3.5 eller 4). 
    # Velg den modellen du har tilgang til (for eksempel "gpt-3.5-turbo").
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": "Du er en dyktig finansanalytiker som returnerer data i JSON-format."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.0  # Sett til 0 for minst mulig 'kreativ' respons
    )

    # Selve svaret fra API-et
    raw_response = response["choices"][0]["message"]["content"].strip()
    
    # Forsøk å parse JSON
    try:
        data = json.loads(raw_response)
    except json.JSONDecodeError:
        # Hvis det skulle feile, kan vi for eksempel returnere tom dict
        data = {}
    
    return data


def main():
    # Eksempel på en tekst vi vil analysere
    quarterly_report_text = """
Rapport for Q4 2024:
- Omsetningen i kvartalet var 14,5 millioner kroner, en økning på 5% fra i fjor.
- Driftsresultatet ble 2 millioner kroner.
- Resultat før skatt endte på 1,5 millioner kroner.
- Selskapet opplyser at EBITDA var 2,5 millioner kroner.
- EPS var 0,12 kroner per aksje.
    """
    quarterly_presentation_text = """
Bla bla bla
    """

    # 1. Kall funksjonen som henter ut nøkkeltall via OpenAI
    extracted_data = extract_financials_from_report(quarterly_report_text, quarterly_presentation_text)

    # 2. Skriv resultatet til en JSON-fil
    output_filename = "extracted_data.json"
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(extracted_data, f, ensure_ascii=False, indent=2)

    print(f"Nøkkeltall lagret i '{output_filename}':")
    print(json.dumps(extracted_data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
