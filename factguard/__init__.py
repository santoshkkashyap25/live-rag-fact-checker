# factguard/__init__.py
"""
FactGuard: Real-Time Web Intelligence & Multi-LLM Fact-Checking Library.
"""

from factguard.client import FactGuard
from factguard.models import FactCheckResult

__version__ = "1.0.0"
__all__ = ["FactGuard", "FactCheckResult"]
