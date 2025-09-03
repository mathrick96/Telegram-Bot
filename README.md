# LangBot – Daily AI‑Generated Language Stories for Telegram

LangBot delivers one short story per user each day in the language and proficiency level they specify. It uses the **Telegram Bot API** for interaction, **OpenAI** for text generation, and a lightweight **SQLite database** to store user preferences and prevent duplicate deliveries within the same day.

---

## Features

* Daily story scheduling with user-defined delivery time and timezone awareness, including daylight‑saving adjustments
* Language and CEFR level selection drawn from a configurable list in `config.json`
* Deferred schedule changes applied the day after a story has already been sent
* One story per 24 hours enforced by the scheduler logic
* Planned enhancements such as translations, vocabulary lists, and cloud deployment scripts (not yet implemented)

---

## Requirements

* Python **3.12** runtime
* **Telegram Bot API token** via `TELEGRAM_BOT_KEY`
* **OpenAI API key** via `OPENAI_API_KEY`

Store these keys in a `.env` file or export them in your environment before running the bot.

### Environment Variables

The application expects the following variables:

* `TELEGRAM_BOT_KEY` – Telegram bot token loaded at startup
* `OPENAI_API_KEY` – OpenAI key used to initialize the async client
* `ADMIN_ID` – (optional) Telegram user ID permitted to run `/deleteuser` for maintenance

---

## Quick Start

### Docker (recommended)

```bash
docker compose up -d --build
```

The container runs `python -m bot.main` and mounts `src/` for live editing.

### Local Python

```bash
pipenv install
pipenv run python -m bot.main
```

---

## Project Structure

```
src/
  bot/
    main.py       # Telegram handlers, scheduling, DB access
    story.py      # OpenAI requests for story generation
    scheduler.py  # job-queue logic
    handlers.py   # conversation flow and commands
    db.py         # SQLite utility functions
    paths.py      # common paths (config & data)
    config.json   # topics, languages, CEFR levels
data/
  users.db        # created at runtime
```

---

## Configuration Flow

* `/start` – introduction and setup guidance
* `/configure` – interactive setup for language, level, timezone, and daily delivery time
* `/help` – list of available commands
* `/stop` – pause daily delivery
* `/cancel` – abort current setup process

---

## How It Works

1. Users choose a language, CEFR level, timezone, and delivery time.
2. The scheduler computes the next send time, ensuring at least 24 hours between stories and adjusting for timezone changes.
3. At send time, the bot generates a story via OpenAI and records the delivery timestamp in the database to prevent duplicates.
4. On bot restart, all configured jobs are reloaded to preserve scheduling.

---

## Development Notes

* Database and configuration utilities reside under `src/bot/`.
* `log_all_users()` and related diagnostics can assist with debugging or inspecting the SQLite data store.
* The codebase is fully containerized, making it straightforward to deploy to a cloud environment when desired.

---

## Roadmap

* Vocabulary CSV export
* User-triggered translations
* Cloud deployment scripts
* Unit tests and CI pipeline

---