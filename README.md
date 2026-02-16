# GreySignal

**State-of-the-Art Cyber Counterintelligence & Financial OSINT Pipeline.**

### [Enter Intelligence Portal (Live Reports)](https://elchacal801.github.io/greysignal/)

![Python](https://img.shields.io/badge/Python-3.11-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)
![Classification](https://img.shields.io/badge/TLE-RED-red)

GreySignal is an advanced agentic intelligence system designed to collect, normalize, and synthesize high-priority signals from diverse open sources.

## Features

- **Multi-Source Ingestion**: Aggregates high-fidelity RSS feeds from CISA, Google TAG, Microsoft, Mandiant, and more.
- **NLP Normalization**: Uses **SpaCy** and `BeautifulSoup` to clean HTML, extract entities (Actors, Countries, Orgs), and deduplicate events using SHA-256 content hashing.
- **Automated Analytics**:
  - **Interactive Timeline**: Visualization of event frequency and clusters (`docs/timeline.html`).
  - **Intelligence Briefing**: AI-generated markdown summary partitioned by source and top entities (`docs/briefing.md`).
- **Data Export**: Export intelligence to JSON, JSONL, or CSV formats for external analysis.
- **Audit Logging**: Tamper-evident audit trails for all collection and processing actions.
- **CI/CD Automation**: GitHub Actions workflow (`daily_intel.yml`) runs daily collection and updates the repo.

## Installation

```bash
pip install -r requirements.txt
python -m spacy download en_core_web_sm
```

## Usage

### 1. Collect Data

Fetch, normalize, and save cyber threat events.

```bash
python -m greysignal.main collect --days 3
```

### 2. Generate Reports

Create the timeline and briefing.

```bash
python -m greysignal.main report --period daily --ai
```

### 3. Search Intelligence

Search the local database for specific keywords.

```bash
python -m greysignal.main search "ransomware"
```

### 4. Export Data

Export collected events to JSON, CSV, or JSONL.

```bash
python -m greysignal.main export json --output data/export.json
```

### 5. Verify Audit Log

Verify the integrity of the audit chain.

```bash
python -m greysignal.main audit --verify
```

## Configuration

1. Copy `.env.example` to `.env`.
2. Set your `OPENAI_API_KEY` for AI summarization.
3. Adjust `FETCH_DELAY_SECONDS` and timeouts as needed.

## Project Structure

- `greysignal/main.py`: CLI entry point.
- `greysignal/models.py`: Pydantic data models.
- `greysignal/collectors`: RSS ingestion logic.
- `greysignal/processors`: NLP normalization, entity extraction, and LLM processing.
- `greysignal/analytics`: Timeline, briefing, and export generators.
- `greysignal/utils`: Logging and audit utilities.
- `.github/workflows`: Automation scripts.

## License

MIT
