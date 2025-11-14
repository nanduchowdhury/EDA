


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
from langchain.schema import AIMessage, HumanMessage
from langchain_google_genai import ChatGoogleGenerativeAI


class baseLLMManager:
    def __init__(self):

        self.columns: List[str] = []
        self.commands: List[Dict[str, List[str]]] = []
        self.chat_history: List[Dict[str, str]] = []  # user_query + gemini_response
        self.context_window_size: int = 5


    def set_context_window_size(self, window_size: int = 5):
        self.context_window_size = window_size

    def reset_context(self):
        self.chat_history.clear()

    def addCommandAndArgs(self, command: str, args: List[str]):
        self.commands.append({"command": command, "args": args})

    def addColumnName(self, columnName: str):
        self.columns.append(columnName)


    def processLlmResponse(self, llm_response, user_query: str):

        try:
            # Normalize different response shapes to a single string
            if hasattr(llm_response, "content"):
                reply = llm_response.content.strip()
            elif isinstance(llm_response, (list, tuple)) and len(llm_response) > 0:
                first = llm_response[0]
                if hasattr(first, "content"):
                    reply = first.content.strip()
                else:
                    reply = str(first).strip()
            elif isinstance(llm_response, str):
                reply = llm_response.strip()
            else:
                reply = str(llm_response).strip()

            # Save the user-Gemini pair in chat history
            self.chat_history.append({
                "user_query": user_query.strip(),
                "gemini_response": reply
            })

            # Extract JSON from response
            match = re.search(r'```json\s*(\{.*?\})\s*```', reply, re.DOTALL)
            json_str = match.group(1) if match else reply
            result = json.loads(json_str)
            return result

        except Exception as e:
            print("❌ Failed to parse LLM response:", e)
            return None



    def _construct_prompt(self, user_prompt: str) -> str:
        # Format last N history entries
        recent_history = self.chat_history[-self.context_window_size:]

        user_history_str = "\n".join(
            f'{{\n  "User": {json.dumps(item["user_query"])},\n  "Assistant": {item["gemini_response"]}\n}}'
            for item in recent_history
        )

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

    Based on the current user prompt and recent history, classify the request into one of:
    1. An action/command execution from available commands.
    2. A SQL-style analysis based on table columns.
    3. A general query needing a direct LLM response.

    Recent User-Gemini History:
    {user_history_str}

    Input Table Columns:
    {columns_str}

    Available Commands and Actions:
    {commands_str}

    Current User Prompt:
    "{user_prompt.strip()}"

    {format_hint}
    Respond ONLY with the appropriate JSON.
    """



class GeminiLangChainLLMManager(baseLLMManager):
    def __init__(self, 
                 api_key: str = 'AIzaSyCCbq3FWvyrS1jnStHeDt3Xzgi8A1E7McI', 
                 model_name: str = "gemini-1.5-flash", 
                 temperature: float = 0.2):
        super().__init__()

        self.llm = ChatGoogleGenerativeAI(
            model=model_name,
            google_api_key=api_key,
            temperature=temperature
        )


    def query(self, user_prompt: str) -> Optional[Dict]:
        if not self.commands and not self.columns:
            raise ValueError("No commands or columns defined.")

        prompt = self._construct_prompt(user_prompt)
        print("\n🔹 Prompt sent to Gemini:\n", prompt)

        response = self.llm([HumanMessage(content=prompt)])
        result = self.processLlmResponse(response, user_prompt)
        return result



###############################################################################
#
# This class uses downloaded inhouse model. Please check
# llm_model_download.py for instructions on how to download a model.
#
###############################################################################


class LLMManager(baseLLMManager):
    def __init__(self, model_path: str = "mistral-7b-instruct-v0.1.Q4_0.gguf"):
        super().__init__()

        # model_path = "tinyllama-1.1b-chat-v1.0.Q4_0.gguf"

        self.llm = GPT4All(model_path)


    def query(self, input_text: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """Use the model to find best matching command and extract argument values."""
        if not self.commands:
            raise ValueError("No commands added yet. Use addCommandAndArgs() first.")

        # Build prompt for GPT4All
        command_list = ""
        for idx, cmd in enumerate(self.commands):
            args_str = ", ".join(cmd["args"]) if cmd["args"] else "none"
            command_list += f"{idx + 1}. {cmd['command']} (Args: {args_str})\n"

        prompt = self._construct_prompt(input_text)
        print("\n🔹 Prompt sent to local-LLM:\n", prompt)

        # Call GPT4All
        with self.llm.chat_session():
            
            # response = self.llm.generate(prompt, max_tokens=300).strip()

            response = self.llm.generate(
                        prompt,
                        max_tokens=300,
                        temp=0.7,
                        top_p=0.9
                    ).strip()

        print(f"Model response:\n{response}\n")

        result = self.processLlmResponse(response, input_text)
        return result
            


global_LLM_manager = LLMManager()

# global_LLM_manager = GeminiLangChainLLMManager()

