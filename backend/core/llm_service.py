# core/llm_service.py
import os
import logging
import re
from typing import List, Tuple, Optional
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from groq import Groq
import json
from dotenv import load_dotenv
from config import GROQ_MODEL
from core.cache import query_cache

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Verdict(BaseModel):
    verdict: str = Field(description="Must be exactly: 'True', 'False', or 'Unverifiable'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Detailed explanation with evidence citations")

class LLMService:
    """Enhanced LLM service with caching and better prompting"""
    
    def __init__(self):
        load_dotenv()
        self.client = None
        self.prompt = self._create_enhanced_prompt()
        logger.info("LLM service initialized (client will be lazy-loaded on request)")

    def _initialize_client(self):
        load_dotenv(override=True)
        api_key = os.environ.get("GROQ_API_KEY", "").strip()
        if not api_key:
            raise ValueError(
                "Groq API key not found. "
                "Set GROQ_API_KEY in backend/.env to enable automated LLM verification."
            )
        if self.client is None or getattr(self, "_last_api_key", None) != api_key:
            logger.info("Initializing Groq LLM client...")
            self.client = Groq(api_key=api_key)
            self._last_api_key = api_key
    
    def _create_enhanced_prompt(self) -> str:
        """Create enhanced prompt with few-shot examples"""
        template = """You are a precise fact-checking AI. Analyze claims against evidence strictly.

RULES:
1. 'True' - Evidence explicitly confirms ALL key facts in the claim
2. 'False' - Evidence explicitly contradicts ANY key fact in the claim  
3. 'Unverifiable' - Evidence is insufficient or ambiguous

EXAMPLES:

Claim: "India has 28 states"
Evidence: "India consists of 28 states and 8 union territories"
Verdict: True (exact match)

Claim: "The Eiffel Tower is in Berlin"
Evidence: "The Eiffel Tower is located in Paris, France"
Verdict: False (contradicts location)

Claim: "Apple will launch new product tomorrow"
Evidence: "Apple announced an event next week"
Verdict: Unverifiable (timing doesn't match exactly)

NOW ANALYZE:

Claim: "{claim}"

Evidence:
{evidence}

Apply normalization:
- Ignore case, punctuation, number formats
- "2005 crore" = "₹2,005 cr" = "Rs. 2005 crores"
- "IREDA" = "India Renewable Energy Development Agency"

Return a JSON with these fields: verdict, confidence, reasoning. The output MUST ONLY be the valid JSON string."""
        
        return PromptTemplate(
            template=template,
            input_variables=["claim", "evidence"]
        )

    
    def get_verdict(self, claim: str, evidence: List[str]) -> Verdict:
        """Get fact-checking verdict using LLM with caching and robust error handling"""
        
        # Check cache first
        cache_key = f"{claim}|{str(sorted(evidence))}"
        cached_result = query_cache.get(cache_key)
        if cached_result:
            logger.info("Returning cached verdict")
            return Verdict(**cached_result)
        
        logger.info(f"Processing claim with LLM: {claim[:100]}...")
        
        # Use LLM for accurate, context-aware verification
        evidence_str = "\n".join([f"{i+1}. {e}" for i, e in enumerate(evidence)])
        candidate_models = list(dict.fromkeys([GROQ_MODEL, "groq/compound-mini", "openai/gpt-oss-20b", "llama-3.1-8b-instant"]))
        
        last_error = None
        try:
            self._initialize_client()
            user_message = self.prompt.format(claim=claim, evidence=evidence_str)
            messages = [{"role": "user", "content": user_message}]
            
            response = None
            for model_name in candidate_models:
                try:
                    logger.info(f"Querying Groq with model: {model_name}...")
                    response = self.client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        max_tokens=512,
                        temperature=0.2,
                        response_format={"type": "json_object"}
                    )
                    if response:
                        break
                except Exception as model_err:
                    logger.warning(f"Groq model '{model_name}' failed: {model_err}")
                    last_error = model_err
            
            if not response:
                raise last_error or RuntimeError("No Groq models available.")
            
            # Parse JSON output
            content = response.choices[0].message.content
            result_dict = json.loads(content)
            result = Verdict(**result_dict)
            
            # Validate confidence
            result.confidence = max(0.0, min(1.0, result.confidence))
            
            logger.info(f"LLM verdict: {result.verdict} (confidence: {result.confidence:.2f})")
            
            # Cache result
            result_data = result.model_dump() if hasattr(result, "model_dump") else result.dict()
            query_cache.set(cache_key, result_data)
            
            return result
        except Exception as e:
            logger.error(f"LLM service error: {e}")
            return self._fallback_verification(claim, evidence, str(e))
    
    
    def _fallback_verification(self, claim: str, evidence: List[str], error_msg: str) -> Verdict:
        """Fallback response when LLM model is unavailable"""
        logger.info(f"LLM verification unavailable: {error_msg}")
        
        has_key = bool(os.environ.get("GROQ_API_KEY", "").strip())
        if not has_key or "Groq API key not found" in error_msg:
            reasoning = (
                "LLM verification model is currently unavailable because GROQ_API_KEY is not configured in backend/.env. "
                "Add your free Groq API key (from https://console.groq.com) to backend/.env as GROQ_API_KEY=gsk_... to enable automatic AI verdicts."
            )
        else:
            reasoning = (
                f"LLM verification model is currently unavailable ({error_msg}). "
                "Please verify your GROQ_API_KEY in backend/.env and check your internet connection."
            )
        
        return Verdict(
            verdict="Unverifiable",
            confidence=0.0,
            reasoning=reasoning
        )

llm_service = LLMService()