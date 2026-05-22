# config.py
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
FACTS_CSV_PATH = DATA_DIR / "trusted_facts.csv"
VECTOR_INDEX_PATH = DATA_DIR / "faiss_index.bin"
BM25_INDEX_PATH = DATA_DIR / "bm25_index.pkl"
METRICS_PATH = BASE_DIR / "metrics.jsonl"
CACHE_PATH = DATA_DIR / "query_cache.json"

# --- Models ---
EMBEDDING_MODEL = 'all-MiniLM-L6-v2'  # 384d, very fast
CROSS_ENCODER_MODEL = 'cross-encoder/ms-marco-MiniLM-L-6-v2' # For re-ranking

# LLM Generation Model
GROQ_MODEL = "llama-3.1-8b-instant"  # Super fast Llama 3 on Groq
SPACY_MODEL = "en_core_web_md"

# --- RAG Pipeline Parameters ---
TOP_K_RETRIEVE = 15     # Number of docs to fetch from Vector DB (FAISS) + BM25 combined
TOP_K_RERANK_RESULTS = 3 # Number of top docs after re-ranking to send to LLM
CONFIDENCE_THRESHOLD = 0.50
SIMILARITY_MATCH_THRESHOLD = 0.85

# --- Cache Settings ---
CACHE_ENABLED = True
CACHE_MAX_SIZE = 1000
CACHE_TTL_SECONDS = 3600  # 1 hour

# --- App Settings ---
APP_TITLE = "LLM-Powered Fact Checker"
APP_VERSION = "2.0.0"
MAX_INPUT_LENGTH = 1000

# --- Data Scraping Settings ---
PIB_RSS_URL = "https://www.pib.gov.in/RssMain.aspx?ModId=6&Lang=1&reg=3"
FACTLY_RSS_URL = "https://factly.in/feed/"
WEBQOOF_RSS_URL = "https://www.thequint.com/news/webqoof/rss"
NEWSCHECKER_RSS_URL = "https://newschecker.in/feed/"

SCRAPE_ENABLED = os.getenv("ENABLE_SCRAPING", "false").lower() == "true"
SCRAPE_INTERVAL_HOURS = 24
SCRAPE_LIMIT_PER_SOURCE = 50
