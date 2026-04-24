import logging
import os
from dotenv import load_dotenv
import tomllib
from pathlib import Path

load_dotenv()

CONFIG_PATH = Path(__file__).parent.parent / "infrastructure" / "environments" / "config.toml"

with open(CONFIG_PATH, "rb") as f:
    _config = tomllib.load(f)

RSS_SOURCES = [(s["url"], s["name"]) for s in _config["rss_sources"]["sources"]]
HN_QUERY = _config["hn"]["query"]
HN_URL = _config["hn"]["url"]
HN_MIN_POINTS = _config["hn"]["min_points"]
REDDIT_BASE_URL = _config["reddit"]["base_url"]
REDDIT_MIN_UPVOTES = _config["reddit"]["min_upvotes"]
REDDIT_MAX_RESULTS = _config["reddit"]["max_results"]
REDDIT_SUBREDDITS = _config["reddit"]["subreddits"]

HISTORY_PATH = Path(__file__).parent.parent / _config["history"]["path"]
MAX_HISTORY = _config["history"]["max_entries"]

FILTER_MAX_INPUT = _config["filter"]["max_input_items"]
FILTER_MAX_WORKERS = _config["filter"]["max_workers"]
FILTER_MIN_SCORE = _config["filter"]["min_score"]
_active_model_key = _config["models"]["active"]
FILTER_MODEL = _config["models"][_active_model_key]
FILTER_TEMPERATURE = _config["filter"]["temperature"]
FILTER_MAX_TOKENS = _config["filter"]["max_tokens"]
SYSTEM_PROMPT = _config["filter"]["system_prompt"]

PREFILTER_KEYWORDS = _config["prefilter"]["keywords"]
PREFILTER_BLACKLIST = _config["prefilter"]["blacklist"]
PREFILTER_MAX_AGE_HOURS = _config["prefilter"]["max_age_hours"]

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def setup_logging() -> None:
    level = _config["logging"]["level"].upper()
    logging.basicConfig(
        level=getattr(logging, level, logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )