import faiss
import numpy as np
import pickle
import google.generativeai as genai
import textwrap

import json
import re

import os

class GeminiRAG:
    """
    A class for Retrieval-Augmented Generation (RAG) using Google's Gemini models
    and the FAISS library for efficient similarity search.
    """
    def __init__(self, api_key='AIzaSyCCbq3FWvyrS1jnStHeDt3Xzgi8A1E7McI', model="gemini-1.5-flash", embed_model="models/text-embedding-004"):
        """
        Initializes the GeminiRAG instance.
        
        Args:
            api_key (str): Your Google API key.
            model (str): The name of the Gemini generation model to use.
            embed_model (str): The name of the Gemini embedding model to use.
        """
        # It's better practice to configure the API key from environment variables
        # or a secure configuration file, not hardcoded.
        genai.configure(api_key=api_key)
        self.model = model
        self.embed_model = embed_model
        
        self.doc_name = None  # To store the name of the document being processed
        self.doc_name_changed = False

        # The embedding size for text-embedding-004 is 768.
        self.dimension = 768
        
        # Initialize a FAISS index for L2 distance.
        self.index = faiss.IndexFlatL2(self.dimension)
        
        # Stores (page_num, chunk_text) for easy retrieval.
        self.documents = []

        self.prompt_base_rules = textwrap.dedent("""
            You are an AI assistant tasked with answering a question based on provided context.
            Follow these rules:
                1. Only use information from the provided context.
                2. If the context does not contain the answer, state that you don't know.
                3. Do not make up any information.
                4. Cite the page number from the context where you found the information.
        """)


    def set_doc_name(self, doc_name):
        self.doc_name = doc_name
        self.doc_name_changed = True


    def embed_text(self, text):
        """
        Gets the embedding vector for the given text using the Gemini API.

        Args:
            text (str): The text to embed.

        Returns:
            np.ndarray: A 1D numpy array representing the embedding vector.
            
        Raises:
            Exception: If there's an error getting the embedding.
        """
        # The Gemini API `embed_content` returns an embedding for a single string.
        # It's an API call, so wrapping it in a try-except is good practice.
        try:
            response = genai.embed_content(
                model=self.embed_model,
                content=text,
                task_type="RETRIEVAL_DOCUMENT" # Specify task type for better embeddings
            )
            
            # The API response is structured as a dictionary.
            # We need to access the 'embedding' key directly, not 'embedding'['values'].
            embedding_values = response['embedding']
            
            # The `embed_content` function returns a list of floats.
            # We convert this to a numpy array of the correct dtype.
            return np.array(embedding_values, dtype=np.float32)
        except Exception as e:
            print(f"Error getting embedding: {e}")
            return None

    def add_chunk(self, page_num, text):
        """
        Stores a text chunk and its embedding in the FAISS index and documents list.

        Args:
            page_num (int): The page number of the chunk.
            text (str): The text content of the chunk.
        """
        embedding = self.embed_text(text)
        if embedding is not None:
            # FAISS requires a 2D numpy array, even for a single vector.
            # Reshape the 1D embedding array to (1, dimension).
            self.index.add(np.array([embedding]))
            self.documents.append((page_num, text))

    def get_index_filenames(self):
        base = os.path.splitext(os.path.basename(self.doc_name))[0]
        index_file = f"rag_index_{base}.faiss"
        docs_file = f"rag_docs_{base}.pkl"
        return index_file, docs_file


    def load_from_list(self, page_text_list, chunk_size=1000, overlap=100):
        """
        Loads data from a list of text content and builds the FAISS index.
        If index files exist for this doc_name, loads them instead of recomputing.
        Otherwise, builds index and saves for future use.
        """

        if not self.doc_name_changed:
            return

        self.doc_name_changed = False

        index_file, docs_file = self.get_index_filenames()
        if os.path.exists(index_file) and os.path.exists(docs_file):
            self.load(index_file, docs_file)
            print(f"[INFO] Loaded existing FAISS index and docs for '{self.doc_name}'")
            return

        # Build index from scratch
        for page_num, text in enumerate(page_text_list):
            print(f'Processing page {page_num + 1}...')
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunk = text[start:end]
                self.add_chunk(page_num, chunk)
                start += chunk_size - overlap
            if len(text) - start > 0:
                chunk = text[start:]
                self.add_chunk(page_num, chunk)

        # Save for next time
        self.save(index_file, docs_file)
        print(f"[INFO] Saved FAISS index and docs for '{self.doc_name}'")


    def retrieve(self, query, top_k=3):
        """
        Finds the top_k most relevant documents for a given query.
        
        Args:
            query (str): The query string.
            top_k (int): The number of relevant documents to retrieve.

        Returns:
            list: A list of tuples, where each tuple is (page_num, chunk_text).
        """
        query_emb = self.embed_text(query)
        if query_emb is None:
            return []
            
        # FAISS search also requires a 2D array.
        distances, indices = self.index.search(np.array([query_emb]), top_k)
        
        # The indices are returned as a 2D array, so we access the first row.
        return [(self.documents[i][0], self.documents[i][1]) for i in indices[0]]

    def ask(self, query, top_k=3):
            """Retrieve context and query Gemini."""
            relevant_docs = self.retrieve(query, top_k)
            context = "\n\n".join([f"[Page {pg + 1}] {txt}" for pg, txt in relevant_docs])
            prompt = f"""
            
            {self.prompt_base_rules}

            Context:
            {context}

            Question: {query}
            
            Answer:
            """

            # Corrected code: First, get the model object.
            model_instance = genai.GenerativeModel(self.model)

            print(f"Querying Gemini model with prompt:\n{prompt}")
            print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")


            # Then, call generate_content on that object.
            response = model_instance.generate_content(
                contents=[prompt]
            )
            
            return response.text

    def save(self, index_file="rag_index.faiss", docs_file="rag_docs.pkl"):
        """
        Saves the FAISS index and documents to files.
        """
        faiss.write_index(self.index, index_file)
        with open(docs_file, "wb") as f:
            pickle.dump(self.documents, f)
        print(f"[✅] RAG index saved to {index_file} and documents to {docs_file}")

    def load(self, index_file="rag_index.faiss", docs_file="rag_docs.pkl"):
        """
        Loads the FAISS index and documents from files.
        """
        try:
            self.index = faiss.read_index(index_file)
            with open(docs_file, "rb") as f:
                self.documents = pickle.load(f)
            print(f"[✅] RAG index loaded from {index_file} and documents from {docs_file}")
        except FileNotFoundError:
            print("[❌] Could not find the index or documents files. Please create them first.")
            self.index = faiss.IndexFlatL2(self.dimension)
            self.documents = []

    def load_from_list_1(self, page_text_list, chunk_size=1000, overlap=100):
        """
        Load data from a list: [(page_num, text), ...] and build FAISS index.
        """
        for page_num, text in enumerate(page_text_list):
            
            print(f'Processing page {page_num + 1}...')

            start = 0
            while start < len(text):
                end = min(start + chunk_size, len(text))
                chunk = text[start:end]
                self.add_chunk(page_num, chunk)
                start += chunk_size - overlap




class GeminiTclRAG:
    def __init__(self, api_key='AIzaSyCCbq3FWvyrS1jnStHeDt3Xzgi8A1E7McI', model="gemini-1.5-flash"):
        """
        page_text: dict {page_number: text} OR list[str] (page texts)
        """
        genai.configure(api_key=api_key)
        
        self.model = model

        self.cmds_and_args = None
        self.cmds = None

        self.prompt_for_cmd = textwrap.dedent("""
            You are an AI assistant tasked with picking the best command and mapping the user question.
            Follow these rules:
                1. Only use information from the provided context.
                2. Find the command that best matches the user question.
                3. Assign values to args based on what user has specified in the question.
                4. Return the result strictly in this JSON format:
                   {
                     "command": "<command>"
                   }
        """)

        self.prompt_for_arg = textwrap.dedent("""
            You are an AI assistant tasked with picking the best and required args & values as per the user question.
            Follow these rules:
                1. Only use information from the provided context.
                2. Find the args that best matches the user question and the command mentioned below.
                3. Assign values to args based on what user has specified in the question.
                4. Return the result strictly in this JSON format:
                   {
                     "args": { "arg1": "value1", "arg2": "value2", ... }
                   }
        """)



    def set_cmds_and_args(self, cmds_and_args):
        
        self.cmds_and_args = cmds_and_args

        self.cmds = list(self.cmds_and_args.keys())
        

    def ask(self, user_query):
        """
        Ask the Gemini model for the best command and args based on the user query.
        
        Args:
            user_query (str): The user's natural language query.

        Returns:
            str: The response from the Gemini model.
        """
        if not self.cmds_and_args:
            raise ValueError("Commands and args must be set before asking.")

        # First, ask for the command.
        cmd_response = self.ask_cmd(user_query)
        print(f"ask_cmd response: {cmd_response}")

        if isinstance(cmd_response, str):
            cmd_response = json.loads(cmd_response)
        cmd = cmd_response.get("command")

        if cmd and cmd in self.cmds_and_args:
            args_response = self.ask_args(cmd, user_query)
            print(f"ask_args response: {args_response}")

            if isinstance(args_response, str):
                args_response = json.loads(args_response)

            args = args_response.get("args")
            args_str = self.get_all_key_value_as_flat_from_json(args)

            return f"{cmd} {args_str}"

        raise ValueError(f"Gemini returned '{cmd}' not found in available commands.")
        


    def ask_cmd(self, query):

        prompt = f"""
            
            {self.prompt_for_cmd}

            Context:
            {self.cmds}

            Question: {query}
            
            Answer:
            """

        model_instance = genai.GenerativeModel(self.model)

        print(f"Querying Gemini model for cmd with prompt:\n{prompt}")
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

        # Then, call generate_content on that object.
        response = model_instance.generate_content(
            contents=[prompt]
        )

        return self.extract_json_from_response(response.text)


    def ask_args(self, cmd, query):
        prompt = f"""

            {self.prompt_for_arg}

            Context:
            {self.cmds_and_args[cmd]}

            Command: {cmd}

            Question: {query}
            
            Answer:
            """

        model_instance = genai.GenerativeModel(self.model)

        print(f"Querying Gemini model for args with prompt:\n{prompt}")
        print("+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++")

        # Then, call generate_content on that object.
        response = model_instance.generate_content(
            contents=[prompt]
        )

        return self.extract_json_from_response(response.text)


    def extract_json_from_response(self, text):
        # Find the first JSON object in the string
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            raise ValueError("No JSON object found in Gemini response.")


    def get_all_key_value_as_flat_from_json(self, json_data):
        """
        Recursively extract all keys and values from a nested JSON (dict/list)
        and return them as a single flat space-separated string.
        
        Args:
            json_data (dict | list | str | int | float | bool | None)
        
        Returns:
            str: Flattened keys and values as a single string.
        """
        flat_parts = []

        def _flatten(data):
            if isinstance(data, dict):
                for k, v in data.items():
                    flat_parts.append(str(k))
                    _flatten(v)
            elif isinstance(data, list):
                for item in data:
                    _flatten(item)
            else:
                flat_parts.append(str(data))

        _flatten(json_data)
        return " ".join(flat_parts)






