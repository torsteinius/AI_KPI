import openai
from llm_model import LLMModel

class OpenAIModel(LLMModel):
    def __init__(self, instructions: str, model_name: str = "gpt-3.5-turbo"):
        """
        Example: Hides OpenAI-specific setup (API key, model name, etc.).
        'instructions' is stored in self.instructions for use as the system prompt.
        """
        super().__init__(instructions)  # Store instructions in self.instructions
        
        # Read API key from secrets.txt
        openai.api_key = None
        with open("secrets.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("OAI_Key="):
                    openai.api_key = line.split("=", 1)[1].strip()
                    break
        
        if not openai.api_key:
            raise ValueError("OpenAI API key not found in secrets.txt. Make sure it contains `OAI_Key=YOUR_KEY`.")

        self.model_name = model_name

    def _chunk_text(self, text: str, chunk_size: int = 2000) -> list[str]:
        """
        Splits 'text' into chunks of approximately 'chunk_size' words.
        You can adjust 'chunk_size' to fit your token or word limit needs.
        """
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i:i+chunk_size])
            chunks.append(chunk)
        return chunks

    def _run_single_call(self, text: str) -> str:
        """
        Basic single-call approach to get the model's response.
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

    def _run_chunked(self, text: str, chunk_size: int = 2000) -> str:
        """
        Splits the text into chunks, summarizing incrementally, then
        returns a single final result at the end.
        """
        # 1. Split text
        chunks = self._chunk_text(text, chunk_size=chunk_size)
        
        # 2. Keep a running summary
        summary_so_far = ""
        
        # --- STEP A: Summarize each chunk into 'summary_so_far' ---
        for i, chunk in enumerate(chunks):
            messages = [
                {
                    "role": "system",
                    "content": (
                        f"{self.instructions}\n\n"
                        "You will receive text in chunks. Your job is to incorporate each chunk "
                        "into an ongoing summary, preserving the important details."
                    )
                },
                {
                    "role": "assistant",
                    "content": f"Current summary so far:\n{summary_so_far}"
                },
                {
                    "role": "user",
                    "content": f"Here is chunk #{i+1}:\n{chunk}\n\nUpdate the summary."
                }
            ]

            response = openai.ChatCompletion.create(
                model=self.model_name,
                messages=messages,
                temperature=0.0
            )
            
            # The model's response is the updated summary
            updated_summary = response["choices"][0]["message"]["content"].strip()
            summary_so_far = updated_summary
        
        # --- STEP B: Final call for the final output/answer ---
        final_messages = [
            {
                "role": "system",
                "content": (
                    f"{self.instructions}\n\n"
                    "You have processed multiple chunks and created a summary. "
                    "Now please provide the final answer or output based on that summary."
                )
            },
            {
                "role": "assistant",
                "content": f"Final summary so far:\n{summary_so_far}"
            },
            {
                "role": "user",
                "content": "Please provide the final answer or output."
            }
        ]

        final_response = openai.ChatCompletion.create(
            model=self.model_name,
            messages=final_messages,
            temperature=0.0
        )
        final_answer = final_response["choices"][0]["message"]["content"].strip()
        return final_answer

    def run(self, text: str, split_into_parts: bool = False, chunk_size: int = 2000) -> str:
        """
        If 'split_into_parts' is False, the text is processed in one single call.
        If 'split_into_parts' is True, the text is split into chunks for incremental summarization.
        """
        if not split_into_parts:
            # Single-call approach
            return self._run_single_call(text)
        else:
            # Chunk-based approach
            return self._run_chunked(text, chunk_size=chunk_size)
