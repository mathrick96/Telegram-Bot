# LangBot – Daily AI‑Generated Language Stories for Telegram

LangBot delivers one short story per user each day in the language and proficiency level they specify. It uses the **Telegram Bot API** for interaction, **OpenAI** for text generation, and a lightweight **SQLite database** to store user preferences and prevent duplicate deliveries within the same day.

---

## Features

* Daily story scheduling with user-defined delivery time and timezone awareness, including daylight‑saving adjustments
* Language and CEFR level selection drawn from a configurable list in `config.json`
* Using `/configure`, users can update their language and level, triggering immediate rescheduling for upcoming deliveries; timezone and delivery time are locked after the initial setup
* Users can pause daily stories with `/stop` and resume through `/configure`
* One story per 24 hours enforced by the scheduler logic
* Planned enhancements such as translations, vocabulary lists, and cloud deployment scripts (not yet implemented)

---

## Requirements

* Python **3.12** runtime
* **Telegram Bot API token** via `TELEGRAM_BOT_KEY`
* **OpenAI API key** via `OPENAI_API_KEY`

Copy `.env.example` to `.env` and fill in these values (and optional `ADMIN_ID`), or export them in your environment before running the bot.

### Environment Variables

The application expects the following variables:

* `TELEGRAM_BOT_KEY` – Telegram bot token loaded at startup
* `OPENAI_API_KEY` – OpenAI key used to initialize the async client
* `ADMIN_ID` – (optional) Telegram user ID permitted to run admin commands like `/deleteuser` and `/logdb` for maintenance
---

## Quick Start

Before running the bot, copy the example environment file and add your API keys:

```bash
cp .env.example .env
# edit .env to include TELEGRAM_BOT_KEY and OPENAI_API_KEY
```


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
### Code Quality

This project uses [pre-commit](https://pre-commit.com/) to run **Black**, **Ruff**, and **MyPy** on every commit.
Install the hooks after setting up the environment:

```bash
pipenv install --dev
pre-commit install
pre-commit run --all-files
```


---

## Project Structure

```
src/
  bot/
    main.py       # application entry point and setup
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
* `/configure` – interactive setup for language, level, timezone, and daily delivery time; timezone and delivery time cannot be changed after this initial configuration
* `/help` – list of available commands
* `/stop` – pause daily delivery
* `/cancel` – abort current setup process

### Admin Commands

The following commands are restricted to the Telegram user ID specified in `ADMIN_ID`:

* `/deleteuser <user_id>` – remove a user from the database. Requires `ADMIN_ID`.
* `/logdb` – log the contents of the SQLite database for debugging.

---

## How It Works

1. Users choose a language, CEFR level, timezone, and delivery time. The chosen timezone and delivery time are locked after the initial setup.
2. The scheduler computes the next send time, ensuring at least 24 hours between stories and adjusting for timezone changes.
3. At send time, the bot generates a story via OpenAI and records the delivery timestamp in the database to prevent duplicates.
4. On bot restart, all configured jobs are reloaded to preserve scheduling.

---

## Development Notes

* Database and configuration utilities reside under `src/bot/`.
* `log_all_users()` and related diagnostics can assist with debugging or inspecting the SQLite data store. The `/logdb` command exposing this information is restricted to the admin.
* The codebase is fully containerized, making it straightforward to deploy to a cloud environment when desired.

---

## Roadmap

* Vocabulary CSV export
* User-triggered translations
* Cloud deployment scripts
* Unit tests and CI pipeline

---

## License

This project is licensed under the terms of the [MIT License](LICENSE).