import logging
import re
from typing import List, Tuple

from config import CROSS_ENCODER_MODEL

logger = logging.getLogger(__name__)

class ReRanker:
    """Uses a CrossEncoder to re-rank documents against a query with optimized memory footprint."""
    
    def __init__(self):
        self.model = None
        self._load_failed = False
    
    def _initialize_model(self):
        if self.model is None and not self._load_failed:
            logger.info(f"Loading CrossEncoder model: {CROSS_ENCODER_MODEL}")
            try:
                # Restrict PyTorch to single-threaded execution to prevent memory arena bloat on 512MB hosts
                import torch
                torch.set_num_threads(1)
                if hasattr(torch, "set_num_interop_threads"):
                    try:
                        torch.set_num_interop_threads(1)
                    except RuntimeError:
                        pass
                
                from sentence_transformers import CrossEncoder
                try:
                    self.model = CrossEncoder(CROSS_ENCODER_MODEL, max_length=512, local_files_only=True)
                except Exception:
                    self.model = CrossEncoder(CROSS_ENCODER_MODEL, max_length=512)
                logger.info("CrossEncoder loaded successfully.")
            except Exception as e:
                logger.warning(f"Failed to load CrossEncoder ({e}). Falling back to lexical keyword scoring.")
                self._load_failed = True
                self.model = None
            
    def rerank(self, query: str, documents: List[str], top_k: int) -> List[Tuple[str, float]]:
        """
        Scores the documents against the query and returns the top_k sorted.
        Returns a list of tuples (document_text, score).
        """
        if not documents:
            return []
            
        self._initialize_model()
        
        scores = []
        if self.model is not None:
            try:
                import torch
                # CrossEncoder expects pairs of (query, document)
                pairs = [[query, doc] for doc in documents]
                logger.info(f"Re-ranking {len(documents)} documents using CrossEncoder...")
                with torch.inference_mode():
                    scores = list(self.model.predict(pairs))
            except Exception as e:
                logger.warning(f"CrossEncoder inference encountered issue ({e}), using lexical fallback")
                scores = [self._lexical_score(query, doc) for doc in documents]
        else:
            logger.info(f"Using lightweight lexical ranking for {len(documents)} documents")
            scores = [self._lexical_score(query, doc) for doc in documents]
        
        # Combine docs and scores, then sort descending
        doc_score_pairs = list(zip(documents, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # Return top K
        top_results = doc_score_pairs[:top_k]
        logger.info(f"Selected top {len(top_results)} documents after re-ranking.")
        
        return top_results

    def _lexical_score(self, query: str, document: str) -> float:
        """Lightweight token overlap scoring without any PyTorch or GPU memory overhead."""
        q_tokens = set(re.split(r'\W+', query.lower())) - {"", "is", "a", "the", "in", "of", "and", "to", "that"}
        d_tokens = set(re.split(r'\W+', document.lower()))
        if not q_tokens:
            return 0.5
        overlap = len(q_tokens.intersection(d_tokens))
        return float(overlap / len(q_tokens))

re_ranker = ReRanker()
