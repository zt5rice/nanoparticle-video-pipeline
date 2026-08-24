FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies first (better layer caching).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY scripts ./scripts

ENV PYTHONPATH=/app/src
EXPOSE 8000

CMD ["uvicorn", "nanotrack.api:app", "--host", "0.0.0.0", "--port", "8000"]

