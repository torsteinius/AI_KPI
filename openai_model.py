import time
import openai
from openai.error import InvalidRequestError, RateLimitError

from llm_model import LLMModel  # Your original parent class

class OpenAIModel(LLMModel):
    def __init__(self, instructions: str, model_name: str = "gpt-3.5-turbo"):
        """
        Example: Hides OpenAI-specific setup (API key, model name, etc.).
        'instructions' is stored in self.instructions for use as the system prompt.
        """
        super().__init__(instructions, model_name)  # Store instructions in self.instructions
        
        # Read API key from secrets.txt
        openai.api_key = None
        with open("secrets.txt", "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("OAI_Key="):
                    openai.api_key = line.split("=", 1)[1].strip()
                    break
        
        if not openai.api_key:
            raise ValueError("OpenAI API key not found in secrets.txt. Make sure it contains `OAI_Key=YOUR_KEY`.")

    def _safe_openai_call(
        self,
        messages: list[dict],
        temperature: float = 0.0,
        max_retries: int = 5,
        initial_wait: float = 8.0  # seconds
    ):
        """
        Calls openai.ChatCompletion.create with retries on RateLimitError.
        - 'max_retries': how many times to try before giving up
        - 'initial_wait': how many seconds to wait on first retry
          (could also do exponential backoff).
        """
        for attempt in range(max_retries):
            try:
                response = openai.ChatCompletion.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=temperature
                )
                return response
            except RateLimitError as e:
                # If we're out of retries, re-raise the error
                if attempt == max_retries - 1:
                    raise
                
                # Otherwise, wait a bit and try again
                # You can do exponential backoff if you prefer:
                # wait_time = initial_wait * (2 ** attempt)
                wait_time = initial_wait
                print(f"RateLimitError: {e}. Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)
        
        # If we somehow exit the loop (shouldn't happen normally), raise
        raise RuntimeError("Exhausted all retries for OpenAI call.")

    def _chunk_text(self, text: str, chunk_size: int = 2000) -> list[str]:
        """
        Splits 'text' into chunks of approximately 'chunk_size' words.
        You can adjust 'chunk_size' to fit your token or word limit needs.
        """
        words = text.split()
        chunks = []
        for i in range(0, len(words), chunk_size):
            chunk = " ".join(words[i : i+chunk_size])
            chunks.append(chunk)
        return chunks

    def _run_single_call(self, text: str) -> str:
        """
        Basic single-call approach to get the model's response.
        Raises InvalidRequestError or RateLimitError if something goes wrong.
        """
        messages = [
            {"role": "system", "content": self.instructions},
            {"role": "user", "content": text}
        ]
        response = self._safe_openai_call(messages, temperature=0.0)
        return response["choices"][0]["message"]["content"].strip()

    def _run_chunked(self, text: str, chunk_size: int = 2000) -> str:
        """
        Splits the text into chunks, summarizing incrementally, then
        returns a single final result at the end.
        """
        chunks = self._chunk_text(text, chunk_size=chunk_size)
        summary_so_far = ""

        # --- STEP A: Summarize each chunk ---
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
            response = self._safe_openai_call(messages, temperature=0.0)
            updated_summary = response["choices"][0]["message"]["content"].strip()
            summary_so_far = updated_summary

        # --- STEP B: Final step (one last call) ---
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
        final_response = self._safe_openai_call(final_messages, temperature=0.0)
        final_answer = final_response["choices"][0]["message"]["content"].strip()
        return final_answer

    def run(self, text: str, split_into_parts: bool = False, chunk_size: int = 2000) -> str:
        """
        If 'split_into_parts' is False, try a single-call approach.
        Otherwise, or if the single call fails due to context length,
        run chunk-based summarization. We wrap calls in '_safe_openai_call'
        to automatically retry on RateLimitError.
        """
        if not split_into_parts:
            # Try single-call approach
            try:
                return self._run_single_call(text)
            except InvalidRequestError as e:
                if "maximum context length" not in str(e):
                    # If it's some other error, just raise it
                    raise
                # If it's a context-length problem, fall back to chunked approach below

        # If single-call is not used or fails, do chunk-based summarization
        min_chunk_size = 200
        while True:
            try:
                return self._run_chunked(text, chunk_size=chunk_size)
            except InvalidRequestError as e:
                # if it's not about max context length, re-raise
                if "maximum context length" not in str(e):
                    raise

                # otherwise, shrink chunk_size and try again
                chunk_size = int(chunk_size * 0.8)
                if chunk_size < min_chunk_size:
                    raise RuntimeError(
                        "Even with repeated chunk-size reductions, the text is too large. "
                        "Try summarizing the text further or switch to a larger-model context."
                    )
