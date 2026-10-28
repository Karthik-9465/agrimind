# RAG Ingestion Skill — Agrimind Agentic

Guidelines for document ingestion and Chroma vector store setup:

## Ingestion Pipeline
1. Load PDF documents from `vector_store/docs/`.
2. Split documents into chunks using `RecursiveCharacterTextSplitter` (chunk size: 800, overlap: 100).
3. Generate embeddings using `GoogleGenerativeAIEmbeddings` or lightweight HuggingFace/Chroma embeddings.
4. Persist index in `vector_store/chroma_db/`.
