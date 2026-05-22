# core/vector_db.py
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import pandas as pd
from typing import List, Tuple, Dict, Any, Optional
import logging
import pickle
from rank_bm25 import BM25Okapi
from config import (
    EMBEDDING_MODEL, VECTOR_INDEX_PATH, 
    FACTS_CSV_PATH, DATA_DIR, BM25_INDEX_PATH,
    TOP_K_RETRIEVE
)

logger = logging.getLogger(__name__)

class VectorDB:
    """Enhanced FAISS vector database with metadata support"""
    
    def __init__(self):
        self.embedding_model = None
        self.embedding_dim = None
        self.index = None
        self.bm25 = None
        self.facts = []
        self.metadata = []
        self.index_path = VECTOR_INDEX_PATH
        self.bm25_path = BM25_INDEX_PATH
    
    def _initialize_model(self):
        """Lazy load embedding model"""
        if self.embedding_model is None:
            logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
            self.embedding_model = SentenceTransformer(EMBEDDING_MODEL)
            self.embedding_dim = self.embedding_model.get_sentence_embedding_dimension()
            logger.info(f"Model loaded. Dimension: {self.embedding_dim}")
    
    def load(self):
        """Load FAISS index and facts from disk"""
        if not self.index_path.exists():
            raise FileNotFoundError(
                f"Vector index not found at {self.index_path}. "
                f"Please run 'python build_database.py' first."
            )
        
        self._initialize_model()
        
        try:
            self.index = faiss.read_index(str(self.index_path))
            
            # Load facts and metadata
            df = pd.read_csv(FACTS_CSV_PATH)
            self.facts = df["statement"].tolist()
            self.metadata = df.to_dict('records') if len(df.columns) > 1 else None
            
            try:
                with open(self.bm25_path, 'rb') as f:
                    self.bm25 = pickle.load(f)
                logger.info("BM25 index loaded.")
            except FileNotFoundError:
                logger.warning("BM25 index not found. Please rebuild database.")
                self.bm25 = None
                
            logger.info(f"VectorDB loaded: {len(self.facts)} facts indexed")
            
        except Exception as e:
            logger.error(f"Error loading vector DB: {e}")
            raise
    
    def build_and_save(self, facts: List[str], metadata: Optional[List[Dict]] = None):
        """Build FAISS index from facts and save to disk"""
        self._initialize_model()
        
        logger.info(f"Building index for {len(facts)} facts...")
        
        # Generate embeddings with progress
        fact_embeddings = self.embedding_model.encode(
            facts,
            convert_to_numpy=True,
            show_progress_bar=True,
            batch_size=32
        )
        
        # Create FAISS index
        self.index = faiss.IndexFlatL2(self.embedding_dim)
        self.index = faiss.IndexIDMap(self.index)
        
        # Add vectors with IDs
        ids = np.arange(len(facts))
        self.index.add_with_ids(fact_embeddings.astype('float32'), ids)
        
        # Save index
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        
        # Build and Save BM25 Index
        logger.info("Building BM25 index...")
        tokenized_facts = [f.lower().split() for f in facts]
        self.bm25 = BM25Okapi(tokenized_facts)
        with open(self.bm25_path, 'wb') as f:
            pickle.dump(self.bm25, f)
        
        self.facts = facts
        self.metadata = metadata
        
        logger.info(f"✓ Index built and saved to {self.index_path}")
        logger.info(f"  - Total facts: {len(facts)}")
        logger.info(f"  - Dimension: {self.embedding_dim}")
        logger.info(f"  - Index type: {type(self.index).__name__}")
    
    def search(
        self,
        query: str,
        k: int = TOP_K_RETRIEVE,
    ) -> List[str]:
        """
        Hybrid Search: Retrieve top K from FAISS and top K from BM25.
        Returns: A unique list of retrieved facts.
        """
        if self.index is None:
            self.load()
            
        k = min(k, len(self.facts))
        retrieved_facts = set()
        
        # 1. FAISS Search
        query_embedding = self.embedding_model.encode([query])
        distances, indices = self.index.search(
            query_embedding.astype('float32'), k
        )
        
        for i in indices[0]:
            if i != -1:
                retrieved_facts.add(self.facts[i])
        
        # 2. BM25 Search
        if self.bm25 is not None:
            tokenized_query = query.lower().split()
            bm25_scores = self.bm25.get_scores(tokenized_query)
            top_bm25_indices = bm25_scores.argsort()[::-1][:k]
            
            for i in top_bm25_indices:
                if bm25_scores[i] > 0: # Only if it actually matched
                    retrieved_facts.add(self.facts[i])
        
        logger.info(f"Retrieved {len(retrieved_facts)} unique facts via Hybrid Search")
        return list(retrieved_facts)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics"""
        if self.index is None:
            return {'status': 'not_loaded'}
        
        return {
            'status': 'loaded',
            'total_facts': len(self.facts),
            'embedding_dim': self.embedding_dim,
            'index_type': type(self.index).__name__,
            'has_metadata': self.metadata is not None
        }

vector_db = VectorDB()
