# core/web_search.py
import requests
from bs4 import BeautifulSoup
import urllib.parse
import logging
from typing import List, Dict, Any, Optional

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

    def search_wikipedia(self, query: str, max_results: int = 4) -> List[Dict[str, str]]:
        """
        Search Wikipedia REST search API for factual / encyclopedic claims.
        """
        results = []
        try:
            url = "https://en.wikipedia.org/w/api.php"
            params = {
                "action": "query",
                "list": "search",
                "srsearch": query,
                "format": "json",
                "srlimit": max_results,
            }
            wiki_headers = {
                "User-Agent": "FactGuardAI/2.0 (factguard-fact-checker@example.com)"
            }
            response = requests.get(url, params=params, headers=wiki_headers, timeout=8)
            
            if response.status_code != 200:
                return results

            data = response.json()
            search_items = data.get("query", {}).get("search", [])

            for item in search_items:
                title = item.get("title", "")
                raw_snippet = item.get("snippet", "")
                # Strip HTML tags like <span class="searchmatch"> while preserving whitespace
                clean_snippet = BeautifulSoup(raw_snippet, "html.parser").get_text(separator=" ", strip=True)
                clean_snippet = " ".join(clean_snippet.split())
                article_url = f"https://en.wikipedia.org/wiki/{urllib.parse.quote(title.replace(' ', '_'))}"

                if clean_snippet:
                    results.append({
                        "title": f"{title} (Wikipedia)",
                        "snippet": clean_snippet,
                        "url": article_url,
                        "source": "Wikipedia"
                    })

            logger.info(f"Wikipedia search retrieved {len(results)} results for '{query}'")
        except Exception as e:
            logger.error(f"Wikipedia search error: {e}")

        return results

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
        Aggregate results from DuckDuckGo Instant Answer, DuckDuckGo Web, and Wikipedia.
        Deduplicates results and returns structured evidence items.
        """
        all_results = []
        seen_texts = set()

        # 1. Instant Answer summary (if available)
        instant = self.search_duckduckgo_instant(query)
        if instant:
            all_results.append(instant)
            seen_texts.add(instant["snippet"][:60].lower())

        # 2. Wikipedia Search
        wiki_results = self.search_wikipedia(query, max_results=4)
        for w in wiki_results:
            key = w["snippet"][:60].lower()
            if key not in seen_texts:
                seen_texts.add(key)
                all_results.append(w)

        # 3. DuckDuckGo Web Search
        ddg_results = self.search_duckduckgo(query, max_results=6)
        for d in ddg_results:
            key = d["snippet"][:60].lower()
            if key not in seen_texts:
                seen_texts.add(key)
                all_results.append(d)

        logger.info(f"Total live search results aggregated: {len(all_results)} for '{query}'")
        return all_results[:max_results]

web_search = WebSearchEngine()
