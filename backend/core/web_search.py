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
        self.session = requests.Session()
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
        self.session.headers.update(self.headers)

    def search_duckduckgo(self, query: str, max_results: int = 6) -> List[Dict[str, str]]:
        """
        Search DuckDuckGo HTML endpoint with automatic fallback to DuckDuckGo Lite.
        Returns a list of dicts with title, snippet, and url.
        """
        results = []
        
        # 1. Primary: DuckDuckGo HTML GET
        try:
            url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(query)}"
            response = self.session.get(url, timeout=8)
            
            if response.status_code == 200:
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
                logger.info(f"DuckDuckGo HTML search retrieved {len(results)} results for '{query}'")
                return results
            else:
                logger.warning(f"DuckDuckGo HTML returned 0 results or status {response.status_code}, attempting Lite fallback...")
        except Exception as e:
            logger.warning(f"DuckDuckGo HTML search attempt failed: {e}, falling back to Lite...")

        # 2. Resilient Fallback: DuckDuckGo Lite POST
        try:
            lite_url = "https://lite.duckduckgo.com/lite/"
            lite_resp = self.session.post(lite_url, data={"q": query}, timeout=8)
            if lite_resp.status_code == 200:
                soup = BeautifulSoup(lite_resp.text, "html.parser")
                titles = soup.select("a.result-link")
                snippets = soup.select("td.result-snippet")
                
                for title_elem, snip_elem in zip(titles, snippets):
                    title = title_elem.get_text(strip=True)
                    href = title_elem.get("href", "")
                    # Extract target URL if wrapped
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
                
                logger.info(f"DuckDuckGo Lite search retrieved {len(results)} results for '{query}'")
        except Exception as e:
            logger.error(f"DuckDuckGo Lite fallback error: {e}")

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
        tokens = [w for w in re.findall(r'[a-zA-Z0-9\+\-]+', text) if w.lower() not in stop_words]
        # Prevent query collapse if text is dominated by stop words (e.g. famous quotes)
        if len(tokens) < 3:
            raw_tokens = re.findall(r'[a-zA-Z0-9\+\-]+', text)
            if raw_tokens:
                return " ".join(raw_tokens[:8])
        return " ".join(tokens[:8])

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
                            # Verify that at least one core keyword appears in title or extract to avoid noisy matches
                            core_terms = [t.lower() for t in re.findall(r'\b[a-zA-Z0-9]{3,}\b', kw) if len(t) > 2]
                            text_check = f"{title} {extract}".lower()
                            if core_terms and not any(term in text_check for term in core_terms):
                                logger.debug(f"Skipping noisy Wikipedia result '{title}' (no core keyword overlap)")
                                continue

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

    def search(self, query: str, max_results: int = 16) -> List[Dict[str, str]]:
        """
        Aggregate results from DuckDuckGo Instant Answer, DuckDuckGo Web, and Wikipedia in parallel.
        Deduplicates results and returns structured evidence items.
        """
        all_results = []
        seen_texts = set()

        # Check for compound conjunctions (e.g. "X, and Y") to retrieve targeted secondary clause evidence
        compound_query = None
        clause_splits = re.split(r',\s*(?:and|but)\s+|;\s*', query)
        if len(clause_splits) > 1:
            first_words = clause_splits[0].strip().split()
            second_words = clause_splits[1].strip().split()
            if first_words and len(second_words) >= 3:
                first_subject = first_words[0]
                compound_query = f"{first_subject} {clause_splits[1].strip()}".strip()

        # Run web searches concurrently to minimize latency (2-3s instead of 25s)
        instant = None
        wiki_results = []
        ddg_results = []
        ddg_sub_results = []

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_instant = executor.submit(self.search_duckduckgo_instant, query)
            future_wiki = executor.submit(self.search_wikipedia, query, 4)
            future_ddg = executor.submit(self.search_duckduckgo, query, 6)
            future_sub = executor.submit(self.search_duckduckgo, compound_query, 4) if compound_query else None

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

            if future_sub:
                try:
                    ddg_sub_results = future_sub.result(timeout=8)
                except Exception as e:
                    logger.debug(f"Sub-query search error: {e}")

        # 1. Instant Answer summary (if available)
        if instant and instant.get("snippet"):
            all_results.append(instant)
            seen_texts.add((instant.get("snippet") or "")[:60].lower())

        # 2. DuckDuckGo Web Search
        for d in (ddg_results or []):
            snippet = d.get("snippet") or ""
            key = snippet[:60].lower()
            if key and key not in seen_texts:
                seen_texts.add(key)
                all_results.append(d)

        # 3. DuckDuckGo Compound Sub-Query Search
        for sub in (ddg_sub_results or []):
            snippet = sub.get("snippet") or ""
            key = snippet[:60].lower()
            if key and key not in seen_texts:
                seen_texts.add(key)
                all_results.append(sub)

        # 4. Wikipedia Search
        for w in (wiki_results or []):
            snippet = w.get("snippet") or ""
            key = snippet[:60].lower()
            if key and key not in seen_texts:
                seen_texts.add(key)
                all_results.append(w)

        logger.info(f"Total live search results aggregated: {len(all_results)} for '{query}'")
        return all_results[:max_results]

web_search = WebSearchEngine()
