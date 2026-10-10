# Atomism backend — works on Render today, and anywhere else (a self-hosted
# server, AWS, GCP, a different Railway account) when Pravinkumar's team
# takes this over. Nothing in here is tied to any one hosting provider.

FROM python:3.11-slim

WORKDIR /app

# System packages needed to build psycopg2 and a couple of ML deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render (and most hosts) inject the port to bind to via $PORT.
# Default to 8000 so this also runs the same way on your own machine.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT}"]