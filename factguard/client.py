# factguard/client.py
import json
import logging
from typing import Optional, Dict, Any, Generator
import requests

from factguard.models import FactCheckResult

logger = logging.getLogger("factguard")

DEFAULT_API_URL = "https://factguard-1gge.onrender.com"

class FactGuard:
    """
    FactGuard: Real-Time Web Intelligence & Multi-LLM Fact-Checking SDK.

    Usage:
        from factguard import FactGuard

        # Initialize with cloud demo or local server:
        fg = FactGuard()  # defaults to live FactGuard cloud endpoint

        # Run verification:
        result = fg.verify("Bananas are naturally radioactive.")
        print(result.verdict)       # 'True'
        print(result.confidence)    # 0.95
        print(result.reasoning)     # Explanation with citations
    """

    def __init__(
        self,
        api_url: Optional[str] = None,
        provider: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: int = 60
    ):
        self.api_url = (api_url or DEFAULT_API_URL).rstrip("/")
        self.provider = provider
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def verify(self, statement: str, user_id: str = "python_sdk_user") -> FactCheckResult:
        """
        Verify a statement against live web evidence and neural re-ranking.

        Args:
            statement: Claim or text to verify.
            user_id: Optional client ID for per-user query caching.

        Returns:
            FactCheckResult with verdict, confidence, reasoning, and citations.
        """
        if not statement or not statement.strip():
            raise ValueError("Statement to verify cannot be empty.")

        url = f"{self.api_url}/api/verify"
        payload: Dict[str, Any] = {
            "text": statement.strip(),
            "user_id": user_id
        }
        if self.provider:
            payload["llm_provider"] = self.provider
        if self.api_key:
            payload["llm_api_key"] = self.api_key
        if self.model:
            payload["llm_model"] = self.model

        try:
            res = requests.post(url, json=payload, timeout=self.timeout)
            if not res.ok:
                err_msg = res.text
                try:
                    err_msg = res.json().get("detail", err_msg)
                except Exception:
                    pass
                raise RuntimeError(f"FactGuard API error ({res.status_code}): {err_msg}")

            data = res.json()
            return FactCheckResult(
                input_text=data.get("input_text", statement),
                extracted_claim=data.get("extracted_claim", statement),
                verdict=data.get("verdict", "Unverifiable"),
                confidence=float(data.get("confidence", 0.8)),
                reasoning=data.get("reasoning", ""),
                evidence=data.get("evidence", []),
                evidence_scores=data.get("evidence_scores", []),
                evidence_sources=data.get("evidence_sources", []),
                evidence_urls=data.get("evidence_urls", []),
                engine=data.get("engine", {}),
                performance=data.get("performance", {}),
                is_cache_hit=data.get("is_cache_hit", False)
            )
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Failed to connect to FactGuard at {self.api_url}: {e}")

    def stream(self, statement: str, user_id: str = "python_sdk_stream") -> Generator[Dict[str, Any], None, None]:
        """
        Stream real-time verification phases ('extracting', 'searching', 'reranking', 'reasoning', 'complete').

        Yields:
            Parsed SSE event dictionary for each phase.
        """
        if not statement or not statement.strip():
            raise ValueError("Statement to verify cannot be empty.")

        url = f"{self.api_url}/api/verify/stream"
        payload: Dict[str, Any] = {
            "text": statement.strip(),
            "user_id": user_id
        }
        if self.provider:
            payload["llm_provider"] = self.provider
        if self.api_key:
            payload["llm_api_key"] = self.api_key
        if self.model:
            payload["llm_model"] = self.model

        try:
            with requests.post(url, json=payload, stream=True, timeout=self.timeout) as res:
                if not res.ok:
                    raise RuntimeError(f"FactGuard streaming API error ({res.status_code}): {res.text}")
                for line in res.iter_lines():
                    if line:
                        decoded = line.decode("utf-8").strip()
                        if decoded.startswith("data: "):
                            raw_json = decoded[6:]
                            try:
                                yield json.loads(raw_json)
                            except json.JSONDecodeError:
                                pass
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Streaming error with FactGuard at {self.api_url}: {e}")

    def share(self, result: FactCheckResult) -> str:
        """
        Publish a verified result to generate a public shareable permalink.

        Returns:
            The public permalink URL (e.g. 'https://factguard-1gge.onrender.com/v/a8f2c3').
        """
        url = f"{self.api_url}/api/share"
        res = requests.post(url, json={"result": result.model_dump()}, timeout=15)
        if not res.ok:
            raise RuntimeError(f"Failed to create share link: {res.text}")
        data = res.json()
        return data.get("full_url") or f"{self.api_url}{data.get('url')}"
