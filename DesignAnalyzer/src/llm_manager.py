


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

class GeminiLLMManager:
    def __init__(self, api_key: str = 'AIzaSyAQCZ2bJHOI6yapnei35Eyrd2IL19ts9GM', model_name: str = "gemini-1.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)
        self.commands: List[Dict] = []  # List of {"command": str, "args": List[str]}

    def addCommandAndArgs(self, command: str, args: List[str]):
        """Add a command and its argument names."""
        self.commands.append({"command": command, "args": args})

    def query(self, input_text: str) -> Optional[Tuple[str, Dict[str, str]]]:
        """Identify best command and extract argument values using Gemini."""
        if not self.commands:
            raise ValueError("No commands have been added.")

        # Construct the list of commands
        command_list = ""
        for i, cmd in enumerate(self.commands):
            args_str = ", ".join(cmd["args"]) if cmd["args"] else "none"
            command_list += f"{i+1}. {cmd['command']} (Args: {args_str})\n"

        # Compose the prompt
        prompt = (
            "You are a helpful assistant. Your task is to identify the best matching command from the list, "
            "based on the user's query. Also extract argument values if they are mentioned.\n\n"
            "Return ONLY a JSON object in this format:\n"
            '{\n  "command": "<command>",\n  "args": { "arg1": "value1", "arg2": "value2" }\n}\n\n'
            f"User Query: {input_text.strip()}\n\n"
            f"Available Commands:\n{command_list}"
        )

        print("\n🔹 Prompt sent to Gemini:\n", prompt)

        try:
            response = self.model.generate_content(prompt)
            reply = response.text.strip()
            print("\n🔸 Gemini Response:\n", reply)

            # Parse JSON from the model's response
            parsed = json.loads(reply)
            command = parsed["command"]
            args = parsed.get("args", {})
            return command, args

        except Exception as e:
            print("❌ Failed to parse Gemini response:", e)
            return None


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
            


global_LLM_manager = LLMManager()

# global_LLM_manager = GeminiLLMManager()

