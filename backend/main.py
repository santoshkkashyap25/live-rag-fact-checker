import os
import logging
from typing import List, Dict, Any
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import APP_TITLE, APP_VERSION
from pipeline import run_fact_checking_pipeline
from core.metrics import metrics_collector
from core.cache import query_cache
from core.vector_db import vector_db

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
    # Load database on startup
    logger.info("Starting up: Loading vector database...")
    try:
        vector_db.load()
        logger.info("Vector database loaded successfully during startup")
    except FileNotFoundError:
        logger.error("Database files not found on startup. Please build database first.")
    except Exception as e:
        logger.exception(f"Unexpected error loading database on startup: {e}")
    
    yield
    
    # Save cache on shutdown
    logger.info("Shutting down: Saving query cache...")
    try:
        query_cache.save_to_disk()
        logger.info("Query cache saved successfully")
    except Exception as e:
        logger.exception(f"Unexpected error saving cache: {e}")

# --- Initialize FastAPI App ---
app = FastAPI(
    title=APP_TITLE,
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
    performance: VerifyResponsePerformance

class ErrorResponse(BaseModel):
    detail: str

# --- Endpoints ---

@app.get("/")
async def root():
    return {
        "app": APP_TITLE,
        "version": APP_VERSION,
        "status": "online"
    }

@app.post(
    "/api/verify", 
    response_model=VerifyResponse, 
    responses={
        400: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def verify_statement(request: VerifyRequest):
    """
    Verify a statement against the trusted fact database.
    """
    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Statement cannot be empty"
        )
    
    logger.info(f"API Request - Verify: {request.text[:100]}...")
    try:
        result = run_fact_checking_pipeline(request.text)
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
    Retrieve performance statistics, verdict distributions, database size, and cache metrics.
    """
    try:
        # Re-load metrics from disk to ensure sync
        metrics_collector.metrics = []
        metrics_collector.load_from_disk()
        
        stats = metrics_collector.get_summary()
        cache_stats = query_cache.get_stats()
        db_stats = vector_db.get_stats()
        
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
async def clear_cache():
    """
    Clear all cached query results.
    """
    try:
        query_cache.clear()
        query_cache.save_to_disk()
        return {"status": "success", "message": "Cache cleared successfully"}
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
            "India met 241 GW peak power demand on 9th June 2025 with zero shortage.",
            "The Ayushman Bharat Pradhan Mantri Jan Arogya Yojana provides health insurance coverage of up to ₹5 lakh per family per year.",
            "IREDA was granted Navratna status by the Government of India.",
            "India has 28 states and 8 union territories.",
            "The Digital India initiative was launched in 2015."
        ]
    }
