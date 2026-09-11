# config.py
from pathlib import Path
from typing import Optional
import os
from dotenv import load_dotenv

# Set Hugging Face environment variables to prevent hangs on Windows
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
os.environ.setdefault("HF_HUB_ENABLE_HF_TRANSFER", "0")
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")

# Load environment variables
load_dotenv()

# --- Paths ---
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
METRICS_PATH = BASE_DIR / "metrics.jsonl"
CACHE_PATH = DATA_DIR / "query_cache.json"

# --- Models ---
CROSS_ENCODER_MODEL = 'cross-encoder/ms-marco-MiniLM-L6-v2' # For re-ranking evidence

# LLM Generation Model
GROQ_MODEL = "llama-3.1-8b-instant"  # Super fast Llama 3 on Groq
SPACY_MODEL = "en_core_web_md"

# --- Web Search & Evidence Parameters ---
WEB_SEARCH_ENABLED = True
TOP_K_RETRIEVE = 10     # Max search results to fetch from DuckDuckGo + Wikipedia
TOP_K_RERANK_RESULTS = 3 # Top evidence items after re-ranking sent to LLM
CONFIDENCE_THRESHOLD = 0.50

# --- Cache Settings ---
CACHE_ENABLED = True
CACHE_MAX_SIZE = 1000
CACHE_TTL_SECONDS = 3600  # 1 hour

# --- App Settings ---
APP_TITLE = "LLM-Powered Fact Checker"
APP_VERSION = "2.0.0"
MAX_INPUT_LENGTH = 1000
HOST = os.getenv("HOST", "127.0.0.1")
PORT = int(os.getenv("PORT", "8000"))

