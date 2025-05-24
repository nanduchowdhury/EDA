
from gpt4all import GPT4All
from typing import List, Optional

class LLMManager:
    def __init__(self, model_path: str = "mistral-7b-instruct-v0.1.Q4_0.gguf"):
        self.llm = GPT4All(model_path)
        self.context_lines: List[str] = []

    def set_context_lines(self, lines: List[str]):
        """Set the list of lines for RAG-like context retrieval."""
        self.context_lines = lines

    def set_context_line(self, line: str):
        """Add a single line to the context lines."""
        self.context_lines.append(line)

    def query(self, input_text: str) -> Optional[str]:
        """Query the model and return the best matching context line."""
        if not self.context_lines:
            raise ValueError("No context lines set. Use set_context_lines() first.")

        # Format prompt for RAG-like reasoning
        prompt = (
            "You are a helpful assistant. Given the user query below and a list of text snippets, "
            "return the exact snippet from the list that best matches the query.\n\n"
            f"Query: {input_text.strip()}\n\n"
            "Snippets:\n"
        )
        for i, line in enumerate(self.context_lines):
            prompt += f"{i+1}. {line}\n"

        prompt += "\nRespond with the number of the most relevant snippet only."

        # Call the model
        with self.llm.chat_session():
            response = self.llm.generate(prompt, max_tokens=10).strip()

        # Extract and return the matched line
        try:
            best_index = int(response) - 1
            if 0 <= best_index < len(self.context_lines):
                return self.context_lines[best_index]
        except ValueError:
            pass  # Unexpected output format

        return None  # No valid match found


global_LLM_manager = LLMManager()

