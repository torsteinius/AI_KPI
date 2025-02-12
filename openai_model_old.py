# openai_model.py
import openai
from llm_model import LLMModel

class OpenAIModel(LLMModel):
    def __init__(self, instructions: str, api_key: str = "SK-DIN-API-NØKKEL-HER", model_name: str = "gpt-3.5-turbo"):
        """
        Eksempel: Skjuler OpenAI-spesifikt oppsett (API-nøkkel, modellnavn, etc.).
        'instructions' tas med og sendes videre til super-klassen.
        """
        super().__init__(instructions)  # Lagrer instructions i self.instructions
        openai.api_key = api_key
        self.model_name = model_name

    def run(self, text: str) -> str:
        """
        Oppretter en chat (OpenAI ChatCompletion) med:
        - system-melding (self.instructions)
        - user-melding (text)
        Returnerer rå tekst fra modellen.
        """
        response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=[
                {"role": "system", "content": self.instructions},
                {"role": "user", "content": text}
            ],
            temperature=0.0
        )
        return response["choices"][0]["message"]["content"].strip()
