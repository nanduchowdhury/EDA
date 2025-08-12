from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS
from langchain.embeddings import OpenAIEmbeddings
from typing import Dict, List, Any

class RAGWorkflow:
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 100, embedding_model: str = "text-embedding-3-large"):
        """
        Initialize the RAG workflow.
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_model = embedding_model
        self.vectorstore = None
        self.chunks_meta = []  # Stores chunks + page info
        self.pages_text = {}
        self.embeddings = OpenAIEmbeddings(model=self.embedding_model)

    def setPagesText(self, pages_text: Dict[int, str]):
        """
        Set the text for each page of the PDF.
        pages_text: dict {page_number: page_text}
        """
        self.pages_text = pages_text
        self._process_pages()

    def _process_pages(self):
        """
        Splits all pages into chunks and builds vectorstore.
        """
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap
        )

        docs = []
        self.chunks_meta.clear()

        for page_num, text in self.pages_text.items():
            page_chunks = text_splitter.split_text(text)
            for chunk in page_chunks:
                docs.append(chunk)
                self.chunks_meta.append({"page": page_num, "text": chunk})

        # Create FAISS vectorstore in-memory
        self.vectorstore = FAISS.from_texts(
            [c["text"] for c in self.chunks_meta],
            self.embeddings,
            metadatas=[{"page": c["page"]} for c in self.chunks_meta]
        )

    def getAssociatedDocs(self, text_query: str, k: int = 4) -> List[Any]:
        """
        Retrieves the top-k most relevant chunks for a given query.
        Returns list of LangChain Document objects.
        """
        if not self.vectorstore:
            raise ValueError("Vectorstore is empty. Please call setPagesText() first.")

        return self.vectorstore.similarity_search(text_query, k=k)

    def getChunks(self) -> List[Dict[str, Any]]:
        """
        Returns the processed chunks along with their page numbers.
        """
        return self.chunks_meta



