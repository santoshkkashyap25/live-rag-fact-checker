# core/data_scraper.py
import requests
from bs4 import BeautifulSoup
import feedparser
import pandas as pd
from datetime import datetime
from typing import List, Dict
import logging
from config import (
    PIB_RSS_URL, FACTLY_RSS_URL, WEBQOOF_RSS_URL, 
    NEWSCHECKER_RSS_URL, FACTS_CSV_PATH, SCRAPE_LIMIT_PER_SOURCE
)

logger = logging.getLogger(__name__)

class DataScraper:
    """Scrapes verified facts from trusted sources"""
    
    def __init__(self):
        self.sources = {
            'PIB India': PIB_RSS_URL,
            'Factly': FACTLY_RSS_URL,
            'WebQoof (The Quint)': WEBQOOF_RSS_URL,
            'Newschecker': NEWSCHECKER_RSS_URL
        }
    
    def _scrape_rss(self, source_name: str, url: str) -> List[Dict[str, str]]:
        """Generic RSS scraper for fact-checking sources"""
        try:
            logger.info(f"Scraping {source_name} from {url}...")
            
            # Use custom headers to avoid bot-blocking
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=15)
            feed = feedparser.parse(response.content)
            
            facts = []
            
            # Use limit from config
            entries = feed.entries[:SCRAPE_LIMIT_PER_SOURCE]
            
            for entry in entries:
                # More robust content extraction
                content = entry.get('summary', 
                                   entry.get('description', 
                                            entry.get('content', [{'value': ''}])[0].get('value', '')))
                
                # Clean HTML if present
                clean_content = BeautifulSoup(content, "html.parser").get_text()
                
                # Title often contains the core claim in fact-check feeds
                title = entry.get('title', '')
                
                # Heuristic: Prefer the title for government releases, 
                # but the summary/description for factcheckers (which often debunk the title)
                if source_name == 'PIB India':
                    statement = title
                else:
                    # For fact checkers, the title is usually "Fact Check: [Claim]"
                    # We want to extract the claim part
                    statement = title.replace("Fact Check:", "").replace("FACT CHECK:", "").strip()
                    if len(statement.split()) < 4:
                        statement = clean_content
                
                statement = self._clean_text(statement)
                
                # Lower the threshold slightly to accept more facts
                if len(statement.split()) > 4:
                    facts.append({
                        'statement': statement,
                        'source': source_name,
                        'url': entry.get('link', ''),
                        'date': entry.get('published', datetime.now().isoformat()),
                        'category': 'fact_check' if source_name != 'PIB India' else 'government_announcement'
                    })
            
            logger.info(f"✓ Successfully scraped {len(facts)} facts from {source_name}")
            return facts
            
        except Exception as e:
            logger.error(f"Error scraping {source_name}: {e}")
            return []
    
    
    def _clean_text(self, text: str) -> str:
        """Clean scraped text"""
        # Remove extra whitespace
        text = ' '.join(text.split())
        # Remove common prefixes
        prefixes = ['Press Release:', 'PIB:', 'Government of India:']
        for prefix in prefixes:
            if text.startswith(prefix):
                text = text[len(prefix):].strip()
        return text
    
    def scrape_all_sources(self) -> pd.DataFrame:
        """Scrape all configured sources and return DataFrame"""
        all_facts = []
        
        for name, url in self.sources.items():
            source_facts = self._scrape_rss(name, url)
            all_facts.extend(source_facts)
        
        if len(all_facts) == 0:
            logger.error("No facts scraped from any source!")
            return pd.DataFrame(columns=['statement', 'source', 'url', 'date', 'category'])
        
        df = pd.DataFrame(all_facts)
        return df
    
    def upsert_to_csv(self, new_df: pd.DataFrame) -> pd.DataFrame:
        """Merge new facts with existing ones, deduplicating by statement and URL"""
        if FACTS_CSV_PATH.exists():
            try:
                existing_df = pd.read_csv(FACTS_CSV_PATH)
                logger.info(f"Loaded {len(existing_df)} existing facts from storage")
                
                # Combine and deduplicate
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                
                # Deduplicate based on statement (semantic) and URL (source-level)
                initial_count = len(combined_df)
                combined_df.drop_duplicates(subset=['statement'], keep='first', inplace=True)
                combined_df.drop_duplicates(subset=['url'], keep='first', inplace=True, ignore_index=True)
                
                new_added = len(combined_df) - len(existing_df)
                logger.info(f"Added {new_added} unique new facts. Total in storage: {len(combined_df)}")
                
                df_to_save = combined_df
            except Exception as e:
                logger.error(f"Error merging with existing CSV: {e}. Overwriting with new data.")
                df_to_save = new_df
        else:
            logger.info("No existing storage found. Creating new fact database.")
            df_to_save = new_df
        
        # Save to CSV
        df_to_save.to_csv(FACTS_CSV_PATH, index=False)
        logger.info(f"Successfully saved {len(df_to_save)} facts to {FACTS_CSV_PATH}")
        return df_to_save

data_scraper = DataScraper()
