# Sample Knowledge: Local RAG

Local RAG is a free, local, login-free chat assistant. It indexes your files into
a local LanceDB vector store and answers questions grounded in your own content.

## Components
- Chainlit provides the chat web interface.
- A local HuggingFace transformers LLM generates the answers, so no API keys or
  logins are required.
- Haystack and LanceDB provide headless retrieval — no text generation.

## Retrieval
The query pipeline embeds the question locally with sentence-transformers and
searches LanceDB for the most relevant chunks, returning them to the LLM with
numbered source citations.
