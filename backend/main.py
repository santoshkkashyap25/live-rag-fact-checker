import os
import logging
from typing import List, Dict, Any, Optional
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import APP_TITLE, APP_VERSION, HOST, PORT
from pipeline import run_fact_checking_pipeline
from core.metrics import metrics_collector
from core.cache import query_cache
from core.llm_service import llm_service

# --- Logging Configuration ---
logging.basicConfig(
    filename="app.log",
    filemode="a",
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Lifespan Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up: Real-Time Web Intelligence Fact Checker online")
    yield
    
    # Save cache on shutdown
    logger.info("Shutting down: Saving query cache...")
    try:
        query_cache.save_to_disk()
        logger.info("Query cache saved successfully")
    except Exception as e:
        logger.exception(f"Unexpected error saving cache: {e}")

# --- Initialize App ---
app = FastAPI(
    title=APP_TITLE,
    description="Real-time web intelligence fact-checking system with multi-provider LLM verification.",
    version=APP_VERSION,
    lifespan=lifespan
)

# --- Configure CORS ---
# In production, specify the allowed origins instead of "*"
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Pydantic Schemas ---
class VerifyRequest(BaseModel):
    text: str = Field(..., max_length=1000, description="The statement to verify")
    user_id: Optional[str] = Field(default="default_user", description="Unique client user identifier")
    llm_provider: Optional[str] = Field(default=None, description="Chosen LLM provider (groq, openai, gemini, claude)")
    llm_api_key: Optional[str] = Field(default=None, description="User BYOK API key")
    llm_model: Optional[str] = Field(default=None, description="User chosen model")

class LLMEngineInfo(BaseModel):
    provider: str
    model: str

class VerifyResponsePerformance(BaseModel):
    extraction_time: str
    retrieval_time: str
    llm_time: str
    total_time: str

class VerifyResponse(BaseModel):
    input_text: str
    extracted_claim: str
    verdict: str
    confidence: str
    reasoning: str
    evidence: List[str]
    evidence_scores: List[str]
    evidence_sources: Optional[List[str]] = Field(default_factory=list)
    evidence_urls: Optional[List[str]] = Field(default_factory=list)
    engine: Optional[LLMEngineInfo] = None
    is_cache_hit: Optional[bool] = Field(default=False, description="True if response was served from cache")
    performance: VerifyResponsePerformance

class LLMTestRequest(BaseModel):
    provider: str = Field(..., description="Provider name (groq, openai, gemini, claude)")
    api_key: str = Field(..., description="API key to test")
    model: Optional[str] = Field(default=None, description="Optional model name")

class LLMTestResponse(BaseModel):
    success: bool
    message: str

class ErrorResponse(BaseModel):
    detail: str

# --- Endpoints ---

@app.get("/")
async def root():
    return {
        "app": APP_TITLE,
        "version": APP_VERSION,
        "status": "online",
        "mode": "real_time_web_search"
    }

@app.post("/api/llm/test", response_model=LLMTestResponse)
async def test_llm_connection(req: LLMTestRequest):
    """
    Test user-provided LLM credentials with a lightweight ping.
    """
    success, message = llm_service.test_connection(
        provider=req.provider,
        api_key=req.api_key,
        model=req.model
    )
    return {"success": success, "message": message}

@app.post(
    "/api/verify", 
    response_model=VerifyResponse, 
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def verify_statement(
    request: VerifyRequest,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
    x_llm_provider: Optional[str] = Header(default=None, alias="X-LLM-Provider"),
    x_llm_api_key: Optional[str] = Header(default=None, alias="X-LLM-API-Key"),
    x_llm_model: Optional[str] = Header(default=None, alias="X-LLM-Model"),
):
    """
    Verify a statement using real-time internet search and multi-provider LLM validation.
    """
    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Statement cannot be empty"
        )
    
    user_id = x_user_id or request.user_id or "default_user"
    provider = x_llm_provider or request.llm_provider
    api_key = x_llm_api_key or request.llm_api_key
    model = x_llm_model or request.llm_model
    
    logger.info(f"API Request - Verify (user: {user_id}, provider: {provider or 'system'}): {request.text[:100]}...")
    try:
        result = run_fact_checking_pipeline(
            request.text, 
            user_id=user_id,
            llm_provider=provider,
            llm_api_key=api_key,
            llm_model=model
        )
        return result
    except ValueError as e:
        logger.error(f"Pipeline validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.exception("Unexpected error in API verify")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@app.get("/api/analytics")
async def get_analytics():
    """
    Retrieve performance statistics, verdict distributions, and real-time search telemetry.
    """
    try:
        # Re-load metrics from disk to ensure sync
        metrics_collector.load_from_disk()
        
        stats = metrics_collector.get_summary()
        cache_stats = query_cache.get_stats()
        db_stats = {
            "status": "loaded",
            "total_facts": "Live Web Index",
            "embedding_dim": 384,
            "index_type": "Real-Time Web Crawler (DuckDuckGo + Wikipedia)",
            "has_metadata": True
        }
        
        # Format metrics history for charting
        history = []
        for m in metrics_collector.metrics[-100:]:
            history.append({
                "timestamp": m.timestamp,
                "total_time": m.total_time,
                "confidence": m.confidence,
                "verdict": m.verdict
            })
            
        return {
            "summary": stats,
            "cache": cache_stats,
            "database": db_stats,
            "history": history
        }
    except Exception as e:
        logger.exception("Failed to compile analytics")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load analytics: {str(e)}"
        )

@app.post("/api/cache/clear")
async def clear_cache(
    user_id: Optional[str] = None,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID")
):
    """
    Clear cached query results for the current user, or all users if unspecified.
    """
    try:
        target_user = x_user_id or user_id
        query_cache.clear(user_id=target_user)
        query_cache.save_to_disk()
        msg = f"Cache cleared for user '{target_user}'" if target_user else "All cache cleared successfully"
        return {"status": "success", "message": msg, "user_id": target_user}
    except Exception as e:
        logger.exception("Failed to clear cache")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to clear cache: {str(e)}"
        )

@app.get("/api/examples")
async def get_examples():
    """
    Retrieve default list of example statements.
    """
    return {
        "examples": [
            "India has 28 states and 8 union territories.",
            "The Great Wall of China is visible from the Moon.",
            "Bananas are naturally radioactive due to potassium-40.",
            "Lightning never strikes the same place twice.",
            "The Digital India initiative was launched in 2015."
        ]
    }

if __name__ == "__main__":
    import uvicorn
    print(f"Starting {APP_TITLE} on http://{HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
