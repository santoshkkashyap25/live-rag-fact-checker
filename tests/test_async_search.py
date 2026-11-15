# tests/test_async_search.py
import asyncio
import time
import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir / "backend"))

from core.web_search import web_search


def test_async_search_concurrency_and_speed():
    """Verify that async_search runs concurrently and completes in sub-4.5 seconds."""
    async def run():
        t0 = time.time()
        results = await web_search.async_search("The Great Wall of China", max_results=8)
        elapsed = time.time() - t0
        return results, elapsed

    results, elapsed = asyncio.run(run())
    assert len(results) > 0, "Expected at least 1 search result"
    assert elapsed < 4.5, f"Search took too long ({elapsed:.2f}s), should be sub-4.5s"
    sources = {r.get("source") for r in results}
    assert any("wikipedia" in s.lower() or "duckduckgo" in s.lower() for s in sources)


def test_async_search_resilience_on_empty():
    """Verify that search handles edge cases without raising exceptions."""
    async def run():
        return await web_search.async_search("", max_results=4)

    results = asyncio.run(run())
    assert isinstance(results, list)


def test_sync_wrapper_compatibility():
    """Verify backward compatibility of synchronous search() wrapper."""
    t0 = time.time()
    results = web_search.search("Apollo 11 Moon landing", max_results=6)
    elapsed = time.time() - t0

    assert len(results) > 0
    assert elapsed < 5.0, f"Sync search took {elapsed:.2f}s, expected < 5.0s"
