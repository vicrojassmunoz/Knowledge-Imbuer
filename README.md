# Knowledge Imbuer

I got tired of opening 12 tabs every morning just to find 2 things worth reading. So I built this.

It scrapes AI/ML news from Arxiv, HuggingFace, Papers With Code and Hacker News, runs everything through an LLM with the personality of a cynical senior engineer, and sends only what actually matters to your Telegram and email.

## How it works

```
fetch → dedup → LLM filter → notify
```

1. Pulls from RSS feeds + HN Algolia API in parallel
2. Skips anything it's already seen (MD5 hash of URL, stored locally)
3. Asks Qwen3-32b (via Groq) to score each item 1–10 and write a one-liner. Hype dies here.
4. Sends the survivors to Telegram + email

## Setup

```bash
uv sync
cp .env.example .env  # fill in your keys
python main.py
```

You'll need:

| Variable | What for |
|---|---|
| `GROQ_API_KEY` | LLM filtering |
| `RESEND_API_KEY` | Email delivery |
| `EMAIL_FROM` / `EMAIL_TO` | Email addresses |
| `TELEGRAM_TOKEN` / `TELEGRAM_CHAT_ID` | Telegram bot |

## Config

Everything tunable lives in `config.toml` — sources, scoring threshold, the model, how many items to process, the system prompt. The system prompt is where the editorial voice lives, mess with it if you want different vibes.

```toml
[filter]
min_score = 6        # 1–10, raise this to be more ruthless
max_input_items = 50
max_workers = 3      # parallel Groq calls, careful with rate limits
```

## Run it on a schedule

```bash
# twice a day, 8am and 6pm
0 8,18 * * * cd /path/to/project && .venv/bin/python main.py
```

## Requirements

Python 3.14+
