FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY backend/ ./backend/

RUN chmod +x /app/backend/entrypoint.sh

# Run the API (and its startup migration) as an unprivileged user, not root.
RUN useradd --no-create-home --uid 10001 app
USER app

EXPOSE 8000

ENTRYPOINT ["/app/backend/entrypoint.sh"]
