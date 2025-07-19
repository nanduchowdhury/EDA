


from typing import List, Dict, Optional, Tuple
from sentence_transformers import SentenceTransformer, util
import re
import json

import torch

from gpt4all import GPT4All

import os


import json
import google.generativeai as genai

###############################################################################
#
# This class uses Google Gemini mode over the internet.
# When last tried, it always errored out due to quota-limit-exceed.
#
###############################################################################

import json
import re
from typing import List, Dict, Optional, Union



import json
import re
from typing import List, Dict, Optional
from langchain.schema import HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


class GeminiLangChainLLMManager:
    def __init__(self, 
                 api_key: str = 'AIzaSyCCbq3FWvyrS1jnStHeDt3Xzgi8A1E7McI', 
                 model_name: str = "gemini-1.5-flash", 
                 temperature: float = 0.2):
    
        self.columns: List[str] = []
        self.commands: List[Dict[str, List[str]]] = []
        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature
        )

    def addCommandAndArgs(self, command: str, args: List[str]):
        self.commands.append({"command": command, "args": args})

    def addColumnName(self, columnName: str):
        self.columns.append(columnName)

    def query(self, user_prompt: str) -> Optional[Dict]:
        if not self.commands and not self.columns:
            raise ValueError("No commands or columns defined.")

        prompt = self._construct_prompt(user_prompt)
        print("\n🔹 Prompt sent to Gemini:\n", prompt)

        try:
            response = self.llm([HumanMessage(content=prompt)])
            reply = response.content.strip()
            print("\n🔸 Gemini Response:\n", reply)

            # Handle ```json blocks
            match = re.search(r'```json\s*(\{.*?\})\s*```', reply, re.DOTALL)
            json_str = match.group(1) if match else reply
            result = json.loads(json_str)
            return result

        except Exception as e:
            print("❌ Failed to parse Gemini response:", e)
            return None

    def _construct_prompt(self, user_prompt: str) -> str:
        columns_str = "\n".join(f"- {col}" for col in self.columns)
        commands_str = "\n".join(
            f"- {cmd['command']} (Args: {', '.join(cmd.get('args', []))})"
            for cmd in self.commands
        )

        format_hint = '''
Return a JSON object in exactly **one** of the following forms:

1. If the prompt matches a command:
{
  "ResultMode": "COMMAND_OR_ACTION_RUN",
  "output": {
    "command_name": "<command>",
    "args": { "arg1": "value1", "arg2": "value2" }
  }
}

2. If the prompt asks for SQL analysis:
{
  "ResultMode": "SQL_COLUMN_ANALYSIS",
  "output": {
    "sql_query": "SELECT ... FROM table WHERE ..."
  }
}

3. If the LLM gives its own answer:
{
  "ResultMode": "LLM_OWN_RESPONSE",
  "output": {
    "llm_own_answer": "Your answer here"
  }
}
'''

        return f"""
You are a helpful assistant.

Based on the user prompt, classify the request into one of:
1. An action/command execution from available commands.
2. A SQL-style analysis based on table columns.
3. A general query needing a direct LLM response.

Input Table Columns:
{columns_str}

Available Commands and Actions:
{commands_str}

User Prompt:
"{user_prompt.strip()}"

{format_hint}
Respond ONLY with the appropriate JSON.
"""


###############################################################################
#
# This class uses downloaded inhouse model. Please check
# llm_model_download.py for instructions on how to download a model.
#
###############################################################################


class LLMManager:
    def __init__(self, model_path: str = "mistral-7b-instruct-v0.1.Q4_0.gguf"):
        
        # model_path = "tinyllama-1.1b-chat-v1.0.Q4_0.gguf"

        self.llm = GPT4All(model_path)

        self.commands: List[Dict] = []  # List of dicts: {"command": str, "args": List[str]}

    def addCommandAndArgs(self, command: str, args: List[str]):
        """Register a command and its argument names."""
        self.commands.append({"command": command, "args": args})

    def query(self, input_text: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """Use the model to find best matching command and extract argument values."""
        if not self.commands:
            raise ValueError("No commands added yet. Use addCommandAndArgs() first.")

        # Build prompt for GPT4All
        command_list = ""
        for idx, cmd in enumerate(self.commands):
            args_str = ", ".join(cmd["args"]) if cmd["args"] else "none"
            command_list += f"{idx + 1}. {cmd['command']} (Args: {args_str})\n"

        prompt = (
            "You are a helpful assistant. Your job is to identify one command from the list of commands that best matches the user query.\n"
            "You are also to extract any argument values provided by the user.\n"
            "Return the result strictly in this JSON format:\n"
            '{\n  "command": "<command>",\n  "args": { "arg1": "value1", "arg2": "value2", ... }\n}\n\n'
            f"User Query: {input_text.strip()}\n\n"
            f"Available Commands:\n{command_list}\n"
        )

        print(f"Prompt sent to model:\n{prompt}\n")

        # Call GPT4All
        with self.llm.chat_session():
            response = self.llm.generate(prompt, max_tokens=300).strip()

        print(f"Model response:\n{response}\n")

        # Parse JSON
        try:
            parsed = json.loads(response)
            command = parsed["command"]
            args = parsed.get("args", {})
            return command, args
        except Exception as e:
            print("Failed to parse response as JSON:", e)
            return None
            


# global_LLM_manager = LLMManager()

global_LLM_manager = GeminiLangChainLLMManager()

