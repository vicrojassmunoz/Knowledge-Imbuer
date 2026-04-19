import logging
import os
from dotenv import load_dotenv
import tomllib
from pathlib import Path

CONFIG_PATH = Path(__file__).parent.parent / "config.toml"

with open(CONFIG_PATH, "rb") as f:
    _config = tomllib.load(f)

RSS_SOURCES = [(s["url"], s["name"]) for s in _config["rss_sources"]["sources"]]
HN_QUERY = _config["hn"]["query"]
HN_URL = _config["hn"]["url"]
HN_MIN_POINTS = _config["hn"]["min_points"]

def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S",
    )

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
EMAIL_TO = os.getenv("EMAIL_TO")