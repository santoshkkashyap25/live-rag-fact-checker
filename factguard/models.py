# factguard/models.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class FactCheckResult(BaseModel):
    """Structured fact-checking result returned by FactGuard"""
    input_text: str = Field(description="Original input statement")
    extracted_claim: str = Field(description="Isolated atomic claim proposition")
    verdict: str = Field(description="'True', 'False', or 'Unverifiable'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Detailed explanation with evidence citations")
    evidence: List[str] = Field(default_factory=list, description="Top re-ranked retrieved evidence snippets")
    evidence_scores: List[str] = Field(default_factory=list, description="Relevance scores from BM25 ranker")
    evidence_sources: List[str] = Field(default_factory=list, description="Source domains / providers (e.g. Wikipedia)")
    evidence_urls: List[str] = Field(default_factory=list, description="Direct clickable source URLs")
    engine: Dict[str, str] = Field(default_factory=dict, description="LLM provider and model used")
    performance: Dict[str, str] = Field(default_factory=dict, description="Pipeline latency breakdown")
    is_cache_hit: bool = Field(default=False, description="Whether served instantly from query cache")
    share_url: Optional[str] = Field(default=None, description="Shareable permalink URL if published")
