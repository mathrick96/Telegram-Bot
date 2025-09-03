# LangBot – Daily Language-Learning Bot for Telegram

LangBot sends each user a short, AI-generated story in their chosen language every day.
The bot is built with the Telegram Bot API, OpenAI, and a lightweight SQLite store to
remember user preferences and enforce one story per day.

## Features

* Daily stories at a scheduled hour – configurable per user.
* Fixed timezone per user – collected at first setup and used to schedule deliveries.
* Daylight-saving aware – schedule calculations rely on standard IANA timezone data.
* One story per day – delivery tracker prevents multiple sends in the same local day.
* Deferred schedule changes – time edits made after today’s story has been delivered take effect starting tomorrow.
* Language & level selection – any language in config.json plus CEFR levels A1–C2.
* Optional full translation & vocabulary list (roadmap).

## Requirements

| Component          | Purpose                            |
| ------------------ | ---------------------------------- |
| Python 3.12        | runtime (slim Docker base image)   |
| TELEGRAM\_BOT\_KEY | Telegram Bot API token             |
| OPENAI\_API\_KEY   | OpenAI API key for text generation |


A `.env` file (used by Docker Compose) can hold these keys:

```
TELEGRAM_BOT_KEY=...
OPENAI_API_KEY=...
```

## Environment Variables

The bot expects the following variables in the environment or `.env` file:

* `TELEGRAM_BOT_KEY` – Telegram Bot API token
* `OPENAI_API_KEY` – OpenAI API key for text generation

## Quick Start

### Docker (recommended)

```bash
cd Telegram-Bot
docker compose up -d --build
```

The container runs `python -m bot.main` and mounts `src/` for live code editing.

### Local Python

```bash
pipenv install
pipenv run python -m bot.main
```

## Project Layout

```
src/
  bot/
    main.py       # Telegram handlers, scheduling, DB access
    story.py      # OpenAI requests for story generation
    paths.py      # helper paths (config & data)
    config.json   # list of topics, CEFR levels, and languages
data/
  users.db        # SQLite database created at runtime
```

## Configuration Flow

* `/start` – greets user and triggers setup.
* `/help` – list available commands.
* User selects:

  * Language (emoji-annotated list from config.json)
  * CEFR level
  * Timezone (IANA name, stored permanently)
  * Daily delivery hour
* Bot schedules the next story using the chosen timezone.

## Delivery Logic

* At send time, the bot checks whether `last_sent` equals today’s date
  (in the user’s timezone). If so, it skips sending.
* After a successful send:

  * `last_sent` is updated.
  * Any `pending_delivery_time` is applied for tomorrow’s job.
* The JobQueue is rebuilt on restart so scheduled deliveries persist.

## Development Tips

* `src/bot/main.py` contains helper `log_all_users()` to inspect the
  SQLite table.
* Use the `docker compose logs -f` command or standard logging to trace
  interactions.
* Topics and language lists can be extended by editing `config.json`.

## Roadmap

* Vocabulary CSV export
* User-triggered full translations
* Cloud deployment scripts
* Unit tests and CI pipeline

Happy language learning!
