import logging
from typing import List, Tuple
from sentence_transformers import CrossEncoder

from config import CROSS_ENCODER_MODEL

logger = logging.getLogger(__name__)

class ReRanker:
    """Uses a CrossEncoder to re-rank documents against a query."""
    
    def __init__(self):
        self.model = None
    
    def _initialize_model(self):
        if self.model is None:
            logger.info(f"Loading CrossEncoder model: {CROSS_ENCODER_MODEL}")
            self.model = CrossEncoder(CROSS_ENCODER_MODEL, max_length=512)
            logger.info("CrossEncoder loaded successfully.")
            
    def rerank(self, query: str, documents: List[str], top_k: int) -> List[Tuple[str, float]]:
        """
        Scores the documents against the query and returns the top_k sorted.
        Returns a list of tuples (document_text, score).
        """
        if not documents:
            return []
            
        self._initialize_model()
        
        # CrossEncoder expects pairs of (query, document)
        pairs = [[query, doc] for doc in documents]
        
        # Predict scores
        logger.info(f"Re-ranking {len(documents)} documents...")
        scores = self.model.predict(pairs)
        
        # Combine docs and scores, then sort descending
        doc_score_pairs = list(zip(documents, scores))
        doc_score_pairs.sort(key=lambda x: x[1], reverse=True)
        
        # Return top K
        top_results = doc_score_pairs[:top_k]
        logger.info(f"Selected top {len(top_results)} documents after re-ranking.")
        
        return top_results

re_ranker = ReRanker()
