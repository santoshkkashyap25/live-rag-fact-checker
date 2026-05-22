# pipeline.py
import logging
import time
from typing import Dict, Any
from core.claim_extractor import claim_extractor
from core.vector_db import vector_db
from core.llm_service import llm_service
from core.re_ranker import re_ranker
from core.metrics import metrics_collector, PipelineMetrics
from config import TOP_K_RETRIEVE, TOP_K_RERANK_RESULTS

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_fact_checking_pipeline(raw_text: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Enhanced RAG pipeline with timing and metrics collection.
    
    Args:
        raw_text: Input text to fact-check
        use_cache: Whether to use cached results
    
    Returns:
        Dictionary with verification results and metadata
    """
    logger.info("=" * 60)
    logger.info("Pipeline started")
    logger.info(f"Input: {raw_text[:100]}...")
    
    start_time = time.time()
    cache_hit = False
    
    try:
        # Stage 1: Claim Extraction
        extraction_start = time.time()
        claim = claim_extractor.extract(raw_text)
        extraction_time = time.time() - extraction_start
        logger.info(f"[1/3] Claim extracted in {extraction_time:.2f}s: {claim}")
        
        # Stage 2: Evidence Retrieval & Re-ranking
        retrieval_start = time.time()
        
        # 2a. Hybrid Search Retrieval (FAISS + BM25)
        retrieved_docs = vector_db.search(
            query=claim,
            k=TOP_K_RETRIEVE
        )
        
        # 2b. CrossEncoder Re-ranking
        reranked_results = re_ranker.rerank(
            query=claim,
            documents=retrieved_docs,
            top_k=TOP_K_RERANK_RESULTS
        )
        retrieval_time = time.time() - retrieval_start
        
        # Extract evidence texts and scores
        evidence_items = [item[0] for item in reranked_results]
        evidence_scores = [float(item[1]) for item in reranked_results]
        
        logger.info(
            f"[2/3] Retrieved {len(evidence_items)} evidence items in {retrieval_time:.2f}s"
        )
        for i, (text, score) in enumerate(zip(evidence_items, evidence_scores)):
            logger.info(f"  {i+1}. (score: {score:.3f}) {text[:80]}...")
        
        # Stage 3: LLM Verification
        llm_start = time.time()
        verdict_obj = llm_service.get_verdict(claim, evidence_items)
        llm_time = time.time() - llm_start
        
        logger.info(f"[3/3] Verdict generated in {llm_time:.2f}s")
        logger.info(f"  Verdict: {verdict_obj.verdict}")
        logger.info(f"  Confidence: {verdict_obj.confidence:.2f}")
        
        # Calculate total time
        total_time = time.time() - start_time
        
        # Collect metrics
        metric = PipelineMetrics(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            claim_extraction_time=extraction_time,
            retrieval_time=retrieval_time,
            llm_time=llm_time,
            total_time=total_time,
            verdict=verdict_obj.verdict,
            confidence=verdict_obj.confidence,
            num_evidence_retrieved=len(evidence_items),
            cache_hit=cache_hit,
            input_length=len(raw_text)
        )
        metrics_collector.log_metric(metric)
        
        # Assemble response
        response = {
            "input_text": raw_text,
            "extracted_claim": claim,
            "verdict": verdict_obj.verdict,
            "confidence": f"{verdict_obj.confidence:.2f}",
            "reasoning": verdict_obj.reasoning,
            "evidence": evidence_items,
            "evidence_scores": [f"{score:.3f}" for score in evidence_scores],
            "performance": {
                "extraction_time": f"{extraction_time:.2f}s",
                "retrieval_time": f"{retrieval_time:.2f}s",
                "llm_time": f"{llm_time:.2f}s",
                "total_time": f"{total_time:.2f}s"
            }
        }
        
        logger.info(f"Pipeline completed in {total_time:.2f}s")
        logger.info("=" * 60)
        
        return response
        
    except FileNotFoundError as e:
        logger.error(f"Database not initialized: {e}")
        raise ValueError(
            "Vector database not found. Please run 'python build_database.py' first."
        )
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        raise
