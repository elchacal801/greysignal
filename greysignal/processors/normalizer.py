"""NLP normalizer with improved entity extraction, deduplication, and sector classification."""

import hashlib
import re
from typing import Dict, List, Set

import spacy
from bs4 import BeautifulSoup

from ..models import Event, SeverityLevel
from ..utils.logging import get_logger

log = get_logger("processors.normalizer")

# Entities that SpaCy commonly misclassifies (false positives)
ENTITY_STOPWORDS: Set[str] = {
    # Common false-positive ORGs/PERSONs
    "op-ed", "editorial", "breaking", "exclusive", "update", "analysis",
    "patch released", "read more", "click here", "subscribe", "rss",
    "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "css", "html", "http", "https", "api", "url", "dns",
    "cve", "cvss", "poc", "ioc", "ttps",
}

# Minimum entity length to avoid noise like "US" misclassified as person
MIN_ENTITY_LENGTH = 3

# Sector classification with word-boundary regex patterns
SECTOR_PATTERNS: Dict[str, re.Pattern] = {
    "Energy": re.compile(r"\b(?:energy|power\s+grid|electricity|oil\s+gas|pipeline|utility)\b", re.I),
    "Finance": re.compile(r"\b(?:financ|banking|bank(?:s)?\b|payment|swift|trading|stock\s+market)\b", re.I),
    "Healthcare": re.compile(r"\b(?:healthcare|hospital|medical|pharma|patient\s+data|hipaa)\b", re.I),
    "Government": re.compile(r"\b(?:government|federal|state\s+department|pentagon|dod|dhs)\b", re.I),
    "Manufacturing": re.compile(r"\b(?:manufactur|industrial\s+control|scada|plc|hmi)\b", re.I),
    "Telecom": re.compile(r"\b(?:telecom|5g|wireless|carrier|mobile\s+network)\b", re.I),
    "Critical Infrastructure": re.compile(r"\b(?:critical\s+infrastructure|water\s+treatment|dam|nuclear)\b", re.I),
    "Maritime": re.compile(r"\b(?:maritime|shipping|port|undersea\s+cable|vessel)\b", re.I),
    "Defense": re.compile(r"\b(?:defense|military|nato|armed\s+forces|intelligence\s+agency)\b", re.I),
}

# Severity keywords (checked against combined text)
SEVERITY_KEYWORDS = {
    SeverityLevel.CRITICAL: re.compile(
        r"\b(?:zero[\-\s]?day|active\s+exploit|nation[\-\s]?state|critical\s+vuln|"
        r"ransomware\s+attack|data\s+breach|mass\s+exploit|emergency\s+patch)\b", re.I
    ),
    SeverityLevel.HIGH: re.compile(
        r"\b(?:apt|advanced\s+persistent|malware\s+campaign|state[\-\s]?sponsored|"
        r"supply[\-\s]?chain\s+attack|critical\s+advisory|espionage)\b", re.I
    ),
    SeverityLevel.MEDIUM: re.compile(
        r"\b(?:vulnerabilit|patch|advisory|phishing|credential|botnet|"
        r"trojan|backdoor|exploit\s+kit)\b", re.I
    ),
}


class Normalizer:
    """
    Normalizes raw RSS events: cleans HTML, extracts entities, deduplicates,
    classifies sectors, and assigns severity levels.
    """

    def __init__(self, model: str = "en_core_web_sm"):
        log.info(f"Loading SpaCy model: {model}")
        try:
            self.nlp = spacy.load(model)
        except OSError:
            log.error(f"SpaCy model '{model}' not found. Run: python -m spacy download {model}")
            raise

    def clean_html(self, html_content: str) -> str:
        """Remove HTML tags, decode entities, and normalize whitespace."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator=" ")
        # Normalize whitespace
        return " ".join(text.split())

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extract named entities with filtering for quality.

        Filters out:
        - Entities shorter than MIN_ENTITY_LENGTH
        - Known false-positive stopwords
        - Purely numeric entities
        """
        doc = self.nlp(text[:5000])  # Cap input length for performance
        entities: Dict[str, List[str]] = {
            "actors": [],
            "countries": [],
        }

        seen: Set[str] = set()
        for ent in doc.ents:
            normalized = ent.text.strip()

            # Skip short entities
            if len(normalized) < MIN_ENTITY_LENGTH:
                continue

            # Skip known false positives
            if normalized.lower() in ENTITY_STOPWORDS:
                continue

            # Skip purely numeric
            if normalized.replace(",", "").replace(".", "").isdigit():
                continue

            # Deduplicate within this extraction
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)

            if ent.label_ == "GPE":
                entities["countries"].append(normalized)
            elif ent.label_ in ("ORG", "PERSON", "NORP"):
                entities["actors"].append(normalized)

        return entities

    def classify_sectors(self, text: str) -> List[str]:
        """Classify sectors using word-boundary-aware regex patterns."""
        sectors: List[str] = []
        for sector_name, pattern in SECTOR_PATTERNS.items():
            if pattern.search(text):
                sectors.append(sector_name)
        return sectors

    def classify_severity(self, text: str) -> SeverityLevel:
        """Assign severity based on keyword analysis (highest match wins)."""
        for level in (SeverityLevel.CRITICAL, SeverityLevel.HIGH, SeverityLevel.MEDIUM):
            if SEVERITY_KEYWORDS[level].search(text):
                return level
        return SeverityLevel.LOW

    def process_all(self, events: List[Event]) -> List[Event]:
        """
        Full normalization pipeline:
        1. Clean HTML from summaries
        2. Deduplicate by content hash (SHA-256 of headline + URL domain)
        3. Deduplicate by raw URL
        4. Extract named entities
        5. Classify sectors and severity
        """
        log.info(f"Processing {len(events)} raw events...")
        processed: List[Event] = []
        seen_hashes: Set[str] = set()
        seen_urls: Set[str] = set()

        for ev in events:
            # 1. Clean summary HTML
            clean_summary = self.clean_html(ev.summary)
            ev.summary = clean_summary[:500] if len(clean_summary) > 500 else clean_summary

            # 2. Content hash deduplication
            content_hash = ev.content_hash or ev.compute_content_hash()
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)
            ev.content_hash = content_hash

            # 3. URL deduplication (secondary check)
            if ev.url and ev.url in seen_urls:
                continue
            if ev.url:
                seen_urls.add(ev.url)

            # 4. Entity extraction
            combined_text = f"{ev.headline}. {ev.summary}"
            ents = self.extract_entities(combined_text)
            ev.actors = ents["actors"]
            ev.countries = ents["countries"]

            # 5. Sector classification
            ev.sectors = self.classify_sectors(combined_text)

            # 6. Severity classification
            ev.severity = self.classify_severity(combined_text)

            processed.append(ev)

        log.info(f"Normalized: {len(events)} raw → {len(processed)} unique events")
        return processed
