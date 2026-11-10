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

    def verify(
        self,
        statement: str,
        user_id: str = "python_sdk_user",
        use_cache: bool = True
    ) -> FactCheckResult:
        """
        Verify a statement against live web evidence and neural re-ranking.

        Args:
            statement: Claim or text to verify.
            user_id: Optional client ID for per-user query caching.
            use_cache: Whether to use cached results (default: True).

        Returns:
            FactCheckResult with verdict, confidence, reasoning, and citations.
        """
        if not statement or not statement.strip():
            raise ValueError("Statement to verify cannot be empty.")

        url = f"{self.api_url}/api/verify"
        payload: Dict[str, Any] = {
            "text": statement.strip(),
            "user_id": user_id,
            "use_cache": use_cache
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

    def stream(
        self,
        statement: str,
        user_id: str = "python_sdk_stream",
        use_cache: bool = True
    ) -> Generator[Dict[str, Any], None, None]:
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
            "user_id": user_id,
            "use_cache": use_cache
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

    def as_langchain_tool(self, name: str = "factguard_verifier"):
        """
        Export FactGuard as a LangChain Tool for autonomous agents.

        Usage:
            from factguard import FactGuard
            fg = FactGuard()
            tool = fg.as_langchain_tool()
            agent = initialize_agent([tool], llm, ...)
        """
        try:
            from langchain.tools import Tool
            return Tool(
                name=name,
                func=lambda query: self.verify(query).reasoning,
                description="Verifies claims against live web intelligence (DuckDuckGo + Wikipedia). Pass a single factual statement to verify."
            )
        except ImportError:
            raise ImportError("LangChain is not installed. Install via `pip install langchain` to use as_langchain_tool().")

    def as_llamaindex_tool(self, name: str = "factguard_verifier"):
        """
        Export FactGuard as a LlamaIndex FunctionTool for ReAct / Agent workflows.

        Usage:
            from factguard import FactGuard
            fg = FactGuard()
            tool = fg.as_llamaindex_tool()
        """
        try:
            from llama_index.core.tools import FunctionTool
            def verify_claim(statement: str) -> str:
                res = self.verify(statement)
                return f"Verdict: {res.verdict} (Confidence: {res.confidence:.2f})\nReasoning: {res.reasoning}"
            return FunctionTool.from_defaults(
                fn=verify_claim,
                name=name,
                description="Verifies factual statements against live web intelligence."
            )
        except ImportError:
            raise ImportError("LlamaIndex is not installed. Install via `pip install llama-index` to use as_llamaindex_tool().")
