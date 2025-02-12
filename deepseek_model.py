import os
import requests
import json
from llm_model import LLMModel

class DeepSeekModel(LLMModel):
    def __init__(self, instructions: str, model_name: str = "deepseek-default"):
        """
        Oppsett for DeepSeek (API-nøkkel, modellnavn, etc.).
        Sender instructions til super-klassen.

        API-nøkkel leses fra `secrets.txt` med formatet: 
        DeepSeek_Key=DIN_API_NØKKEL
        """
        super().__init__(instructions)

        # Standardiser API-nøkkel
        self.api_key = None
        try:
            with open("secrets.txt", "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("DeepSeek_Key="):
                        self.api_key = line.split("=", 1)[1].strip()
                        break
        except FileNotFoundError:
            raise ValueError("Filen `secrets.txt` mangler. Opprett den og legg inn `DeepSeek_Key=DIN_API_NØKKEL`.")

        if not self.api_key:
            raise ValueError("DeepSeek API-nøkkel ikke funnet i `secrets.txt`. Sørg for at den inneholder `DeepSeek_Key=DIN_API_NØKKEL`.")

        self.model_name = model_name
        self.api_url = "https://api.deepseek.com/generate"  # Eksempel-URL, endre ved behov.

    def run(self, text: str) -> str:
        """
        Kalles fra main med en brukertekst, returnerer AI-generert svar.

        :param text: Brukerinput
        :return: Modellens svar i JSON-format
        """
        payload = {
            "model": self.model_name,
            "prompt": text,
            "instructions": self.instructions
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        try:
            response = requests.post(self.api_url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()  # Kaster feil hvis API-kallet feiler
            return response.json()
        except requests.exceptions.RequestException as e:
            return json.dumps({"error": f"DeepSeek API-kall feilet: {str(e)}"})
