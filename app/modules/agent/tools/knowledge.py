import os
import glob
import re
import math
from typing import List, Dict, Any, Optional, Set
from langchain_core.tools import tool
from app.modules.agent.schemas import KnowledgeResult

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "vector_store", "docs"))

class LocalVectorKnowledgeStore:
    """
    RAG agronomy document chunking and retrieval engine using section-level chunking
    and TF-IDF cosine similarity scoring across official ICAR & SAU publications.
    """

    def __init__(self, docs_directory: str = DOCS_DIR):
        self.docs_directory = docs_directory
        self.chunks: List[Dict[str, Any]] = []
        self.df: Dict[str, int] = {} # Document frequency for IDF
        self.num_chunks: int = 0
        self._load_and_index_documents()

    def _tokenize(self, text: str) -> List[str]:
        """Extracts normalized alphanumeric words from text."""
        return re.findall(r'\b[a-z0-9_]{3,}\b', text.lower())

    def _load_and_index_documents(self):
        """Loads, chunks, and indexes all text documents in the docs directory."""
        if not os.path.exists(self.docs_directory):
            os.makedirs(self.docs_directory, exist_ok=True)

        doc_files = glob.glob(os.path.join(self.docs_directory, "*.txt"))
        self.chunks = []
        self.df = {}

        for filepath in doc_files:
            filename = os.path.basename(filepath)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract title and source document header
                doc_title = filename
                header_match = re.search(r"Source Document:\s*(.*)", content)
                topic_match = re.search(r"Topic:\s*(.*)", content)
                
                source_meta = header_match.group(1).strip() if header_match else "ICAR Extension Advisory"
                topic_meta = topic_match.group(1).strip() if topic_match else "General Agronomy"

                # Split content into section blocks by numbered headings (e.g., '1. ', '2. ')
                sections = re.split(r'\n(?=[0-9]+\.\s+[A-Z])', content)
                for idx, sec in enumerate(sections):
                    sec_clean = sec.strip()
                    if not sec_clean or len(sec_clean) < 40:
                        continue
                    
                    lines = sec_clean.split("\n")
                    section_name = lines[0].strip() if lines else "General Section"

                    tokens = self._tokenize(sec_clean)
                    term_freq: Dict[str, int] = {}
                    for t in tokens:
                        term_freq[t] = term_freq.get(t, 0) + 1

                    unique_tokens = set(term_freq.keys())
                    for t in unique_tokens:
                        self.df[t] = self.df.get(t, 0) + 1

                    self.chunks.append({
                        "id": f"{filename}_sec_{idx}",
                        "filename": filename,
                        "doc_title": f"{filename} — {source_meta}",
                        "source_institution": source_meta,
                        "topic": topic_meta,
                        "section_name": section_name,
                        "text": sec_clean,
                        "tokens": tokens,
                        "tf": term_freq,
                        "total_tokens": len(tokens)
                    })
            except Exception as e:
                print(f"Error loading RAG doc {filepath}: {e}")

        self.num_chunks = len(self.chunks)

    def search(self, query: str, top_k: int = 1) -> KnowledgeResult:
        """
        Performs TF-IDF vector similarity search against indexed agronomy chunks.
        """
        if not self.chunks:
            self._load_and_index_documents()

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return KnowledgeResult(
                query=query,
                answer="Please provide specific crop management or agronomic keywords (e.g. 'tomato blight', 'cotton pink bollworm', 'rice tillering').",
                source_document="AgriMind Agronomy Knowledge Base",
                relevant_section="None",
                source_metadata={"status": "empty_query"}
            )

        best_chunk = None
        best_score = 0.0

        for chunk in self.chunks:
            score = 0.0
            tf_dict = chunk["tf"]
            total_words = max(chunk["total_tokens"], 1)

            for token in query_tokens:
                if token in tf_dict:
                    # Normalized TF
                    tf = tf_dict[token] / total_words
                    # IDF
                    doc_count = self.df.get(token, 1)
                    idf = math.log((self.num_chunks + 1) / (doc_count + 0.5)) + 1.0
                    score += tf * idf

            if score > best_score:
                best_score = score
                best_chunk = chunk

        if best_chunk and best_score > 0.005:
            return KnowledgeResult(
                query=query,
                answer=best_chunk["text"],
                source_document=best_chunk["doc_title"],
                relevant_section=best_chunk["section_name"],
                source_metadata={
                    "filename": best_chunk["filename"],
                    "source_institution": best_chunk["source_institution"],
                    "topic": best_chunk["topic"],
                    "chunk_id": best_chunk["id"],
                    "similarity_score": round(best_score, 4)
                }
            )

        return KnowledgeResult(
            query=query,
            answer="No specific ICAR agricultural university advisory document was found matching your query in the local repository.",
            source_document="AgriMind Agronomy Extension Repository",
            relevant_section="Unmatched",
            source_metadata={"status": "not_found", "max_score": round(best_score, 4)}
        )

# Global store instance
knowledge_store = LocalVectorKnowledgeStore()

def search_crop_knowledge(query: str) -> KnowledgeResult:
    """Public helper for querying the local RAG knowledge store."""
    return knowledge_store.search(query)

@tool
def agricultural_knowledge_tool(query: str) -> str:
    """
    Searches official ICAR & state agricultural university agronomy extension handbooks
    for verified crop cultivation, pest management, and soil health practices.
    """
    res = search_crop_knowledge(query)
    if res.source_metadata.get("status") == "not_found":
        return res.answer
    return f"Knowledge Base [{res.source_document} - {res.relevant_section}]: {res.answer}"
