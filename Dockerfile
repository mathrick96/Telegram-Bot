# ---- builder ----
FROM python:3.12-slim AS builder
WORKDIR /app
COPY Pipfile Pipfile.lock ./
RUN pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --deploy --system

# ---- runtime ----
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local /usr/local

COPY src/ /app/src/

# Option A: run from /app/src (common for “src/” layout)
WORKDIR /app/src
ENTRYPOINT ["python", "-m", "bot.story"]
