# openai_model.py
import openai
from llm_model import LLMModel

class OpenAIModel(LLMModel):
    def __init__(self, instructions: str, model_name: str = "gpt-3.5-turbo"):
        """
        Example: Hides OpenAI-specific setup (API key, model name, etc.).
        'instructions' is stored in self.instructions for use as the system prompt.
        """
        super().__init__(instructions)  # Lagrer instructions i self.instructions
        
        # Read API key from secrets.txt
        # The file should contain a line like: OAI_Key=sk-xxxxx
        openai.api_key = None
        with open("secrets.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("OAI_Key="):
                    openai.api_key = line.split("=", 1)[1].strip()
                    break
        
        if not openai.api_key:
            raise ValueError("OpenAI API key not found in secrets.txt. Make sure it contains `OAI_Key=YOUR_KEY`.")

        self.model_name = model_name

    def run(self, text: str) -> str:
        """
        Creates an OpenAI ChatCompletion with:
        - system message (self.instructions)
        - user message (text)
        Returns raw text from the model response.
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
