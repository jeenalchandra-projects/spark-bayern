FROM python:3.13-slim

# Install build tools needed by chromadb (has C extensions)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /app/data

COPY . .

# Railway injects PORT at runtime — we read it in main.py
EXPOSE 8000

CMD ["python", "main.py"]
