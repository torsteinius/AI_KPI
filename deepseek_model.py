# deepseek_model.py
from llm_model import LLMModel

class DeepSeekModel(LLMModel):
    def __init__(self, instructions: str, api_key: str = "DIN-DEEPSEEK-API-NØKKEL-HER", model_name: str = "deepseek-default"):
        """
        Fiktivt oppsett for DeepSeek (API-nøkkel, modellnavn, etc.).
        Sender instructions til super-klassen.
        """
        super().__init__(instructions)
        self.api_key = api_key
        self.model_name = model_name
        # Evt. opprett en DeepSeek-klient her.

    def run(self, text: str) -> str:
        """
        Kalles fra main med en brukertekst, returnerer (fiktivt) råtekst-svar.
        """
        # Eksempel på fiktivt kall:
        # raw_response = deepseek_client.generate_text(
        #     system_instructions=self.instructions,
        #     user_text=text,
        #     api_key=self.api_key,
        #     model=self.model_name
        # )
        # return raw_response

        # For å illustrere, returnerer vi en "dummy"-JSON-streng.
        dummy_json = """
        {
            "revenue": 123.4,
            "operating_income": 56.7,
            "profit_before_tax": 45.6,
            "profit_after_tax": 34.5,
            "ebitda": 50.0,
            "eps": 1.23,
            "backlog": 200.0,
            "fremtid1år": 3.0,
            "fremtid2år": 4.0,
            "fremtid3år": 5.0
        }
        """
        return dummy_json
