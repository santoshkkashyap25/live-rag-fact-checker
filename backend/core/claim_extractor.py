# core/claim_extractor.py
import spacy
import logging
import subprocess
import sys
import re
from typing import List, Optional
from config import SPACY_MODEL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ClaimExtractor:
    """Enhanced claim extraction with multiple strategies"""
    
    def __init__(self):
        logger.info(f"Loading SpaCy model '{SPACY_MODEL}'...")
        try:
            self.nlp = spacy.load(SPACY_MODEL)
        except OSError:
            logger.warning(f"Model '{SPACY_MODEL}' not found. Downloading...")
            subprocess.check_call([
                sys.executable, "-m", "spacy", "download", SPACY_MODEL
            ])
            self.nlp = spacy.load(SPACY_MODEL)
        logger.info("SpaCy model loaded successfully.")
    
    def extract(self, text: str) -> str:
        """Extract main claim from text using multiple strategies"""
        logger.info(f"Extracting claim from: {text[:100]}...")
        
        # Strategy 1: Clean and check if already atomic
        cleaned = self._clean_text(text)
        if self._is_atomic_claim(cleaned):
            logger.info("Claim is already atomic, returning as-is")
            return cleaned
        
        # Strategy 2: Extract from complex sentence
        doc = self.nlp(cleaned)
        
        # Try dependency parsing
        claim = self._extract_via_dependency_parsing(doc)
        if claim:
            logger.info(f"Extracted via dependency parsing: {claim}")
            return claim
        
        # Strategy 3: Extract longest declarative sentence
        claim = self._extract_longest_declarative(doc)
        if claim:
            logger.info(f"Extracted longest declarative: {claim}")
            return claim
        
        # Fallback: return cleaned text
        logger.warning("No specific pattern matched, returning cleaned text")
        return cleaned or text.strip()
    
    def _clean_text(self, text: str) -> str:
        """Remove common fillers and conversational phrases"""
        # Remove common prefixes
        patterns = [
            r'^(for example\s*:?\s*|e\.g\.\s*:?\s*|i\.e\.\s*:?\s*)',
            r'^(I think that\s*|It is believed that\s*|Some say\s*)',
            r'^(According to\s+\w+\s*,\s*)',
            r'\s*\(\s*for example\s*\)\s*',
        ]
        
        for pattern in patterns:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        return text.strip()
    
    def _is_atomic_claim(self, text: str) -> bool:
        """Check if text is already a simple, atomic claim"""
        # Short, no conjunctions, no questions
        word_count = len(text.split())
        has_conjunctions = any(conj in text.lower() for conj in [' and ', ' but ', ' or ', ' however '])
        is_question = text.strip().endswith('?')
        
        return (5 <= word_count <= 15 and 
                not has_conjunctions and 
                not is_question and
                text.strip())
    
    def _extract_via_dependency_parsing(self, doc) -> Optional[str]:
        """Extract claim using dependency parsing"""
        for sent in doc.sents:
            for token in sent:
                # Find root verb
                if token.dep_ == "ROOT" and token.pos_ == "VERB":
                    # Get subject
                    subjects = [
                        self._get_full_phrase(child)
                        for child in token.children
                        if child.dep_ in ("nsubj", "nsubjpass")
                    ]
                    
                    # Get objects/complements
                    objects = []
                    for child in token.children:
                        if child.dep_ in ("dobj", "attr", "acomp", "prep"):
                            objects.append(self._get_full_phrase(child))
                    
                    # Reconstruct claim
                    if subjects and objects:
                        verb = token.text
                        claim = f"{subjects[0]} {verb} {' '.join(objects)}"
                        return self._clean_claim(claim)
        
        return None
    
    def _extract_longest_declarative(self, doc) -> Optional[str]:
        """Extract longest declarative sentence"""
        candidates = []
        
        for sent in doc.sents:
            text = sent.text.strip()
            # Skip questions, exclamations, very short sentences
            if (not text.endswith(('?', '!')) and 
                len(text.split()) >= 5):
                candidates.append(text)
        
        if candidates:
            # Return longest
            return max(candidates, key=lambda x: len(x.split()))
        
        return None
    
    def _get_full_phrase(self, token) -> str:
        """Get full phrase including all children"""
        return " ".join([t.text for t in sorted(token.subtree, key=lambda t: t.i)])
    
    def _clean_claim(self, claim: str) -> str:
        """Final cleanup of extracted claim"""
        # Remove extra spaces
        claim = ' '.join(claim.split())
        # Capitalize first letter
        if claim:
            claim = claim[0].upper() + claim[1:]
        return claim

claim_extractor = ClaimExtractor()