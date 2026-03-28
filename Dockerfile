FROM python:3.14-slim

WORKDIR /app

# System dependencies
# gcc required for some python packages if wheels are missing
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && python -m spacy download en_core_web_sm

# Application code
COPY . .

# Create data directory
RUN mkdir -p data docs

# Non-root user for security
RUN useradd -m -r greysignal && chown -R greysignal:greysignal /app
USER greysignal

ENTRYPOINT ["python", "-m", "greysignal.main"]
CMD ["--help"]
