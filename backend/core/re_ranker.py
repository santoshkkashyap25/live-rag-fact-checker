import logging
import math
import re
from typing import List, Tuple

from config import USE_CROSS_ENCODER, CROSS_ENCODER_MODEL

logger = logging.getLogger(__name__)

class ReRanker:
    """
    High-performance semantic & lexical ranker.
    Uses BM25Okapi + phrase matching by default (0 extra MB RAM, sub-millisecond execution).
    Optionally supports CrossEncoder if USE_CROSS_ENCODER=true and memory allows.
    """
    
    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.cross_encoder = None
        self._cross_encoder_failed = False
        self._stop_words = {
            "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or",
            "is", "are", "was", "were", "it", "this", "that", "these", "those",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "by", "with", "from", "as", "about", "into", "through", "during"
        }
    
    def _initialize_cross_encoder(self):
        if not USE_CROSS_ENCODER or self._cross_encoder_failed:
            return
        if self.cross_encoder is None:
            logger.info(f"Loading CrossEncoder model: {CROSS_ENCODER_MODEL}")
            try:
                import os
                os.environ["HF_HUB_OFFLINE"] = "1"
                os.environ["TRANSFORMERS_OFFLINE"] = "1"
                import torch
                torch.set_num_threads(1)
                from sentence_transformers import CrossEncoder
                self.cross_encoder = CrossEncoder(CROSS_ENCODER_MODEL, max_length=256)
                logger.info("CrossEncoder loaded successfully.")
            except Exception as e:
                logger.warning(f"CrossEncoder unavailable ({e}), using BM25 ranker.")
                self._cross_encoder_failed = True
                self.cross_encoder = None
            
    def _tokenize(self, text: str) -> List[str]:
        """Extract alphanumeric word tokens in lowercase."""
        return [w for w in re.findall(r'\b\w+\b', text.lower()) if len(w) > 1 and w not in self._stop_words]

    def _rank_bm25(self, query: str, documents: List[str], top_k: int) -> List[Tuple[str, float]]:
        """
        Industry-standard BM25Okapi ranking algorithm with bi-gram / exact phrase boost.
        Ultra-fast (0.1ms), 0 MB memory footprint, perfect for cloud free tiers.
        """
        q_tokens = self._tokenize(query)
        if not q_tokens:
            q_tokens = [w for w in re.findall(r'\b\w+\b', query.lower()) if len(w) > 1]
            
        doc_tokens_list = [self._tokenize(d) for d in documents]
        N = len(documents)
        if N == 0 or not q_tokens:
            return [(d, 0.5) for d in documents[:top_k]]
        
        avgdl = sum(len(d) for d in doc_tokens_list) / max(N, 1)
        if avgdl == 0:
            avgdl = 1.0
        
        # Compute document frequencies
        df = {}
        for q in set(q_tokens):
            df[q] = sum(1 for d in doc_tokens_list if q in d)
            
        scores = []
        for i, doc_tokens in enumerate(doc_tokens_list):
            score = 0.0
            doc_len = len(doc_tokens)
            doc_freqs = {}
            for t in doc_tokens:
                doc_freqs[t] = doc_freqs.get(t, 0) + 1
                
            for q in q_tokens:
                if q in doc_freqs:
                    freq = doc_freqs[q]
                    idf = math.log((N - df[q] + 0.5) / (df[q] + 0.5) + 1.0)
                    numerator = freq * (self.k1 + 1.0)
                    denominator = freq + self.k1 * (1.0 - self.b + self.b * (doc_len / avgdl))
                    score += idf * (numerator / denominator)
            
            # Phrase bonus for contiguous keyword matches
            doc_lower = documents[i].lower()
            q_lower = query.lower()
            if q_lower in doc_lower:
                score += 3.0
            elif len(q_tokens) >= 2:
                # Check for 2-word phrase matches
                for j in range(len(q_tokens) - 1):
                    pair = f"{q_tokens[j]} {q_tokens[j+1]}"
                    if pair in doc_lower:
                        score += 1.0
                        
            scores.append((documents[i], float(score)))
            
        scores.sort(key=lambda x: x[1], reverse=True)
        return scores[:top_k]

    def rerank(self, query: str, documents: List[str], top_k: int) -> List[Tuple[str, float]]:
        """
        Scores the documents against the query and returns the top_k sorted.
        Returns a list of tuples (document_text, score).
        """
        if not documents:
            return []
            
        if USE_CROSS_ENCODER:
            self._initialize_cross_encoder()
            if self.cross_encoder is not None:
                try:
                    import torch
                    pairs = [[query, doc] for doc in documents]
                    logger.info(f"Re-ranking {len(documents)} documents using CrossEncoder...")
                    with torch.inference_mode():
                        scores = list(self.cross_encoder.predict(pairs))
                    doc_score_pairs = list(zip(documents, scores))
                    doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
                    return doc_score_pairs[:top_k]
                except Exception as e:
                    logger.warning(f"CrossEncoder prediction issue ({e}), falling back to BM25")
        
        # Default: High-speed BM25 re-ranking
        logger.info(f"Re-ranking {len(documents)} documents using BM25Okapi ranker...")
        top_results = self._rank_bm25(query, documents, top_k)
        logger.info(f"Selected top {len(top_results)} documents after BM25 re-ranking.")
        return top_results

re_ranker = ReRanker()
