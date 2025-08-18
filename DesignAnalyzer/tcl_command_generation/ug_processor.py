

import spacy
import json

import re
import string

import os
import pickle

from collections import defaultdict



class UserGuideProcessor:
    def __init__(self):

        self.result_cmds = []
        self.result_args = []

        self.doc_name = None
        self.result_cmd_args = {}

        ##################################################################
        #
        # Make sure to download the vocabulary-model using following command:
        #
        #           ..\..\..\AppData\Local\Programs\Python\Python311\python.exe -m spacy download en_core_web_sm
        #
        #  Alternatively you can also download following:
        #
        #            en_core_web_md → medium (better accuracy, bigger vectors)
        #            en_core_web_lg → large (best accuracy, most memory use)
        #
        #
        ##################################################################

        self.nlp = spacy.load("en_core_web_sm")

    
    def set_doc_name(self, doc_name):
        self.doc_name = doc_name
        self.result_cmd_args = {}

    def _get_cache_path(self):
        """Return the path for the cache file based on doc_name."""
        return f"{self.doc_name}_cmd_args.pkl"

    def load_from_cache(self):
        """Load command-args dict from disk if available."""
        cache_path = self._get_cache_path()
        if os.path.exists(cache_path):
            with open(cache_path, "rb") as f:
                print(f"Loading command-args dict from cache: {cache_path}")
                return pickle.load(f)
        return None

    def save_to_cache(self, data):
        """Save command-args dict to disk."""
        cache_path = self._get_cache_path()
        with open(cache_path, "wb") as f:
            pickle.dump(data, f)
        print(f"Saved command-args dict to cache: {cache_path}")

    def is_cache_available(self):
        
        # 1. Try memory cache
        if self.result_cmd_args:
            return True

        # 2. Try disk cache
        cached = self.load_from_cache()
        if cached is not None:
            self.result_cmd_args = cached
            return True
        
        return False

    def getCommandsAndArgs(self, pages_text):
        """
        Extract commands and their arguments from a list of page texts.
        Uses disk cache to avoid re-extraction.
        
        Args:
            pages_text (list[str]): List of page contents.

        Returns:
            dict: { command_name: {arg_name: arg_values_dict, ...}, ... }
        """
        
        # 1. Check if we have cached data
        if self.is_cache_available():
            return self.result_cmd_args
        

        # 3. Extract fresh
        self.result_cmd_args = {}
        print("Extracting commands from PDF...")
        commands = set()
        for page_num, text in enumerate(pages_text):
            if text.strip():
                cmds = self.extract_commands(text)
                commands.update(cmds)

        print(f"Extracted {len(commands)} commands from PDF.")

        print("Extracting args for commands...")
        for cmd in commands:
            args = {}
            for page_num, text in enumerate(pages_text):
                a = self.extract_args(text, cmd)
                args.update(a)
            self.result_cmd_args[cmd] = args

        print(f"Extracted arguments for {len(self.result_cmd_args)} commands from PDF.")

        # 4. Save to disk cache
        self.save_to_cache(self.result_cmd_args)

        return self.result_cmd_args


    

    def extract_commands(self, page_text, check_n_pre_post_words=3):
        """
        Extracts unique command words from page_text that:
        1. Contain '_' and only letters/underscores.
        2. Have the word 'command' within N words before or after.
        
        Args:
            page_text (str): The text to process.
            check_n_pre_post_words (int): Number of words before/after to check for 'command'.
        Returns:
            list[str]: Unique matching commands.
        """
        doc = self.nlp(page_text)
        commands = set()

        for i, token in enumerate(doc):
            word = token.text
            # Match words containing '_' and only letters/underscores
            if '_' in word and re.fullmatch(r'[A-Za-z_]+', word):
                # Collect surrounding words in lowercase
                pre_words = [t.text.lower() for t in doc[max(0, i - check_n_pre_post_words):i]]
                post_words = [t.text.lower() for t in doc[i + 1:i + 1 + check_n_pre_post_words]]
                context = pre_words + post_words

                # Check if any context word contains "command"
                if any("command" in w for w in context):
                    commands.add(word)

        return list(commands)




    def extract_args(self, text, cmd_name):
        """
        Extract arguments and their values from a PDF text page based on a given command name.
        Handles:
            - Multi-line continuation with '\'
            - Arguments starting with '-'
            - Values with or without {}
            - Cases where values directly follow the command without arg-name

        Returns:
            dict: { arg-name: {example-1: value, example-2: value, ...}, ... }
        """

        # Step 1: Join lines that end with '\'
        lines = text.splitlines()
        merged_lines = []
        buffer = ""
        for line in lines:
            if line.rstrip().endswith("\\"):
                buffer += line.rstrip()[:-1] + " "  # remove '\' and add space
            else:
                buffer += line
                merged_lines.append(buffer)
                buffer = ""
        if buffer:
            merged_lines.append(buffer)

        # Step 2: Find the portion starting with the command name
        pattern = re.compile(rf"\b{re.escape(cmd_name)}\b", re.IGNORECASE)
        args_dict = defaultdict(dict)

        for line in merged_lines:
            match = pattern.search(line)
            if not match:
                continue

            # Extract text after command name
            after_cmd = line[match.end():].strip()

            # Step 3: Tokenize while preserving {} groups
            tokens = re.findall(r"\{[^}]*\}|\S+", after_cmd)

            current_arg = None
            example_counter = defaultdict(int)

            for token in tokens:
                if token.startswith("-"):  # New argument name
                    current_arg = token
                    example_counter[current_arg] = 0
                    if current_arg not in args_dict:
                        args_dict[current_arg] = {}
                else:
                    # This is a value — could be {value} or plain
                    value = token.strip("{}")
                    if current_arg is None:
                        # No arg-name yet — assign to a special placeholder
                        current_arg = "<no-arg>"
                        example_counter[current_arg] = 0
                        if current_arg not in args_dict:
                            args_dict[current_arg] = {}

                    example_counter[current_arg] += 1
                    args_dict[current_arg][f"example-{example_counter[current_arg]}"] = value

        return dict(args_dict)


