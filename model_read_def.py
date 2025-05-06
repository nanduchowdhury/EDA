from gpt4all import GPT4All
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
import textwrap

# Step 1: Load model
embedder = SentenceTransformer('all-MiniLM-L6-v2')  # Small & fast
llm = GPT4All("mistral-7b-instruct-v0.1.Q4_0.gguf")

# Step 2: Load your file and split into chunks
with open("power3.txt", "r", encoding="utf-8") as f:
    full_text = f.read()
chunks = textwrap.wrap(full_text, 1000)  # chars per chunk

# Step 3: Create embeddings
embeddings = embedder.encode(chunks, convert_to_numpy=True)

# Step 4: Build FAISS index
dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

# Step 5: Ask a question
query = "What does the data tell?"
query_embedding = embedder.encode([query], convert_to_numpy=True)
D, I = index.search(query_embedding, k=3)  # top 3 similar chunks

# Step 6: Feed to LLM
retrieved_chunks = "\n---\n".join(chunks[i] for i in I[0])
prompt = f"The following are code chunks:\n{retrieved_chunks}\n\nQuestion: {query}"

response = llm.generate(prompt, max_tokens=300)
print("\n🤖 Answer:\n", response)
