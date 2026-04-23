# Knowledge Imbuer

I got tired of opening 12 tabs every morning just to find 2 things worth reading. So I built this.

It scrapes AI/ML news from Arxiv, HuggingFace Blog, HF Daily Papers and Hacker News, runs everything through an LLM with the personality of a cynical senior engineer, and sends only what actually matters to your Telegram and email.

## How it works

```
fetch → dedup → prefilter → LLM filter → notify
```

1. Pulls from RSS feeds (Arxiv CS.AI, Arxiv CS.LG, HuggingFace Blog, HF Daily Papers) + HN Algolia API in parallel
2. Skips anything it's already seen (MD5 hash of URL, stored in `data/history.json`)
3. Drops items older than 24 hours, anything matching a blacklist (hiring, funding, events), and anything without a keyword hit (llm, transformer, benchmark, etc.)
4. Asks Qwen3-32b (via Groq) to score each remaining item 1–10 and write a one-liner. Items below the threshold are dropped. Hype dies here.
5. Sends the survivors to Telegram (HTML) + email (Resend)

## Setup

```bash
uv sync
cp .env.example .env  # fill in your keys
python main.py
```

Create a `.env` file with:

```env
GROQ_API_KEY=
RESEND_API_KEY=
EMAIL_FROM=
EMAIL_TO=
TELEGRAM_TOKEN=
TELEGRAM_CHAT_ID=
```

| Variable | What for |
|---|---|
| `GROQ_API_KEY` | LLM filtering via Groq |
| `RESEND_API_KEY` | Email delivery via Resend |
| `EMAIL_FROM` / `EMAIL_TO` | Sender and recipient addresses |
| `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | Telegram bot credentials |

## Config

Everything tunable lives in `config.toml` — sources, scoring threshold, the model, how many items to process, the system prompt. The system prompt is where the editorial voice lives, mess with it if you want different vibes.

```toml
[filter]
min_score = 7        # 1–10, raise this to be more ruthless
max_input_items = 30
max_workers = 2      # parallel Groq calls, careful with rate limits
```

## Run it on a schedule

```bash
# twice a day, 8am and 6pm
0 8,18 * * * cd /path/to/project && .venv/bin/python main.py
```

## Tests

```bash
uv run pytest
```

All external calls (Groq, httpx, Resend, feedparser) are mocked. 66 tests covering hash generation, dedup logic, prefilter keyword/date rules, LLM filter behaviour, notifier formatting, and the full pipeline flow.

## Requirements

Python 3.14+
