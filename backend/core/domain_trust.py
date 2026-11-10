# core/domain_trust.py
"""
FactGuard AI: Source Authority & Domain Credibility Scoring Engine (Moat A).
Evaluates origin domains, assigns calibrated trust multipliers, and detects satirical sources.
"""

import re
import urllib.parse
from typing import Dict, Any, Tuple, Optional

# Tier 1: Peer-Reviewed Scientific, Institutional, Government & Primary Wire Agencies (1.5x Multiplier)
TIER_1_AUTHORITATIVE = {
    # Scholarly & Scientific
    "nature.com": 1.6, "science.org": 1.6, "nih.gov": 1.6, "ncbi.nlm.nih.gov": 1.6,
    "cdc.gov": 1.5, "who.int": 1.5, "nasa.gov": 1.5, "britannica.com": 1.5,
    "wikipedia.org": 1.4, "stanford.edu": 1.5, "mit.edu": 1.5, "harvard.edu": 1.5,
    "ox.ac.uk": 1.5, "cam.ac.uk": 1.5, "arxiv.org": 1.5, "jstor.org": 1.5,
    "pnas.org": 1.6, "cell.com": 1.6, "thelancet.com": 1.6, "nejm.org": 1.6,
    "nobelprize.org": 1.6, "un.org": 1.5, "scientificamerican.com": 1.4,
    # Primary Wire Services & Verified Fact Checkers
    "reuters.com": 1.5, "apnews.com": 1.5, "bbc.com": 1.5, "bbc.co.uk": 1.5,
    "snopes.com": 1.5, "politifact.com": 1.5, "factcheck.org": 1.5,
    "fullfact.org": 1.5, "afp.com": 1.5
}

# Tier 2: Mainstream Credible Journalism & Established Publications (1.2x Multiplier)
TIER_2_MAINSTREAM_PRESS = {
    "nytimes.com": 1.25, "wsj.com": 1.25, "theguardian.com": 1.2,
    "washingtonpost.com": 1.2, "economist.com": 1.25, "thehindu.com": 1.2,
    "bloomberg.com": 1.25, "forbes.com": 1.1, "time.com": 1.15,
    "nationalgeographic.com": 1.25, "ft.com": 1.25, "npr.org": 1.2,
    "pbs.org": 1.2, "theatlantic.com": 1.2, "newscientist.com": 1.25,
    "technologyreview.com": 1.25, "arstechnica.com": 1.15, "wired.com": 1.15
}

# Tier 3: User-Generated Content, Unvetted Blogs & Forums (0.4x Multiplier)
TIER_3_USER_GENERATED = {
    "medium.com": 0.4, "quora.com": 0.3, "reddit.com": 0.3,
    "blogspot.com": 0.3, "wordpress.com": 0.3, "tumblr.com": 0.25,
    "substack.com": 0.5, "twitter.com": 0.3, "x.com": 0.3,
    "facebook.com": 0.25, "tiktok.com": 0.2, "instagram.com": 0.2
}

# Tier 0: Known Parody & Satirical Publications (Flagged & Disqualified)
TIER_0_SATIRE = {
    "theonion.com", "babylonbee.com", "clickhole.com",
    "theshovel.com.au", "waterfordwhispersnews.com", "newsthump.com",
    "thebeaverton.com", "satirewire.com", "duffelblog.com"
}

def extract_domain(url_or_str: str) -> str:
    """
    Extracts the root registered domain (e.g., 'nature.com' from 'https://www.nature.com/articles/xyz').
    """
    if not url_or_str:
        return ""
    
    # Handle direct text or partial URLs
    raw = url_or_str.strip().lower()
    if not raw.startswith("http://") and not raw.startswith("https://"):
        raw = "https://" + raw

    try:
        parsed = urllib.parse.urlparse(raw)
        netloc = parsed.netloc.split(":")[0]  # Strip port if present
        # Strip leading 'www.'
        if netloc.startswith("www."):
            netloc = netloc[4:]
        return netloc
    except Exception:
        return ""

def get_domain_trust(url_or_str: str) -> Dict[str, Any]:
    """
    Computes domain authority score, category tier, and satire status.
    Returns:
        {
            "domain": str,
            "multiplier": float,
            "tier": str,
            "is_satire": bool,
            "badge": str
        }
    """
    domain = extract_domain(url_or_str)
    
    if not domain:
        return {
            "domain": "web",
            "multiplier": 1.0,
            "tier": "Tier 3: Standard Web",
            "is_satire": False,
            "badge": "🌐 Web"
        }

    # Check Satire First
    for satire_domain in TIER_0_SATIRE:
        if domain == satire_domain or domain.endswith("." + satire_domain):
            return {
                "domain": domain,
                "multiplier": 0.05,
                "tier": "Tier 0: Satire / Parody",
                "is_satire": True,
                "badge": "⚠️ Satire Source"
            }

    # Check Tier 1 Authoritative
    for auth_domain, mult in TIER_1_AUTHORITATIVE.items():
        if domain == auth_domain or domain.endswith("." + auth_domain):
            return {
                "domain": domain,
                "multiplier": mult,
                "tier": "Tier 1: High Authority",
                "is_satire": False,
                "badge": "🏛️ Authoritative Source"
            }

    # Institutional TLD bonuses (.gov, .edu)
    if domain.endswith(".gov") or domain.endswith(".gov.uk") or domain.endswith(".gov.in"):
        return {
            "domain": domain,
            "multiplier": 1.5,
            "tier": "Tier 1: Government Authority",
            "is_satire": False,
            "badge": "🏛️ Official Government"
        }
    if domain.endswith(".edu") or domain.endswith(".ac.uk"):
        return {
            "domain": domain,
            "multiplier": 1.5,
            "tier": "Tier 1: Academic Institution",
            "is_satire": False,
            "badge": "🎓 Academic / Research"
        }

    # Check Tier 2 Mainstream Press
    for press_domain, mult in TIER_2_MAINSTREAM_PRESS.items():
        if domain == press_domain or domain.endswith("." + press_domain):
            return {
                "domain": domain,
                "multiplier": mult,
                "tier": "Tier 2: Mainstream Press",
                "is_satire": False,
                "badge": "📰 Verified Press"
            }

    # Check Tier 3 User Generated Content / Blogs
    for ugc_domain, mult in TIER_3_USER_GENERATED.items():
        if domain == ugc_domain or domain.endswith("." + ugc_domain):
            return {
                "domain": domain,
                "multiplier": mult,
                "tier": "Tier 4: User Generated / Forum",
                "is_satire": False,
                "badge": "💬 Blog / Forum"
            }

    # Default General Web
    return {
        "domain": domain,
        "multiplier": 1.0,
        "tier": "Tier 3: Standard Web",
        "is_satire": False,
        "badge": "🌐 Web"
    }

def score_and_badge_evidence(evidence_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriches evidence dictionary with domain trust metrics.
    """
    url = evidence_dict.get("url", "")
    trust_meta = get_domain_trust(url)
    evidence_dict["domain_trust"] = trust_meta
    return evidence_dict
