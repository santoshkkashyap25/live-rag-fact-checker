# pipeline.py
import json
import logging
import time
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator

from core.claim_extractor import claim_extractor
from core.web_search import web_search
from core.llm_service import llm_service
from core.re_ranker import re_ranker
from core.metrics import metrics_collector, PipelineMetrics
from core.cache import query_cache
from core.security import sanitize_secrets, clean_api_key
from config import TOP_K_RETRIEVE, TOP_K_RERANK_RESULTS, CACHE_ENABLED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def stream_fact_checking_pipeline(
    raw_text: str,
    user_id: str = "default_user",
    use_cache: bool = True,
    llm_provider: Optional[str] = None,
    llm_api_key: Optional[str] = None,
    llm_model: Optional[str] = None
) -> AsyncGenerator[str, None]:
    """
    Enhanced Real-Time Fact-Checking Pipeline with Web Search, Re-ranking, and
    streaming progress events to the client via Server-Sent Events.
    """
    
    def emit(data: Dict[str, Any]):
        return f"data: {json.dumps(data)}\n\n"

    try:
        # Start
        start_time = time.time()
        
        # 1. Claim Extraction
        yield emit({"type": "status", "step": 1, "phase": "extracting", "message": "Analyzing linguistic structure & extracting claim..."})
        extraction_start = time.time()
        claim = await asyncio.to_thread(claim_extractor.extract, raw_text)
        extraction_time = time.time() - extraction_start
        
        # Cache Check (isolated per provider & model)
        if use_cache and CACHE_ENABLED:
            cached = query_cache.get(claim, user_id=user_id, provider=llm_provider, model=llm_model)
            if cached:
                cached_copy = dict(cached)
                cached_copy["input_text"] = raw_text
                cached_copy["is_cache_hit"] = True
                yield emit({"type": "status", "step": 4, "phase": "cached", "message": "Instant cache hit! Loading pre-verified verdict..."})
                yield emit({"type": "complete", "result": cached_copy})
                return

        # 2. Web Search
        yield emit({"type": "status", "step": 2, "phase": "searching", "message": f"Searching live internet for: '{claim}'...", "extracted_claim": claim})
        retrieval_start = time.time()
        web_results = await asyncio.to_thread(web_search.search, query=claim, max_results=TOP_K_RETRIEVE)
        
        # Reranking with Domain Trust Matrix (Moat A)
        yield emit({"type": "status", "step": 3, "phase": "reranking", "message": "Re-ranking retrieved passages with BM25Okapi + Domain Trust Matrix...", "retrieved_count": len(web_results)})
        reranked_items = await asyncio.to_thread(re_ranker.rerank_items, query=claim, items=web_results, top_k=TOP_K_RERANK_RESULTS)
        retrieval_time = time.time() - retrieval_start
        
        # Prepare LLM Input
        evidence_items = []
        evidence_scores = []
        evidence_sources = []
        evidence_urls = []
        
        for item, weighted_score in reranked_items:
            title = item.get('title', 'Web')
            snippet = item.get('snippet', '')
            trust = item.get('domain_trust', {})
            badge = trust.get('badge', item.get('source', 'Web'))
            
            if trust.get('is_satire'):
                evidence_items.append(f"[{title} | ⚠️ SATIRE SOURCE] {snippet}")
            else:
                evidence_items.append(f"[{title} | {badge}] {snippet}")

            evidence_scores.append(float(weighted_score))
            evidence_sources.append(badge)
            evidence_urls.append(item.get('url', ''))

        # 3. LLM Verdict
        provider_label = (llm_provider or "Groq").upper()
        yield emit({"type": "status", "step": 4, "phase": "reasoning", "message": f"Synthesizing factual verdict via {provider_label}...", "top_evidence_count": len(evidence_items)})
        
        llm_start = time.time()
        result = await asyncio.to_thread(
            llm_service.get_verdict,
            claim=claim,
            evidence=evidence_items,
            provider=llm_provider,
            api_key=llm_api_key,
            model=llm_model
        )
        llm_time = time.time() - llm_start
        total_time = time.time() - start_time
        
        # Assemble Final Result
        final_result = {
            "input_text": raw_text,
            "verdict": result.verdict,
            "confidence": f"{result.confidence:.2f}",
            "reasoning": result.reasoning,
            "extracted_claim": claim,
            "evidence": evidence_items,
            "evidence_scores": [f"{s:.3f}" for s in evidence_scores],
            "evidence_sources": evidence_sources,
            "evidence_urls": evidence_urls,
            "consensus_score": getattr(result, "consensus_score", 1.0),
            "disputed": getattr(result, "disputed", False),
            "numerical_variance": getattr(result, "numerical_variance", None),
            "engine": {"provider": result.provider_used or (llm_provider or "groq"), "model": result.model_used or (llm_model or "default")},
            "performance": {
                "extraction_time": f"{extraction_time:.2f}s",
                "retrieval_time": f"{retrieval_time:.2f}s",
                "llm_time": f"{llm_time:.2f}s",
                "total_time": f"{total_time:.2f}s"
            },
            "is_cache_hit": False
        }

        # Save to cache and log metrics (isolated per provider & model)
        query_cache.set(claim, final_result, user_id=user_id, provider=llm_provider, model=llm_model)
        metrics_collector.log_metric(PipelineMetrics(
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
            claim_extraction_time=extraction_time,
            retrieval_time=retrieval_time,
            llm_time=llm_time,
            total_time=total_time,
            verdict=result.verdict,
            confidence=float(result.confidence),
            num_evidence_retrieved=len(evidence_items),
            cache_hit=False,
            input_length=len(raw_text)
        ))
        
        yield emit({"type": "complete", "result": final_result})
    except Exception as e:
        sanitized_msg = sanitize_secrets(str(e), custom_keys=[llm_api_key])
        logger.exception("Error during streaming pipeline")
        yield emit({"type": "error", "message": f"Verification error: {sanitized_msg}"})

def run_fact_checking_pipeline(
    raw_text: str, 
    user_id: str = "default_user", 
    use_cache: bool = True,
    llm_provider: Optional[str] = None,
    llm_api_key: Optional[str] = None,
    llm_model: Optional[str] = None
) -> Dict[str, Any]:
    """
    Enhanced Real-Time Fact-Checking Pipeline with Web Search and Multi-Provider LLM Verification.
    
    Args:
        raw_text: Input text to fact-check
        user_id: Unique client user identifier for isolated per-user caching
        use_cache: Whether to use cached results
        llm_provider: Optional user LLM provider ('groq', 'openai', 'gemini', 'claude')
        llm_api_key: Optional user API key
        llm_model: Optional user chosen model
    
    Returns:
        Dictionary with verification results, real-time citations, timing metadata, engine used, and is_cache_hit flag
    """
    logger.info("=" * 60)
    logger.info(f"Fact-Checking Pipeline started (User: {user_id})")
    logger.info(f"Input: {raw_text[:100]}...")
    
    start_time = time.time()
    cache_hit = False
    
    try:
        # Stage 1: Claim Extraction
        extraction_start = time.time()
        claim = claim_extractor.extract(raw_text)
        extraction_time = time.time() - extraction_start
        logger.info(f"[1/3] Claim extracted in {extraction_time:.2f}s: {claim}")
        
        # Check cache if enabled (isolated per provider & model)
        if use_cache and CACHE_ENABLED:
            cached = query_cache.get(claim, user_id=user_id, provider=llm_provider, model=llm_model)
            if cached:
                total_time = time.time() - start_time
                logger.info(f"Cache hit for user '{user_id}' claim '{claim}'. Returning cached result in {total_time:.3f}s")
                cached_copy = dict(cached)
                cached_copy["input_text"] = raw_text
                cached_copy["is_cache_hit"] = True
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
        
        # 2b. Domain Trust Re-ranking (Moat A)
        if web_results:
            reranked_items = re_ranker.rerank_items(
                query=claim,
                items=web_results,
                top_k=TOP_K_RERANK_RESULTS
            )
        else:
            reranked_items = []
            
        retrieval_time = time.time() - retrieval_start
        
        # Extract evidence texts, URLs, and scores
        evidence_items = []
        evidence_scores = []
        evidence_sources = []
        evidence_urls = []
        
        for item, weighted_score in reranked_items:
            title = item.get("title", "Web")
            snippet = item.get("snippet", "")
            url = item.get("url", "")
            trust = item.get("domain_trust", {})
            badge = trust.get("badge", item.get("source", "Web"))
            
            if trust.get("is_satire"):
                formatted_text = f"[{title} | ⚠️ SATIRE SOURCE] {snippet}"
            else:
                formatted_text = f"[{title} | {badge}] {snippet}"

            evidence_items.append(formatted_text)
            evidence_scores.append(float(weighted_score))
            evidence_sources.append(badge)
            evidence_urls.append(url)
        
        logger.info(
            f"[2/3] Retrieved {len(evidence_items)} live web evidence items in {retrieval_time:.2f}s"
        )
        for i, (text, score) in enumerate(zip(evidence_items, evidence_scores)):
            logger.info(f"  {i+1}. (score: {score:.3f}) {text[:80]}...")
        
        # Stage 3: LLM Verification
        llm_start = time.time()
        verdict_obj = llm_service.get_verdict(
            claim=claim, 
            evidence=evidence_items,
            provider=llm_provider,
            api_key=llm_api_key,
            model=llm_model
        )
        llm_time = time.time() - llm_start
        
        logger.info(f"[3/3] Verdict generated in {llm_time:.2f}s [{verdict_obj.provider_used}/{verdict_obj.model_used}]")
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
            "consensus_score": getattr(verdict_obj, "consensus_score", 1.0),
            "disputed": getattr(verdict_obj, "disputed", False),
            "numerical_variance": getattr(verdict_obj, "numerical_variance", None),
            "engine": {
                "provider": verdict_obj.provider_used or "groq",
                "model": verdict_obj.model_used or "default"
            },
            "is_cache_hit": False,
            "performance": {
                "extraction_time": f"{extraction_time:.2f}s",
                "retrieval_time": f"{retrieval_time:.2f}s",
                "llm_time": f"{llm_time:.2f}s",
                "total_time": f"{total_time:.2f}s"
            }
        }
        
        # Cache response for future queries (per user, provider & model)
        if CACHE_ENABLED:
            query_cache.set(claim, response, user_id=user_id, provider=llm_provider, model=llm_model)

        logger.info(f"Pipeline completed in {total_time:.2f}s")
        logger.info("=" * 60)
        
        return response
        
    except Exception as e:
        sanitized_err = sanitize_secrets(str(e), custom_keys=[llm_api_key])
        logger.exception(f"Pipeline failed: {sanitized_err}")
        raise
