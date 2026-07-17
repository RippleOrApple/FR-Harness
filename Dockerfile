FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FR_DATABASE_PATH=/data/fr_harness.sqlite3

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN python -m pip install --no-cache-dir .

RUN mkdir -p /data

EXPOSE 8000

CMD ["python", "-m", "fr_harness.cli", "serve"]
