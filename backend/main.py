import os
import time
import asyncio
import logging
import threading
from typing import List, Dict, Any, Optional, Tuple
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import StreamingResponse, HTMLResponse, Response
from pydantic import BaseModel, Field

from config import APP_TITLE, APP_VERSION, HOST, PORT
from pipeline import run_fact_checking_pipeline, stream_fact_checking_pipeline
from core.metrics import metrics_collector
from core.cache import query_cache
from core.llm_service import llm_service
from core.share_store import share_store
from core.og_renderer import render_og_svg, render_shared_page_html
from core.visitor_tracker import visitor_tracker
from core.security import sanitize_secrets, clean_api_key

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
    
    # Save cache and visitor metrics on shutdown
    logger.info("Shutting down: Saving query cache and visitor metrics...")
    try:
        query_cache.save_to_disk()
        visitor_tracker.save_to_disk()
        logger.info("Query cache and visitor metrics saved successfully")
    except Exception as e:
        logger.exception(f"Unexpected error saving cache/metrics: {e}")

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
    use_cache: Optional[bool] = Field(default=True, description="Whether to check and return cached verification results")
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

class ShareRequest(BaseModel):
    result: Dict[str, Any]

class ShareResponse(BaseModel):
    id: str
    url: str
    full_url: str

class VisitTelemetryRequest(BaseModel):
    path: Optional[str] = Field(default="/", description="Current URL path visited")
    referrer: Optional[str] = Field(default=None, description="Document referrer URL")

def _get_client_telemetry(http_req: Request) -> Tuple[str, Optional[str]]:
    """Extract authentic client IP and referrer safely from request headers against spoofing."""
    cf_ip = http_req.headers.get("CF-Connecting-IP")
    true_ip = http_req.headers.get("True-Client-IP")
    forwarded = http_req.headers.get("X-Forwarded-For")
    
    if cf_ip and cf_ip.strip():
        client_ip = cf_ip.strip()
    elif true_ip and true_ip.strip():
        client_ip = true_ip.strip()
    elif forwarded and forwarded.strip():
        # Taking rightmost trusted hop added by upstream reverse proxy to prevent client-spoofing
        parts = [p.strip() for p in forwarded.split(",") if p.strip()]
        client_ip = parts[-1] if parts else (http_req.client.host if http_req.client else "unknown")
    else:
        client_ip = http_req.client.host if http_req.client else "unknown"

    referrer = http_req.headers.get("referer") or http_req.headers.get("referrer")
    return client_ip, referrer

# --- Demo Traffic Armor: In-Memory IP Rate Limiter ---
RATE_LIMIT_MAX_REQUESTS = 12  # Max 12 requests
RATE_LIMIT_WINDOW_SECONDS = 60  # per 60 seconds per IP
client_request_history: Dict[str, List[float]] = {}
client_history_lock = threading.Lock()

def check_ip_rate_limit(client_ip: str, byok: bool = False) -> Tuple[bool, int]:
    """
    Check if IP has exceeded demo request budget.
    BYOK (users providing custom API keys) and local tests are 100% exempt from rate limits.
    Returns (is_allowed, remaining_requests).
    """
    if byok or client_ip in ("127.0.0.1", "testclient", "localhost", "::1"):
        return True, RATE_LIMIT_MAX_REQUESTS
    
    now = time.time()
    with client_history_lock:
        history = [t for t in client_request_history.get(client_ip, []) if now - t < RATE_LIMIT_WINDOW_SECONDS]
        if len(history) >= RATE_LIMIT_MAX_REQUESTS:
            client_request_history[client_ip] = history
            return False, 0
        history.append(now)
        client_request_history[client_ip] = history
        return True, RATE_LIMIT_MAX_REQUESTS - len(history)

# --- Endpoints ---

@app.api_route("/health", methods=["GET", "HEAD"])
@app.api_route("/api/health", methods=["GET", "HEAD"])
async def health_check():
    return {
        "status": "healthy",
        "app": APP_TITLE,
        "version": APP_VERSION
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

@app.get("/api/llm/ollama/models")
async def get_ollama_models(url: Optional[str] = None):
    """
    Query local or remote Ollama instance for installed models.
    """
    import requests
    target_url = (url or "").strip() or "http://127.0.0.1:11434"
    if not target_url.startswith("http://") and not target_url.startswith("https://"):
        target_url = f"http://{target_url}"
    target_url = target_url.rstrip("/")
    try:
        res = await asyncio.to_thread(requests.get, f"{target_url}/api/tags", timeout=4)
        if res.status_code == 200:
            models = [m.get("name") for m in res.json().get("models", [])]
            return {"status": "online", "url": target_url, "models": models}
        return {"status": "error", "url": target_url, "models": []}
    except Exception:
        return {"status": "offline", "url": target_url, "models": []}

@app.post("/api/telemetry/visit")
async def record_visit(http_req: Request, payload: Optional[VisitTelemetryRequest] = None):
    """
    Record privacy-preserving pageview telemetry from web or client navigation.
    """
    try:
        client_ip, ref_header = _get_client_telemetry(http_req)
        path = payload.path if (payload and payload.path) else "/"
        referrer = (payload.referrer if (payload and payload.referrer) else None) or ref_header
        visitor_tracker.log_pageview(client_ip, path=path, referrer=referrer)
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Error logging visit: {e}")
        return {"status": "error", "detail": str(e)}

@app.post("/api/verify/stream")
async def verify_statement_stream(
    http_req: Request,
    request: VerifyRequest,
    x_user_id: Optional[str] = Header(default=None, alias="X-User-ID"),
    x_llm_provider: Optional[str] = Header(default=None, alias="X-LLM-Provider"),
    x_llm_api_key: Optional[str] = Header(default=None, alias="X-LLM-API-Key"),
    x_llm_model: Optional[str] = Header(default=None, alias="X-LLM-Model"),
):
    """
    Verify a statement with real-time Server-Sent Events (SSE) progress streaming.
    """
    if not request.text.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Statement cannot be empty"
        )
    
    user_id = x_user_id or request.user_id or "default_user"
    provider = x_llm_provider or request.llm_provider
    api_key = clean_api_key(x_llm_api_key or request.llm_api_key)
    model = x_llm_model or request.llm_model

    # Check Demo IP Rate Limiting (BYOK custom keys are exempt)
    client_ip, _ = _get_client_telemetry(http_req)
    allowed, remaining = check_ip_rate_limit(client_ip, byok=bool(api_key))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Public demo rate limit reached (12 requests/min). Please add your free Groq API key in LLM Settings for unlimited verifications."
        )
    
    # Track verification in visitor telemetry (anonymized, zero claim text stored)
    visitor_tracker.log_verification(client_ip)
    
    logger.info(f"API Stream Request - Verify (user: {user_id}, provider: {provider or 'system'}): {request.text[:100]}...")
    
    return StreamingResponse(
        stream_fact_checking_pipeline(
            raw_text=request.text,
            user_id=user_id,
            use_cache=request.use_cache,
            llm_provider=provider,
            llm_api_key=api_key,
            llm_model=model
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )

@app.post(
    "/api/verify", 
    response_model=VerifyResponse, 
    responses={
        400: {"model": ErrorResponse},
        429: {"model": ErrorResponse},
        500: {"model": ErrorResponse}
    }
)
async def verify_statement(
    http_req: Request,
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
    api_key = clean_api_key(x_llm_api_key or request.llm_api_key)
    model = x_llm_model or request.llm_model

    # Check Demo IP Rate Limiting (BYOK custom keys are exempt)
    client_ip, _ = _get_client_telemetry(http_req)
    allowed, remaining = check_ip_rate_limit(client_ip, byok=bool(api_key))
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Public demo rate limit reached (12 requests/min). Please add your free Groq API key in LLM Settings for unlimited verifications."
        )
    
    # Track verification in visitor telemetry (anonymized, zero claim text stored)
    visitor_tracker.log_verification(client_ip)
    
    logger.info(f"API Request - Verify (user: {user_id}, provider: {provider or 'system'}): {request.text[:100]}...")
    try:
        result = await asyncio.to_thread(
            run_fact_checking_pipeline,
            request.text, 
            user_id=user_id,
            use_cache=request.use_cache,
            llm_provider=provider,
            llm_api_key=api_key,
            llm_model=model
        )
        return result
    except ValueError as e:
        clean_err = sanitize_secrets(str(e), custom_keys=[api_key])
        logger.error(f"Pipeline validation error: {clean_err}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=clean_err
        )
    except Exception as e:
        clean_err = sanitize_secrets(str(e), custom_keys=[api_key])
        logger.exception("Unexpected error in API verify")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {clean_err}"
        )

@app.get("/api/analytics")
async def get_analytics():
    """
    Retrieve performance statistics, verdict distributions, real-time search telemetry,
    and privacy-preserving visitor analytics.
    """
    try:
        # Re-load metrics and visitor telemetry from disk to ensure sync
        metrics_collector.load_from_disk()
        visitor_tracker.load_from_disk()
        
        stats = metrics_collector.get_summary()
        visitor_stats = visitor_tracker.get_summary()
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
            "visitors": visitor_stats,
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

# --- Social Sharing & OpenGraph Endpoints ---

@app.post("/api/share", response_model=ShareResponse)
async def create_shareable_verdict(req: ShareRequest):
    """
    Store a fact-checking verdict and generate a shareable short URL.
    """
    if not req.result:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Result payload required"
        )
    short_id = share_store.save_verdict(req.result)
    return {
        "id": short_id,
        "url": f"/v/{short_id}",
        "full_url": f"https://factguard-1gge.onrender.com/v/{short_id}"
    }

@app.get("/api/share/{share_id}")
async def get_shared_verdict(share_id: str):
    """
    Retrieve stored verdict data for client-side hydration.
    """
    item = share_store.get_verdict(share_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Shared verdict not found"
        )
    return item

@app.get("/api/og/{share_id}.svg")
async def get_og_card_svg(share_id: str):
    """
    Dynamic SVG OpenGraph image banner for social preview unfurling.
    """
    clean_id = share_id.replace(".svg", "").strip()
    item = share_store.get_verdict(clean_id)
    if not item:
        item = {
            "verdict": "FactGuard",
            "extracted_claim": "Real-Time AI Fact Checker",
            "confidence": 1.0,
            "evidence": []
        }
    svg_content = render_og_svg(item)
    return Response(
        content=svg_content, 
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=86400"}
    )

@app.get("/v/{share_id}", response_class=HTMLResponse)
async def view_shared_verdict(http_req: Request, share_id: str):
    """
    Server-rendered public landing page with OpenGraph & Twitter Card tags.
    """
    # Track pageview in visitor telemetry
    client_ip, referrer = _get_client_telemetry(http_req)
    visitor_tracker.log_pageview(client_ip, path=f"/v/{share_id}", referrer=referrer)

    item = share_store.get_verdict(share_id)
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="Shared verdict not found or expired"
        )
    html_content = render_shared_page_html(item, share_id)
    return HTMLResponse(content=html_content)

# --- Static File Serving (Unified Next.js Frontend) ---
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")
else:
    @app.api_route("/", methods=["GET", "HEAD"])
    async def root(http_req: Request):
        client_ip, referrer = _get_client_telemetry(http_req)
        visitor_tracker.log_pageview(client_ip, path="/", referrer=referrer)
        return {
            "app": APP_TITLE,
            "version": APP_VERSION,
            "status": "online",
            "mode": "api_only"
        }

if __name__ == "__main__":
    import uvicorn
    print(f"Starting {APP_TITLE} on http://{HOST}:{PORT}")
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
