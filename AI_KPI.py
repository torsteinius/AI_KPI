# main.py
import json
from openai_model import OpenAIModel
from deepseek_model import DeepSeekModel

def main():
    # Felles instruksjoner (systemprompt) - kun et eksempel
    instructions = """
    Du er en dyktig finansanalytiker som returnerer data i JSON-format. 
    Pass på å holde deg til JSON-struktur, ingen ekstra tegn.
    """

    # Eksempeltekst (brukerprompt / "text" som LLM-en skal analysere)
    # Du kan lage en større prompt her om du vil, 
    # men ofte er det lurt å sende inn kun det som er relevant å analysere.
    user_text = """
    Identifiser følgende økonomiske nøkkeltall i denne kvartalsrapporten og returner dem som JSON:
    - Omsetning (revenue)
    - Driftsresultat (operating_income)
    - Resultat før skatt (profit_before_tax)
    - ...
    
    Rapport (Q4 2024):
    - Omsetning: 14,5 millioner kroner.
    - Driftsresultat: 2 millioner kroner.
    - Resultat før skatt: 1,5 millioner kroner.
    - EBITDA: 2,5 millioner kroner.
    - EPS: 0,12 kroner per aksje.
    """

    # 1) Bruk OpenAI-implementasjonen
    openai_model = OpenAIModel(
        instructions=instructions,
        api_key="SK-DIN-API-NØKKEL-HER",
        model_name="gpt-3.5-turbo"
    )

    openai_raw_response = openai_model.run(user_text)
    print("OpenAI Rå-respons:\n", openai_raw_response)

    # Parse JSON hvis du ønsker struktur
    try:
        openai_data = json.loads(openai_raw_response)
    except json.JSONDecodeError:
        openai_data = {}
    print("OpenAI JSON:\n", json.dumps(openai_data, indent=2, ensure_ascii=False))

    # 2) Bruk DeepSeek-implementasjonen
    deepseek_model = DeepSeekModel(
        instructions=instructions,
        api_key="DIN-DEEPSEEK-API-NØKKEL-HER",
        model_name="deepseek-default"
    )

    deepseek_raw_response = deepseek_model.run(user_text)
    print("\nDeepSeek Rå-respons:\n", deepseek_raw_response)

    try:
        deepseek_data = json.loads(deepseek_raw_response)
    except json.JSONDecodeError:
        deepseek_data = {}
    print("DeepSeek JSON:\n", json.dumps(deepseek_data, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
