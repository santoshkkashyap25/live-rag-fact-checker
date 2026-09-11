# pipeline.py
import logging
import time
from typing import Dict, Any
from core.claim_extractor import claim_extractor
from core.web_search import web_search
from core.llm_service import llm_service
from core.re_ranker import re_ranker
from core.metrics import metrics_collector, PipelineMetrics
from core.cache import query_cache
from config import TOP_K_RETRIEVE, TOP_K_RERANK_RESULTS, CACHE_ENABLED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_fact_checking_pipeline(raw_text: str, use_cache: bool = True) -> Dict[str, Any]:
    """
    Enhanced Real-Time Fact-Checking Pipeline with Web Search (DuckDuckGo + Wikipedia).
    
    Args:
        raw_text: Input text to fact-check
        use_cache: Whether to use cached results
    
    Returns:
        Dictionary with verification results, real-time citations, and timing metadata
    """
    logger.info("=" * 60)
    logger.info("Fact-Checking Pipeline started (Real-Time Web Search)")
    logger.info(f"Input: {raw_text[:100]}...")
    
    start_time = time.time()
    cache_hit = False
    
    try:
        # Stage 1: Claim Extraction
        extraction_start = time.time()
        claim = claim_extractor.extract(raw_text)
        extraction_time = time.time() - extraction_start
        logger.info(f"[1/3] Claim extracted in {extraction_time:.2f}s: {claim}")
        
        # Check cache if enabled
        if use_cache and CACHE_ENABLED:
            cached = query_cache.get(claim)
            if cached:
                total_time = time.time() - start_time
                logger.info(f"Cache hit for claim '{claim}'. Returning cached result in {total_time:.3f}s")
                cached_copy = dict(cached)
                cached_copy["input_text"] = raw_text
                cached_copy["performance"] = dict(cached.get("performance", {}))
                cached_copy["performance"]["total_time"] = f"{total_time:.2f}s"
                
                # Log metric for cache hit
                metric = PipelineMetrics(
                    timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
                    claim_extraction_time=extraction_time,
                    retrieval_time=0.0,
                    llm_time=0.0,
                    total_time=total_time,
                    verdict=cached_copy.get("verdict", "Unverifiable"),
                    confidence=float(cached_copy.get("confidence", 0.0)),
                    num_evidence_retrieved=len(cached_copy.get("evidence", [])),
                    cache_hit=True,
                    input_length=len(raw_text)
                )
                metrics_collector.log_metric(metric)
                return cached_copy
        
        # Stage 2: Real-Time Web Evidence Retrieval & Re-ranking
        retrieval_start = time.time()
        
        # 2a. Search web via DuckDuckGo + Wikipedia
        web_results = web_search.search(
            query=claim,
            max_results=TOP_K_RETRIEVE
        )
        
        # Map documents for re-ranking
        candidate_docs = []
        doc_meta_map = {}
        for item in web_results:
            text = f"{item['title']}: {item['snippet']}"
            candidate_docs.append(text)
            doc_meta_map[text] = item
        
        # 2b. CrossEncoder Re-ranking
        if candidate_docs:
            reranked_results = re_ranker.rerank(
                query=claim,
                documents=candidate_docs,
                top_k=TOP_K_RERANK_RESULTS
            )
        else:
            reranked_results = []
            
        retrieval_time = time.time() - retrieval_start
        
        # Extract evidence texts, URLs, and scores
        evidence_items = []
        evidence_scores = []
        evidence_sources = []
        evidence_urls = []
        
        for text, score in reranked_results:
            meta = doc_meta_map.get(text, {})
            title = meta.get("title", "")
            snippet = meta.get("snippet", text)
            url = meta.get("url", "")
            source = meta.get("source", "Web")
            
            # Format clean evidence item
            formatted_text = f"[{title}] {snippet}" if title else snippet
            evidence_items.append(formatted_text)
            evidence_scores.append(float(score))
            evidence_sources.append(source)
            evidence_urls.append(url)
        
        logger.info(
            f"[2/3] Retrieved {len(evidence_items)} live web evidence items in {retrieval_time:.2f}s"
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
            "evidence_sources": evidence_sources,
            "evidence_urls": evidence_urls,
            "performance": {
                "extraction_time": f"{extraction_time:.2f}s",
                "retrieval_time": f"{retrieval_time:.2f}s",
                "llm_time": f"{llm_time:.2f}s",
                "total_time": f"{total_time:.2f}s"
            }
        }
        
        # Cache response for future queries
        if CACHE_ENABLED:
            query_cache.set(claim, response)

        logger.info(f"Pipeline completed in {total_time:.2f}s")
        logger.info("=" * 60)
        
        return response
        
    except Exception as e:
        logger.exception(f"Pipeline failed: {e}")
        raise
