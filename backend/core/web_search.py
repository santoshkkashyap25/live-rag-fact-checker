# core/web_search.py
"""
FactGuard AI - High-Performance Asynchronous Web Search Engine
Features:
1. Native Async Concurrency via httpx (sub-second parallel queries)
2. Multi-Engine Architecture: DuckDuckGo HTML + DuckDuckGo Lite + Wikipedia REST API
3. Optional Commercial Fallback: Brave Search API v1 (when BRAVE_API_KEY is configured)
4. Fast Conjunction / Clause-Splitting for Multi-Proposition Claims
5. Dual Interface: Native `async_search()` for async FastAPI pipelines + `search()` for sync callers
"""

import os
import re
import urllib.parse
import logging
import asyncio
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
import httpx

try:
    import trafilatura
    HAS_TRAFILATURA = True
except ImportError:
    HAS_TRAFILATURA = False

from config import BRAVE_API_KEY

logger = logging.getLogger(__name__)


class WebSearchEngine:
    """
    Real-time, resilient web search engine combining Wikipedia REST APIs,
    DuckDuckGo HTML/Lite endpoints, and optional Brave Search API fallback.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://html.duckduckgo.com/",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1"
        }
        self.wiki_headers = {
            "User-Agent": "FactGuardAI/2.0 (factguard-fact-checker@example.com)"
        }
        self.brave_api_key = BRAVE_API_KEY or os.getenv("BRAVE_API_KEY", "").strip()

    @staticmethod
    def _extract_keywords(text: str) -> str:
        stop_words = {
            "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or",
            "is", "are", "was", "were", "it", "this", "that", "these", "those",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "by", "with", "from", "as", "about", "into", "through", "during",
            "due", "presence", "naturally", "specifically", "because", "they",
            "their", "compared", "average", "unusually", "designated", "official",
            "originally", "conceived", "created", "become", "becomes", "see", "sees",
            "seen", "perform", "daily"
        }
        tokens = [w for w in re.findall(r'[a-zA-Z0-9\+\-]+', text) if w.lower() not in stop_words]
        if len(tokens) < 3:
            raw_tokens = re.findall(r'[a-zA-Z0-9\+\-]+', text)
            if raw_tokens:
                return " ".join(raw_tokens[:8])
        return " ".join(tokens[:8])

    async def _async_search_duckduckgo(self, client: httpx.AsyncClient, query: str, max_results: int = 6) -> List[Dict[str, str]]:
        """Search DuckDuckGo HTML endpoint with immediate fallback to DuckDuckGo Lite."""
        results = []

        # 1. Primary: DuckDuckGo HTML GET (fast 2.0s attempt)
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
            resp = await client.get(url, timeout=2.0)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for r in soup.select(".result"):
                    title_elem = r.select_one(".result__title")
                    snippet_elem = r.select_one(".result__snippet")
                    url_elem = r.select_one(".result__url")
                    link_elem = r.select_one("a.result__url") or r.select_one(".result__title a")

                    if title_elem and snippet_elem:
                        title = title_elem.get_text(strip=True)
                        snippet = snippet_elem.get_text(strip=True)
                        href = ""
                        if link_elem and link_elem.get("href"):
                            raw_href = link_elem["href"]
                            if "uddg=" in raw_href:
                                try:
                                    parsed = urllib.parse.parse_qs(urllib.parse.urlparse(raw_href).query)
                                    href = parsed.get("uddg", [""])[0]
                                except Exception:
                                    href = raw_href
                            else:
                                href = raw_href
                        if not href and url_elem:
                            raw_url = url_elem.get_text(strip=True)
                            href = f"https://{raw_url}" if not raw_url.startswith("http") else raw_url

                        if snippet and len(snippet) > 20:
                            results.append({
                                "title": title,
                                "snippet": snippet,
                                "url": href,
                                "source": "DuckDuckGo"
                            })
                    if len(results) >= max_results:
                        break

            if results:
                logger.debug(f"DuckDuckGo HTML search retrieved {len(results)} results for '{query}'")
                return results
        except Exception as e:
            logger.debug(f"DuckDuckGo HTML attempt failed ({e}), falling back to Lite...")

        # 2. Resilient Fallback: DuckDuckGo Lite POST (2.0s attempt)
        try:
            lite_url = "https://lite.duckduckgo.com/lite/"
            lite_resp = await client.post(lite_url, data={"q": query}, timeout=2.0)
            if lite_resp.status_code == 200:
                soup = BeautifulSoup(lite_resp.text, "html.parser")
                titles = soup.select("a.result-link")
                snippets = soup.select("td.result-snippet")
                for title_elem, snip_elem in zip(titles, snippets):
                    title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    if "uddg=" in href:
                        try:
                            parsed = urllib.parse.parse_qs(urllib.parse.urlparse(href).query)
                            href = parsed.get("uddg", [""])[0]
                        except Exception:
                            pass
                    snippet = snip_elem.get_text(strip=True)
                    if snippet and len(snippet) > 20:
                        results.append({
                            "title": title,
                            "snippet": snippet,
                            "url": href,
                            "source": "DuckDuckGo"
                        })
                    if len(results) >= max_results:
                        break
        except Exception as e:
            logger.debug(f"DuckDuckGo Lite fallback error: {e}")

        return results

    async def _async_search_wikipedia(self, client: httpx.AsyncClient, query: str, max_results: int = 4) -> List[Dict[str, str]]:
        """Search Wikipedia Action API using extracts generator for rich introductory context."""
        results = []
        seen_titles = set()
        url = "https://en.wikipedia.org/w/api.php"

        search_terms = []
        kw = self._extract_keywords(query)
        if kw and kw.lower() != query.lower():
            search_terms.append(kw)
        search_terms.append(query)

        for term in search_terms:
            try:
                params = {
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": term,
                    "gsrlimit": max_results,
                    "prop": "extracts",
                    "exintro": "1",
                    "explaintext": "1",
                    "exsentences": "4",
                    "format": "json",
                }
                resp = await client.get(url, params=params, headers=self.wiki_headers, timeout=3.5)
                if resp.status_code == 200:
                    data = resp.json()
                    pages = data.get("query", {}).get("pages", {})
                    for page_id, page_data in pages.items():
                        title = page_data.get("title", "")
                        extract = page_data.get("extract", "").strip()
                        article_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                        if title and extract and len(extract) > 20 and title not in seen_titles:
                            seen_titles.add(title)
                            results.append({
                                "title": f"{title} (Wikipedia)",
                                "snippet": extract,
                                "url": article_url,
                                "source": "Wikipedia"
                            })
                if len(results) >= max_results:
                    break
            except Exception as e:
                logger.debug(f"Wikipedia generator issue for '{term}': {e}")

        if results:
            return results[:max_results]

        # Fallback: list=search
        try:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": max_results,
            }
            resp = await client.get(url, params=params, headers=self.wiki_headers, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title", "")
                    raw_snippet = item.get("snippet", "")
                    clean_snippet = BeautifulSoup(raw_snippet, "html.parser").get_text(separator=" ", strip=True)
                    article_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                    if clean_snippet and title not in seen_titles:
                        seen_titles.add(title)
                        results.append({
                            "title": f"{title} (Wikipedia)",
                            "snippet": clean_snippet,
                            "url": article_url,
                            "source": "Wikipedia"
                        })
        except Exception as e:
            logger.debug(f"Wikipedia list=search fallback error: {e}")

        return results[:max_results]

    async def _async_search_brave(self, client: httpx.AsyncClient, query: str, max_results: int = 6) -> List[Dict[str, str]]:
        """Optional commercial Brave Search API fallback (when BRAVE_API_KEY is configured)."""
        if not self.brave_api_key:
            return []

        results = []
        try:
            url = "https://api.search.brave.com/res/v1/web/search"
            headers = {
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": self.brave_api_key
            }
            params = {"q": query, "count": max_results}
            resp = await client.get(url, params=params, headers=headers, timeout=3.0)
            if resp.status_code == 200:
                data = resp.json()
                web_items = data.get("web", {}).get("results", [])
                for item in web_items:
                    title = item.get("title", "")
                    desc = item.get("description", "")
                    link = item.get("url", "")
                    if title and desc:
                        results.append({
                            "title": title,
                            "snippet": desc,
                            "url": link,
                            "source": "Brave Search"
                        })
                logger.info(f"Brave Search API retrieved {len(results)} authoritative results for '{query}'")
        except Exception as e:
            logger.debug(f"Brave Search API call failed: {e}")

        return results

    async def _async_search_duckduckgo_instant(self, client: httpx.AsyncClient, query: str) -> Optional[Dict[str, str]]:
        """Query DuckDuckGo Instant Answer API for quick definitions."""
        try:
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_redirect": "1",
                "no_html": "1",
                "skip_disambig": "1"
            }
            resp = await client.get(url, params=params, timeout=2.5)
            if resp.status_code == 200:
                data = resp.json()
                abstract = data.get("AbstractText", "").strip()
                source_url = data.get("AbstractURL", "")
                heading = data.get("Heading", query)
                if abstract:
                    return {
                        "title": f"{heading} Summary",
                        "snippet": abstract,
                        "url": source_url or "https://duckduckgo.com",
                        "source": "DuckDuckGo Instant Answer"
                    }
        except Exception:
            pass
        return None

    @staticmethod
    def _extract_salient_passage(full_text: str, query: str, max_chars: int = 800) -> str:
        """Find the most relevant paragraph or passage containing query keywords."""
        paragraphs = [p.strip() for p in re.split(r'\n+', full_text) if len(p.strip()) > 40]
        if not paragraphs:
            clean_all = re.sub(r'\s+', ' ', full_text).strip()
            return clean_all[:max_chars].rsplit(' ', 1)[0] + '...' if len(clean_all) > max_chars else clean_all

        # Tokenize query keywords (excluding stop words)
        q_tokens = set(re.findall(r'[a-zA-Z0-9]+', query.lower())) - {
            "a", "an", "the", "in", "on", "at", "to", "for", "of", "and", "or",
            "is", "are", "was", "were", "it", "this", "that", "these", "those",
            "be", "been", "being", "have", "has", "had", "do", "does", "did",
            "by", "with", "from", "as", "about", "into", "through", "during"
        }

        best_score = -1
        best_p = paragraphs[0]

        for p in paragraphs:
            p_tokens = set(re.findall(r'[a-zA-Z0-9]+', p.lower()))
            overlap = len(q_tokens.intersection(p_tokens))
            if overlap > best_score:
                best_score = overlap
                best_p = p

        clean_passage = re.sub(r'\s+', ' ', best_p).strip()
        if len(clean_passage) > max_chars:
            return clean_passage[:max_chars].rsplit(' ', 1)[0] + '...'
        return clean_passage

    async def _async_extract_article_content(
        self,
        client: httpx.AsyncClient,
        url: str,
        query: str,
        timeout_sec: float = 1.5,
        max_chars: int = 800
    ) -> Optional[str]:
        """
        Fetch webpage HTML asynchronously and extract salient article body text.
        Uses trafilatura if available, falling back to BeautifulSoup paragraph extraction.
        """
        if not url or not url.startswith("http"):
            return None

        lower_url = url.lower()
        # Skip Wikipedia (already has introductory extracts) or non-HTML/media assets
        if "wikipedia.org" in lower_url or any(ext in lower_url for ext in [".pdf", ".jpg", ".png", ".zip", ".mp4", "youtube.com"]):
            return None

        try:
            resp = await client.get(url, timeout=timeout_sec, follow_redirects=True)
            if resp.status_code != 200 or not resp.text:
                return None

            html = resp.text
            extracted_text = None

            # 1. Trafilatura Extraction
            if HAS_TRAFILATURA:
                try:
                    extracted_text = trafilatura.extract(
                        html,
                        include_comments=False,
                        include_tables=False,
                        include_images=False,
                        include_links=False,
                        deduplicate=True
                    )
                except Exception:
                    extracted_text = None

            # 2. BeautifulSoup Fallback
            if not extracted_text:
                soup = BeautifulSoup(html, "html.parser")
                for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
                    tag.decompose()
                paragraphs = [p.get_text(strip=True) for p in soup.find_all("p") if len(p.get_text(strip=True)) > 50]
                if paragraphs:
                    extracted_text = "\n\n".join(paragraphs)

            if not extracted_text or len(extracted_text.strip()) < 80:
                return None

            # 3. Locate Salient Passage Matching Query Keywords
            return self._extract_salient_passage(extracted_text, query, max_chars=max_chars)
        except Exception as e:
            logger.debug(f"Article extraction skipped for {url}: {e}")
            return None

    async def async_search(self, query: str, max_results: int = 16) -> List[Dict[str, str]]:
        """
        Execute concurrent non-blocking web retrieval across Wikipedia, DuckDuckGo,
        and optional Brave Search in sub-second time.
        """
        all_results = []
        seen_texts = set()

        # Detect compound conjunctions for sub-clause querying
        compound_query = None
        clause_splits = re.split(r',\s*(?:and|but)\s+|;\s*', query)
        if len(clause_splits) > 1:
            first_words = clause_splits[0].strip().split()
            second_words = clause_splits[1].strip().split()
            if first_words and len(second_words) >= 3:
                first_subject = first_words[0]
                compound_query = f"{first_subject} {clause_splits[1].strip()}".strip()

        timeout = httpx.Timeout(4.0, connect=2.0)
        limits = httpx.Limits(max_keepalive_connections=10, max_connections=20)
        
        async with httpx.AsyncClient(headers=self.headers, timeout=timeout, limits=limits, follow_redirects=True) as client:
            tasks = [
                self._async_search_wikipedia(client, query, max_results=4),
                self._async_search_duckduckgo(client, query, max_results=6),
                self._async_search_duckduckgo_instant(client, query)
            ]
            if self.brave_api_key:
                tasks.append(self._async_search_brave(client, query, max_results=6))
            if compound_query:
                tasks.append(self._async_search_duckduckgo(client, compound_query, max_results=4))

            gathered_results = await asyncio.gather(*tasks, return_exceptions=True)

            # Unpack gathered tasks safely
            wiki_res = gathered_results[0] if isinstance(gathered_results[0], list) else []
            ddg_res = gathered_results[1] if isinstance(gathered_results[1], list) else []
            instant_res = gathered_results[2] if isinstance(gathered_results[2], dict) else None
            
            brave_res = []
            sub_res = []
            idx = 3
            if self.brave_api_key:
                brave_res = gathered_results[idx] if isinstance(gathered_results[idx], list) else []
                idx += 1
            if compound_query and idx < len(gathered_results):
                sub_res = gathered_results[idx] if isinstance(gathered_results[idx], list) else []

            # 1. Instant Answer
            if instant_res and instant_res.get("snippet"):
                all_results.append(instant_res)
                seen_texts.add((instant_res.get("snippet") or "")[:60].lower())

            # 2. Brave Search (if available)
            for item in brave_res:
                snippet = item.get("snippet", "")
                key = snippet[:60].lower()
                if key and key not in seen_texts:
                    seen_texts.add(key)
                    all_results.append(item)

            # 3. Wikipedia Extracts
            for item in wiki_res:
                snippet = item.get("snippet", "")
                key = snippet[:60].lower()
                if key and key not in seen_texts:
                    seen_texts.add(key)
                    all_results.append(item)

            # 4. DuckDuckGo Results
            for item in ddg_res:
                snippet = item.get("snippet", "")
                key = snippet[:60].lower()
                if key and key not in seen_texts:
                    seen_texts.add(key)
                    all_results.append(item)

            # 5. Compound Sub-Query Results
            for item in sub_res:
                snippet = item.get("snippet", "")
                key = snippet[:60].lower()
                if key and key not in seen_texts:
                    seen_texts.add(key)
                    all_results.append(item)

            # 6. Deep Article Body Enrichment (Trafilatura / BeautifulSoup)
            # Parallel fetch top non-Wikipedia URLs to enrich short snippets into full salient passages
            external_items = [
                item for item in all_results
                if item.get("url") and "wikipedia.org" not in item.get("url", "").lower()
            ][:3]

            if external_items:
                extract_tasks = [
                    self._async_extract_article_content(client, item["url"], query)
                    for item in external_items
                ]
                extracted_passages = await asyncio.gather(*extract_tasks, return_exceptions=True)
                for item, passage in zip(external_items, extracted_passages):
                    if isinstance(passage, str) and len(passage) > len(item.get("snippet", "")):
                        logger.debug(f"Enriched snippet for {item.get('url')} ({len(item.get('snippet', ''))} -> {len(passage)} chars)")
                        item["snippet"] = passage

        logger.info(f"Async search aggregated {len(all_results)} results for '{query}'")
        return all_results[:max_results]

    def search(self, query: str, max_results: int = 16) -> List[Dict[str, str]]:
        """
        Synchronous wrapper for async_search to provide seamless backward compatibility
        with non-async callers, evaluation scripts, and legacy SDK entrypoints.
        """
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            # If already inside an active asyncio event loop, execute in a worker thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(asyncio.run, self.async_search(query, max_results=max_results))
                return future.result()
        else:
            return asyncio.run(self.async_search(query, max_results=max_results))


web_search = WebSearchEngine()
