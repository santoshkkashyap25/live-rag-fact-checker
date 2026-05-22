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
        if self.client is None:
            if "GROQ_API_KEY" not in os.environ:
                raise ValueError(
                    "Groq API key not found. "
                    "Set GROQ_API_KEY in environment or .env file."
                )
            logger.info("Initializing Groq LLM client...")
            self.client = Groq(
                api_key=os.environ.get("GROQ_API_KEY")
            )
    
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

    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        text = text.lower()
        # Remove currency symbols and commas
        text = re.sub(r'rs\.|₹|,', '', text)
        # Standardize number formats
        text = re.sub(r'(\d+)\s*(crore|cr|crores|billion|million)', r'\1 \2', text)
        text = re.sub(r'(\d+)\s*lakh', r'\1 lakh', text)
        # Remove punctuation
        text = re.sub(r'[^\w\s]', ' ', text)
        # Normalize common entities
        text = re.sub(r'\bireda\b', 'india renewable energy development agency', text)
        # Remove extra spaces
        text = ' '.join(text.split())
        return text
    
    def _check_exact_match(self, claim: str, evidence: List[str]) -> Tuple[bool, List[str]]:
        """Check for normalized exact matches"""
        norm_claim = self._normalize_text(claim)
        matches = []
        
        for item in evidence:
            norm_item = self._normalize_text(item)
            # Check if normalized claim is substring of evidence
            if norm_claim in norm_item:
                matches.append(item)
        
        return (len(matches) > 0, matches)
    
    def get_verdict(self, claim: str, evidence: List[str]) -> Verdict:
        """Get fact-checking verdict with caching and robust error handling"""
        
        # Check cache first
        cache_key = f"{claim}|{str(sorted(evidence))}"
        cached_result = query_cache.get(cache_key)
        if cached_result:
            logger.info("Returning cached verdict")
            return Verdict(**cached_result)
        
        logger.info(f"Processing claim: {claim[:100]}...")
        
        # Quick exact match check
        has_match, matches = self._check_exact_match(claim, evidence)
        
        if has_match:
            logger.info(f"Exact match found in {len(matches)} evidence items")
            result = Verdict(
                verdict="True",
                confidence=0.95,
                reasoning=f"The claim directly matches verified evidence: '{matches[0][:200]}...'"
            )
            query_cache.set(cache_key, result.dict())
            return result
        
        # Check for clear contradictions
        contradiction_result = self._check_contradiction(claim, evidence)
        if contradiction_result:
            logger.info("Clear contradiction detected")
            query_cache.set(cache_key, contradiction_result.dict())
            return contradiction_result
        
        # Use LLM for nuanced verification
        evidence_str = "\n".join([f"{i+1}. {e}" for i, e in enumerate(evidence)])
        try:
            self._initialize_client()
            # Prepare messages
            user_message = self.prompt.format(claim=claim, evidence=evidence_str)
            messages = [{"role": "user", "content": user_message}]
            
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=messages,
                max_tokens=512,
                temperature=0.2,
                response_format={"type": "json_object"}
            )
            
            # Parse JSON output
            content = response.choices[0].message.content
            result_dict = json.loads(content)
            result = Verdict(**result_dict)
            
            # Validate confidence
            result.confidence = max(0.0, min(1.0, result.confidence))
            
            logger.info(f"LLM verdict: {result.verdict} (confidence: {result.confidence:.2f})")
            
            # Cache result
            query_cache.set(cache_key, result.dict())
            
            return result

            
        except Exception as e:
            logger.error(f"LLM service error: {e}")
            
            # Fallback to rule-based verification
            return self._fallback_verification(claim, evidence, str(e))
    
    def _check_contradiction(self, claim: str, evidence: List[str]) -> Optional[Verdict]:
        """Check for obvious contradictions (e.g., different countries/entities)"""
        norm_claim = self._normalize_text(claim)
        
        # Extract key entities from claim (simple approach)
        claim_entities = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', claim))
        
        for item in evidence:
            norm_item = self._normalize_text(item)
            item_entities = set(re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b', item))
            
            # Check if claim mentions one country but evidence mentions another
            countries = ['india', 'china', 'usa', 'england', 'france', 'germany', 'japan']
            claim_countries = [c for c in countries if c in norm_claim]
            item_countries = [c for c in countries if c in norm_item]
            
            if claim_countries and item_countries:
                if claim_countries[0] != item_countries[0]:
                    return Verdict(
                        verdict="False",
                        confidence=0.90,
                        reasoning=f"The claim refers to {claim_countries[0].title()} but the evidence discusses {item_countries[0].title()}. This is a clear contradiction."
                    )
        
        return None
    
    def _fallback_verification(self, claim: str, evidence: List[str], error_msg: str) -> Verdict:
        """Fallback rule-based verification when LLM fails"""
        logger.info("Using fallback rule-based verification")
        
        norm_claim = self._normalize_text(claim)
        
        # Calculate similarity scores manually
        max_similarity = 0.0
        best_evidence = ""
        
        for item in evidence:
            norm_item = self._normalize_text(item)
            
            # Simple word overlap similarity
            claim_words = set(norm_claim.split())
            item_words = set(norm_item.split())
            
            if len(claim_words) > 0:
                overlap = len(claim_words & item_words)
                similarity = overlap / len(claim_words)
                
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_evidence = item
        
        # Make decision based on similarity
        if max_similarity > 0.7:
            verdict = "True"
            confidence = max_similarity
            reasoning = f"High similarity ({max_similarity:.2%}) with evidence: '{best_evidence[:150]}...'"
        elif max_similarity > 0.3:
            verdict = "Unverifiable"
            confidence = 0.5
            reasoning = f"Partial match ({max_similarity:.2%}) with evidence. Cannot confirm or deny with certainty."
        else:
            verdict = "Unverifiable"
            confidence = 0.3
            reasoning = f"Low similarity ({max_similarity:.2%}) with available evidence. Claim cannot be verified."
        
        return Verdict(
            verdict=verdict,
            confidence=confidence,
            reasoning=f"{reasoning} (Note: LLM unavailable, using rule-based verification)"
        )

llm_service = LLMService()