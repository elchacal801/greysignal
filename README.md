# GreySignal 📡

**State-of-the-Art Cyber Counterintelligence & Financial OSINT Pipeline.**

### [🔴 Enter Intelligence Portal (Live Reports)](https://elchacal801.github.io/greysignal/)

![Python](https://img.shields.io/badge/Python-3.11-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Status](https://img.shields.io/badge/Status-Active-success)
![Classification](https://img.shields.io/badge/TLE-RED-red)

GreySignal is an advanced agentic intelligence system designed to collect, normalize, and synthesize high-priority signals from:iggers.

## Features

- **Multi-Source Ingestion**: Aggregates high-fidelity RSS feeds from CISA, Google TAG, Microsoft, Mandiant, and more.
- **NLP Normalization**: Uses **SpaCy** and `BeautifulSoup` to clean HTML, extract entities (Actors, Countries, Orgs), and deduplicate events.
- **Automated Analytics**:
  - **Interactive Timeline**: Visualization of event frequency and clusters (`docs/timeline.html`).
  - **Intelligence Briefing**: Markdown summary partitioned by source and top entities (`docs/briefing.md`).
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
python -m greysignal.main report
```

### 3. View Results
Open `docs/timeline.html` in your browser or read `docs/briefing.md`.

## Configuration
Edit `config/sources.yaml` to add or remove RSS feeds.

## Project Structure
- `greysignal/collectors`: RSS ingestion logic.
- `greysignal/processors`: NLP normalization and entity extraction.
- `greysignal/analytics`: Timeline and briefing generators.
- `.github/workflows`: Automation scripts.

## License
MIT
