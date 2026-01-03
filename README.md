# GreySignal: Cyber Counterintelligence Pipeline

GreySignal is an open-source OSINT pipeline designed to track state-aligned operations, influence campaigns, and emerging cyber threats correlated with geopolitical triggers.

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
