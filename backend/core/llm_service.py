# core/llm_service.py
import os
import logging
import re
import json
from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from dotenv import load_dotenv
from config import GROQ_MODEL
from core.cache import query_cache

try:
    import litellm
    # Suppress verbose litellm logs
    litellm.suppress_debug_info = True
    litellm.set_verbose = False
except ImportError:
    litellm = None

try:
    from groq import Groq
except ImportError:
    Groq = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Verdict(BaseModel):
    model_config = ConfigDict(protected_namespaces=())
    verdict: str = Field(description="Must be exactly: 'True', 'False', or 'Unverifiable'")
    confidence: float = Field(description="Confidence score between 0.0 and 1.0")
    reasoning: str = Field(description="Detailed explanation with evidence citations")
    provider_used: Optional[str] = "groq"
    model_used: Optional[str] = GROQ_MODEL

class LLMService:
    """Multi-provider LLM service supporting Groq, OpenAI, Google Gemini, and Anthropic Claude"""
    
    DEFAULT_MODELS = {
        "groq": GROQ_MODEL or "groq/compound-mini",
        "openai": "gpt-4o-mini",
        "gemini": "gemini/gemini-1.5-flash",
        "claude": "anthropic/claude-3-5-haiku-20241022",
    }
    
    def __init__(self):
        load_dotenv()
        self.groq_client = None
        self.prompt = self._create_enhanced_prompt()
        logger.info("LLM service initialized with multi-provider BYOK support")

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
        return template

    def _normalize_model(self, provider: str, model: Optional[str]) -> str:
        provider = (provider or "groq").lower().strip()
        if not model or not model.strip():
            return self.DEFAULT_MODELS.get(provider, self.DEFAULT_MODELS["groq"])
        
        m = model.strip()
        if provider == "groq":
            return m
        elif provider == "gemini" and not m.startswith("gemini/"):
            return f"gemini/{m}"
        elif provider == "claude" and not m.startswith("anthropic/"):
            return f"anthropic/{m}"
        elif provider == "openai":
            return m
        return m

    def _extract_json(self, text: str) -> Dict[str, Any]:
        """Safely extract JSON from model output across different providers"""
        text = text.strip()
        fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fence_match:
            return json.loads(fence_match.group(1))
        
        brace_match = re.search(r"(\{.*\})", text, re.DOTALL)
        if brace_match:
            return json.loads(brace_match.group(1))
        
        return json.loads(text)

    def test_connection(
        self, 
        provider: str, 
        api_key: str, 
        model: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Test user API key connectivity with a lightweight prompt"""
        clean_key = (api_key or "").strip()
        if not clean_key:
            return False, "API key cannot be empty."
        
        clean_provider = (provider or "groq").lower().strip()
        
        # 1. Native Groq testing
        if clean_provider == "groq":
            if Groq is None:
                return False, "Groq client library is not available."
            try:
                client = Groq(api_key=clean_key)
                m = (model or GROQ_MODEL).strip()
                client.chat.completions.create(
                    model=m,
                    messages=[{"role": "user", "content": "Ping test: reply with 'OK'."}],
                    max_tokens=5
                )
                return True, f"Connection verified successfully! ({m})"
            except Exception as ge:
                err_str = str(ge)
                logger.warning(f"Groq connection test failed: {err_str}")
                if "401" in err_str or "invalid_api_key" in err_str or "authentication" in err_str.lower():
                    return False, "Invalid API Key for Groq."
                elif "404" in err_str or "not found" in err_str.lower():
                    return False, f"Model '{m}' not found or restricted for your key."
                return False, f"Groq error: {err_str[:120]}"

        # 2. LiteLLM testing for OpenAI, Gemini, Claude
        litellm_model = self._normalize_model(clean_provider, model)
        try:
            if litellm is None:
                return False, "LiteLLM multi-provider engine is initializing."
            
            logger.info(f"Testing connection for '{clean_provider}' using model '{litellm_model}'...")
            litellm.completion(
                model=litellm_model,
                messages=[{"role": "user", "content": "Ping test: reply with 'OK' in one word."}],
                api_key=clean_key,
                max_tokens=10,
                temperature=0.1
            )
            return True, f"Connection verified successfully! ({litellm_model})"
        except Exception as e:
            err_str = str(e)
            logger.warning(f"Connection test failed for {clean_provider}: {err_str}")
            if "401" in err_str or "authentication" in err_str.lower() or "api_key" in err_str.lower():
                return False, f"Invalid API Key for {clean_provider.capitalize()}."
            elif "429" in err_str or "quota" in err_str.lower() or "rate" in err_str.lower():
                return False, f"Rate limit or quota reached on {clean_provider.capitalize()} account."
            elif "404" in err_str or "not found" in err_str.lower():
                return False, f"Model '{litellm_model}' not found or restricted for your key."
            return False, f"Connection test failed: {err_str[:120]}"

    def get_verdict(
        self, 
        claim: str, 
        evidence: List[str],
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ) -> Verdict:
        """Get fact-checking verdict using LLM with caching and multi-provider BYOK support"""
        
        # Determine provider and model
        clean_provider = (provider or "groq").lower().strip()
        custom_key = (api_key or "").strip()
        has_custom_key = bool(custom_key)
        
        effective_provider = clean_provider if has_custom_key else "groq"
        effective_model = self._normalize_model(effective_provider, model)
        
        # Check cache
        cache_key = f"{effective_provider}:{effective_model}:{claim}|{str(sorted(evidence))}"
        cached_result = query_cache.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached verdict for [{effective_provider}]")
            return Verdict(**cached_result)
        
        logger.info(f"Processing claim with LLM [{effective_provider} - {effective_model}]: {claim[:100]}...")
        
        evidence_str = "\n".join([f"{i+1}. {e}" for i, e in enumerate(evidence)])
        user_message = self.prompt.format(claim=claim, evidence=evidence_str)
        messages = [{"role": "user", "content": user_message}]
        
        try:
            content = None
            
            # --- Branch 1: Groq (via native client) ---
            if effective_provider == "groq":
                target_key = custom_key or os.environ.get("GROQ_API_KEY", "").strip()
                if not target_key:
                    raise ValueError("Groq API key not provided or configured in server environment.")
                
                client = Groq(api_key=target_key)
                
                # Candidate fallback models on Groq
                candidates = list(dict.fromkeys([
                    effective_model,
                    GROQ_MODEL,
                    "groq/compound-mini",
                    "openai/gpt-oss-20b",
                    "qwen/qwen3.6-27b",
                ]))
                
                last_err = None
                for cand in candidates:
                    try:
                        logger.info(f"Querying Groq with model: {cand}...")
                        res = client.chat.completions.create(
                            model=cand,
                            messages=messages,
                            max_tokens=512,
                            temperature=0.2,
                            response_format={"type": "json_object"}
                        )
                        content = res.choices[0].message.content
                        effective_model = cand
                        break
                    except Exception as ge:
                        logger.warning(f"Groq model {cand} failed: {ge}")
                        last_err = ge
                
                if not content:
                    raise last_err or RuntimeError("No Groq models available.")

            # --- Branch 2: OpenAI, Gemini, Claude (via LiteLLM) ---
            else:
                if litellm is None:
                    raise RuntimeError("LiteLLM library is not installed.")
                if not custom_key:
                    raise ValueError(f"Please provide an API key for {effective_provider.capitalize()} in LLM Settings.")
                
                logger.info(f"Querying {effective_provider} via LiteLLM with {effective_model}...")
                completion_kwargs: Dict[str, Any] = {
                    "model": effective_model,
                    "messages": messages,
                    "api_key": custom_key,
                    "max_tokens": 512,
                    "temperature": 0.2,
                }
                if effective_provider == "openai":
                    completion_kwargs["response_format"] = {"type": "json_object"}
                
                response = litellm.completion(**completion_kwargs)
                content = response.choices[0].message.content

            # Parse JSON output
            result_dict = self._extract_json(content)
            
            verdict = result_dict.get("verdict", "Unverifiable")
            if verdict not in ["True", "False", "Unverifiable"]:
                verdict = "Unverifiable"
                
            raw_conf = result_dict.get("confidence", 0.8)
            if isinstance(raw_conf, (int, float)):
                confidence = float(raw_conf)
            elif isinstance(raw_conf, str):
                clean_conf = raw_conf.replace("%", "").strip()
                try:
                    val = float(clean_conf)
                    confidence = val / 100.0 if val > 1.0 else val
                except ValueError:
                    if "high" in raw_conf.lower():
                        confidence = 0.90
                    elif "med" in raw_conf.lower():
                        confidence = 0.60
                    elif "low" in raw_conf.lower():
                        confidence = 0.30
                    else:
                        confidence = 0.70
            else:
                confidence = 0.80
            confidence = max(0.0, min(1.0, confidence))
            
            reasoning = result_dict.get("reasoning", "Evidence evaluated against claim.")
            clean_display_model = effective_model
            
            result = Verdict(
                verdict=verdict,
                confidence=confidence,
                reasoning=reasoning,
                provider_used=effective_provider,
                model_used=clean_display_model
            )
            
            logger.info(f"LLM verdict [{result.provider_used}/{result.model_used}]: {result.verdict} ({result.confidence:.2f})")
            
            # Cache result
            result_data = result.model_dump() if hasattr(result, "model_dump") else result.dict()
            query_cache.set(cache_key, result_data)
            
            return result
            
        except Exception as e:
            logger.error(f"LLM service error: {e}")
            return self._fallback_verification(claim, evidence, str(e), effective_provider, effective_model)

    def _fallback_verification(
        self, 
        claim: str, 
        evidence: List[str], 
        error_msg: str,
        provider: str = "groq",
        model: str = "default"
    ) -> Verdict:
        """Fallback response when LLM model is unavailable"""
        logger.info(f"LLM verification unavailable: {error_msg}")
        
        has_sys_key = bool(os.environ.get("GROQ_API_KEY", "").strip())
        if "API Key" in error_msg or not has_sys_key:
            reasoning = (
                f"LLM verification failed ({error_msg}). "
                "Please configure a valid API key for your chosen provider in 'LLM Settings' (Groq, OpenAI, Google Gemini, Anthropic Claude)."
            )
        else:
            reasoning = (
                f"LLM verification unavailable ({error_msg}). "
                "Please check your API key / model in 'LLM Settings' or internet connection."
            )
        
        return Verdict(
            verdict="Unverifiable",
            confidence=0.0,
            reasoning=reasoning,
            provider_used=provider,
            model_used=model
        )

llm_service = LLMService()