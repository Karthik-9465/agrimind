import os
import glob
import re
from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from app.modules.agent.schemas import KnowledgeResult

DOCS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "vector_store", "docs"))

class LocalVectorKnowledgeStore:
    """
    Local agronomy document chunking and retrieval engine for academic RAG demonstration.
    Preserves document name, section headers, and source metadata.
    """

    def __init__(self, docs_directory: str = DOCS_DIR):
        self.docs_directory = docs_directory
        self.chunks: List[Dict[str, Any]] = []
        self._load_and_index_documents()

    def _load_and_index_documents(self):
        """Loads and splits text files into section-based chunks with metadata."""
        if not os.path.exists(self.docs_directory):
            os.makedirs(self.docs_directory, exist_ok=True)

        doc_files = glob.glob(os.path.join(self.docs_directory, "*.txt"))
        self.chunks = []

        for filepath in doc_files:
            filename = os.path.basename(filepath)
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract document header source if available
                doc_title = filename
                header_match = re.search(r"Source Document:\s*(.*)", content)
                if header_match:
                    doc_title = f"{filename} ({header_match.group(1).strip()})"

                # Split content into section blocks
                sections = re.split(r'\n(?=[0-9]+\.\s+[A-Z])', content)
                for idx, sec in enumerate(sections):
                    sec_clean = sec.strip()
                    if not sec_clean:
                        continue
                    
                    lines = sec_clean.split("\n")
                    section_name = lines[0] if lines else "General Section"

                    self.chunks.append({
                        "id": f"{filename}_sec_{idx}",
                        "filename": filename,
                        "doc_title": doc_title,
                        "section_name": section_name,
                        "text": sec_clean,
                        "lower_text": sec_clean.lower()
                    })
            except Exception as e:
                print(f"Error loading RAG doc {filepath}: {e}")

    def search(self, query: str) -> KnowledgeResult:
        """Searches indexed document chunks for relevant query terms."""
        if not self.chunks:
            self._load_and_index_documents()

        query_clean = query.lower().strip()
        query_words = set(re.findall(r'\b\w+\b', query_clean))

        best_chunk = None
        best_score = 0

        for chunk in self.chunks:
            # Calculate match score based on keyword frequency
            matches = sum(1 for word in query_words if word in chunk["lower_text"])
            if matches > best_score:
                best_score = matches
                best_chunk = chunk

        if best_chunk and best_score > 0:
            return KnowledgeResult(
                query=query,
                answer=best_chunk["text"],
                source_document=best_chunk["doc_title"],
                relevant_section=best_chunk["section_name"],
                source_metadata={
                    "filename": best_chunk["filename"],
                    "chunk_id": best_chunk["id"],
                    "match_score": best_score
                }
            )

        return KnowledgeResult(
            query=query,
            answer="No relevant agronomic advisory document found in the local knowledge base matching your specific query.",
            source_document="Agrimind Knowledge Base",
            relevant_section="None",
            source_metadata={"status": "not_found"}
        )

# Global store instance
knowledge_store = LocalVectorKnowledgeStore()

def search_crop_knowledge(query: str) -> KnowledgeResult:
    """Public helper for querying the local RAG knowledge store."""
    return knowledge_store.search(query)

@tool
def knowledge_tool(query: str) -> str:
    """Searches official agronomy advisory documents and returns relevant cultivation guidance with source metadata."""
    res = search_crop_knowledge(query)
    if res.source_metadata.get("status") == "not_found":
        return res.answer
    return f"Knowledge Base [{res.source_document} - {res.relevant_section}]: {res.answer}"
