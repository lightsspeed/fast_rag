import spacy
import hashlib
import numpy as np
from typing import List, Dict, Any
from app.services.embedder import embedder
from app.services.structure_analyzer import structure_analyzer
from app.services.metadata_generator import metadata_generator

# Load English tokenizer, tagger, parser and NER
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import en_core_web_sm
    nlp = en_core_web_sm.load()

# Increase max_length for large documents (default is 1,000,000)
nlp.max_length = 2000000

CHUNK_CONFIG = {
    'max_chunk_size': 512,  # tokens
    'similarity_threshold': 0.5, # Break if distance > 0.5 (similarity < 0.5)
    'min_chunk_size': 50,
}

class ChunkerService:
    def __init__(self):
        pass

    def chunk_text(self, text: str, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        # 1. Structural Analysis
        structure = structure_analyzer.analyze(text)
        headings = {h['start']: h for h in structure['headings']}
        tables = structure['tables']
        
        # 2. Preprocessing
        # Note: We don't normalize text here to preserve structural positions
        
        # 3. Sentence Splitting
        doc = nlp(text)
        sentences = []
        for sent in doc.sents:
            if sent.text.strip():
                sentences.append({
                    "text": sent.text.strip(),
                    "start": sent.start_char,
                    "end": sent.end_char
                })
        
        if not sentences:
            return []

        # 4. Semantic Grouping & Structure-Aware Breaking
        sent_texts = [s['text'] for s in sentences]
        try:
            flat_embeddings = embedder.embed_batch(sent_texts)
        except Exception as e:
            print(f"Embedding failed during chunking: {e}")
            return self._fallback_chunking(sent_texts, metadata)
        
        chunks = []
        current_chunk_sentences = []
        current_tokens = 0
        
        for i, sent_obj in enumerate(sentences):
            sent = sent_obj['text']
            sent_start = sent_obj['start']
            sent_tokens = len(sent.split()) # Approx
            
            # Check structure-based breaking triggers
            is_heading = sent_start in headings
            is_in_table = self._is_inside_table(sent_start, tables)
            
            # Decision point for breaking
            should_break = False
            
            if current_chunk_sentences:
                # Break at headings
                if is_heading:
                    should_break = True
                
                # Semantic Check (only if not forced by heading)
                if not should_break and i < len(flat_embeddings):
                    prev_emb = flat_embeddings[i-1]
                    curr_emb = flat_embeddings[i]
                    
                    norm_prev = np.linalg.norm(prev_emb)
                    norm_curr = np.linalg.norm(curr_emb)
                    
                    similarity = np.dot(prev_emb, curr_emb) / (norm_prev * norm_curr) if norm_prev > 0 and norm_curr > 0 else 1.0
                    
                    if (similarity < CHUNK_CONFIG['similarity_threshold']):
                        # Don't break if we're inside a table
                        if not is_in_table:
                            should_break = True
                
                # Size Check
                if (current_tokens + sent_tokens > CHUNK_CONFIG['max_chunk_size']):
                    # Break unless we're in the middle of a table and it's not too giant
                    if not is_in_table or current_tokens > CHUNK_CONFIG['max_chunk_size'] * 1.5:
                        should_break = True

            if should_break and current_tokens >= CHUNK_CONFIG['min_chunk_size']:
                self._add_to_chunks(chunks, current_chunk_sentences, metadata)
                current_chunk_sentences = []
                current_tokens = 0

            current_chunk_sentences.append(sent)
            current_tokens += sent_tokens
        
        # Final
        if current_chunk_sentences:
            self._add_to_chunks(chunks, current_chunk_sentences, metadata)

        return chunks

    def _is_inside_table(self, pos: int, tables: List[Dict[str, Any]]) -> bool:
        # Tables detect line ranges, so we need to be careful. 
        # Simplified: Check content if text exists in any table block
        # Real implementation should use char offsets but StructureAnalyzer uses lines
        # For now, approximate or refine StructureAnalyzer to provide offsets
        return False # Placeholder - refined in next step or if needed

    def _fallback_chunking(self, sentences, metadata):
        chunks = []
        current = []
        curr_len = 0
        for s in sentences:
            l = len(s.split())
            if curr_len + l > 512:
                self._add_to_chunks(chunks, current, metadata)
                current = [s]
                curr_len = l
            else:
                current.append(s)
                curr_len += l
        if current:
            self._add_to_chunks(chunks, current, metadata)
        return chunks

    def _add_to_chunks(self, chunks_list, sentences, metadata):
        text = " ".join(sentences)
        chunk_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Enriched Metadata Creation
        rich_meta = metadata_generator.generate_metadata(text)
        
        meta = metadata.copy()
        meta['chunk_hash'] = chunk_hash
        meta.update(rich_meta) # Add summary, keywords, questions
        
        chunks_list.append({
            'text': text,
            'metadata': meta
        })

    def _normalize_text(self, text: str) -> str:
        return " ".join(text.split())

chunker = ChunkerService()
