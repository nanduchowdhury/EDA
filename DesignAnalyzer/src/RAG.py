import faiss
import numpy as np
import pickle
import google.generativeai as genai
import textwrap

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
        
        # The embedding size for text-embedding-004 is 768.
        self.dimension = 768
        
        # Initialize a FAISS index for L2 distance.
        self.index = faiss.IndexFlatL2(self.dimension)
        
        # Stores (page_num, chunk_text) for easy retrieval.
        self.documents = []

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

    def load_from_list(self, page_text_list, chunk_size=1000, overlap=100):
        """
        Loads data from a list of text content and builds the FAISS index.
        The list should contain strings, where each string is the text of a page.
        
        Args:
            page_text_list (list): A list of strings, where each string is the content of a page.
            chunk_size (int): The maximum size of each text chunk.
            overlap (int): The number of characters to overlap between chunks.
        """
        for page_num, text in enumerate(page_text_list):
            print(f'Processing page {page_num + 1}...')

            # The original code's chunking logic was flawed. 
            # `textwrap.wrap` is a simple and effective way to chunk text.
            # Using `textwrap.wrap` is not ideal for overlapping chunks.
            # Let's revert to a corrected version of the original loop.
            start = 0
            while start < len(text):
                end = start + chunk_size
                chunk = text[start:end]
                self.add_chunk(page_num, chunk)
                start += chunk_size - overlap
                
            # If the last chunk is not a full chunk, add it as well.
            if len(text) - start > 0:
                chunk = text[start:]
                self.add_chunk(page_num, chunk)


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
            You are an AI assistant tasked with answering a question based on provided context.
            Follow these rules:
            1. Only use information from the provided context.
            2. If the context does not contain the answer, state that you don't know.
            3. Do not make up any information.
            4. Cite the page number from the context where you found the information.

            Context:
            {context}

            Question: {query}
            
            Answer:
            """

            # Corrected code: First, get the model object.
            model_instance = genai.GenerativeModel(self.model)

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

