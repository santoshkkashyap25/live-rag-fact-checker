# core/web_search.py
import re
import requests
from bs4 import BeautifulSoup
import urllib.parse
import logging
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class WebSearchEngine:
    """
    Real-time web search engine using DuckDuckGo and Wikipedia APIs.
    Zero-key, zero-dependency search that fetches live evidence and citations.
    """

    def __init__(self):
        self.headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        }

    def search_duckduckgo(self, query: str, max_results: int = 6) -> List[Dict[str, str]]:
        """
        Search DuckDuckGo HTML endpoint for live web results.
        Returns a list of dicts with title, snippet, and url.
        """
        results = []
        try:
            url = "https://html.duckduckgo.com/html/"
            data = {"q": query}
            response = requests.post(url, data=data, headers=self.headers, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"DuckDuckGo returned status {response.status_code}")
                return results

            soup = BeautifulSoup(response.text, "html.parser")
            for r in soup.select(".result"):
                title_elem = r.select_one(".result__title")
                snippet_elem = r.select_one(".result__snippet")
                url_elem = r.select_one(".result__url")
                link_elem = r.select_one("a.result__url") or r.select_one(".result__title a")

                if title_elem and snippet_elem:
                    title = title_elem.get_text(strip=True)
                    snippet = snippet_elem.get_text(strip=True)
                    
                    # Extract direct destination URL
                    href = ""
                    if link_elem and link_elem.get("href"):
                        raw_href = link_elem["href"]
                        # DuckDuckGo wraps links in /l/?uddg=...
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

            logger.info(f"DuckDuckGo search retrieved {len(results)} results for '{query}'")
        except Exception as e:
            logger.error(f"DuckDuckGo search error: {e}")

        return results

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
        words = [w for w in re.findall(r'\b[a-zA-Z0-9\-]+\b', text) if w.lower() not in stop_words]
        return " ".join(words[:8])

    def search_wikipedia(self, query: str, max_results: int = 4) -> List[Dict[str, str]]:
        """
        Search Wikipedia REST API for factual extracts and definitions in an optimized generator request.
        """
        results = []
        seen_titles = set()
        wiki_headers = {
            "User-Agent": "FactGuardAI/2.0 (factguard-fact-checker@example.com)"
        }
        
        # Build search terms: prioritize refined keywords to strip filler words
        search_terms = []
        kw = self._extract_keywords(query)
        if kw and kw.lower() != query.lower():
            search_terms.append(kw)
        search_terms.append(query)

        url = "https://en.wikipedia.org/w/api.php"

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
                response = requests.get(url, params=params, headers=wiki_headers, timeout=5)
                if response.status_code == 200:
                    data = response.json()
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
            except Exception as ge:
                logger.debug(f"Wikipedia generator search issue for '{term}': {ge}")

        if results:
            logger.info(f"Wikipedia generator search retrieved {len(results)} extracts for '{query}'")
            return results[:max_results]

        # 2. Fallback: list=search with HTML snippet cleaning
        try:
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": max_results,
            }
            response = requests.get(url, params=params, headers=wiki_headers, timeout=4)
            if response.status_code == 200:
                data = response.json()
                for item in data.get("query", {}).get("search", []):
                    title = item.get("title", "")
                    raw_snippet = item.get("snippet", "")
                    clean_snippet = BeautifulSoup(raw_snippet, "html.parser").get_text(separator=" ", strip=True)
                    clean_snippet = " ".join(clean_snippet.split())
                    article_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"
                    if clean_snippet and title not in seen_titles:
                        seen_titles.add(title)
                        results.append({
                            "title": f"{title} (Wikipedia)",
                            "snippet": clean_snippet,
                            "url": article_url,
                            "source": "Wikipedia"
                        })
            logger.info(f"Wikipedia fallback search retrieved {len(results)} results for '{query}'")
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")

        return results[:max_results]

    def search_duckduckgo_instant(self, query: str) -> Optional[Dict[str, str]]:
        """
        Query DuckDuckGo Instant Answer API for direct definition / fact summary.
        """
        try:
            url = "https://api.duckduckgo.com/"
            params = {
                "q": query,
                "format": "json",
                "no_redirect": "1",
                "no_html": "1",
                "skip_disambig": "1"
            }
            resp = requests.get(url, params=params, headers=self.headers, timeout=6)
            if resp.status_code == 200:
                data = resp.json()
                abstract = data.get("AbstractText", "").strip()
                source_url = data.get("AbstractURL", "")
                source_name = data.get("AbstractSource", "DuckDuckGo Instant Answer")
                heading = data.get("Heading", query)

                if abstract:
                    return {
                        "title": f"{heading} Summary",
                        "snippet": abstract,
                        "url": source_url or "https://duckduckgo.com",
                        "source": source_name or "DuckDuckGo"
                    }
        except Exception as e:
            logger.debug(f"DuckDuckGo Instant Answer error: {e}")
        return None

    def search(self, query: str, max_results: int = 10) -> List[Dict[str, str]]:
        """
        Aggregate results from DuckDuckGo Instant Answer, DuckDuckGo Web, and Wikipedia in parallel.
        Deduplicates results and returns structured evidence items.
        """
        all_results = []
        seen_texts = set()

        # Run web searches concurrently to minimize latency (2-3s instead of 25s)
        instant = None
        wiki_results = []
        ddg_results = []

        with ThreadPoolExecutor(max_workers=3) as executor:
            future_instant = executor.submit(self.search_duckduckgo_instant, query)
            future_wiki = executor.submit(self.search_wikipedia, query, 4)
            future_ddg = executor.submit(self.search_duckduckgo, query, 6)

            try:
                instant = future_instant.result(timeout=5)
            except Exception as e:
                logger.debug(f"Instant search error: {e}")

            try:
                wiki_results = future_wiki.result(timeout=8)
            except Exception as e:
                logger.warning(f"Wiki search error: {e}")

            try:
                ddg_results = future_ddg.result(timeout=8)
            except Exception as e:
                logger.warning(f"DuckDuckGo search error: {e}")

        # 1. Instant Answer summary (if available)
        if instant and instant.get("snippet"):
            all_results.append(instant)
            seen_texts.add(instant["snippet"][:60].lower())

        # 2. Wikipedia Search
        for w in (wiki_results or []):
            key = w["snippet"][:60].lower()
            if key not in seen_texts:
                seen_texts.add(key)
                all_results.append(w)

        # 3. DuckDuckGo Web Search
        for d in (ddg_results or []):
            key = d["snippet"][:60].lower()
            if key not in seen_texts:
                seen_texts.add(key)
                all_results.append(d)

        logger.info(f"Total live search results aggregated: {len(all_results)} for '{query}'")
        return all_results[:max_results]

web_search = WebSearchEngine()
