# ---- builder ----
FROM python:3.11-slim AS builder
WORKDIR /app
COPY Pipfile Pipfile.lock ./
RUN pip install --upgrade pip && \
    pip install pipenv && \
    pipenv install --deploy --system    

# ---- runtime ----
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local /usr/local
COPY . .          
ENTRYPOINT ["python", "main.py"]
