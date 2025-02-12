# llm_model.py
from abc import ABC, abstractmethod

class LLMModel(ABC):
    def __init__(self, instructions: str):
        """
        Lagre instruksjoner (systemprompt) i selve objektet.
        Alle konkrete LLM-klasser vil arve dette.
        """
        self.instructions = instructions

    @abstractmethod
    def run(self, text: str) -> str:
        """
        Kalles med en tekst (f.eks. brukerens innhold eller prompt),
        og returnerer råtekstsvar fra LLM-en.
        """
        pass
