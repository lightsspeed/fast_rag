import sys
import os
import asyncio

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.chunker import chunker
from app.services.structure_analyzer import structure_analyzer

def test_structure_analysis():
    print("\n--- Testing Structure Analysis ---")
    sample_text = """
# Main Title
This is some introductory text.

## Section 1: Tables
| Header 1 | Header 2 |
|----------|----------|
| Row 1, Col 1 | Row 1, Col 2 |
| Row 2, Col 1 | Row 2, Col 2 |

## Section 2: More Text
This section should be a separate chunk because of the heading.

---
This is after a horizontal rule boundary.
    """
    
    structure = structure_analyzer.analyze(sample_text)
    print(f"Headings detected: {len(structure['headings'])}")
    for h in structure['headings']:
        print(f"  - Level {h['level']}: {h['text']}")
    
    print(f"Tables detected: {len(structure['tables'])}")
    print(f"Boundaries detected: {len(structure['boundaries'])}")

def test_chunking_and_metadata():
    print("\n--- Testing Chunking and Metadata Generation ---")
    sample_text = """
# Implementation of RAG
Retrieval-Augmented Generation (RAG) is a technique for enhancing LLMs with external data.
It involves a retrieval step where relevant documents are found in a vector database.

## Architecture
The system consists of an ingestion pipeline, a vector store, and a generation interface.
The ingestion pipeline processes documents into chunks and embeddings.
    """
    
    metadata = {"source": "test_doc.md"}
    chunks = chunker.chunk_text(sample_text, metadata)
    
    print(f"Total chunks generated: {len(chunks)}")
    for i, chunk in enumerate(chunks):
        print(f"\nChunk {i+1}:")
        print(f"Text snippet: {chunk['text'][:100]}...")
        print(f"Summary: {chunk['metadata'].get('summary', 'N/A')}")
        print(f"Keywords: {chunk['metadata'].get('keywords', [])}")
        print(f"Questions: {chunk['metadata'].get('questions', [])}")

if __name__ == "__main__":
    test_structure_analysis()
    test_chunking_and_metadata()
