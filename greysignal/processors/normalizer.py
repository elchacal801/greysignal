import spacy
from bs4 import BeautifulSoup
from typing import List
from ..models import Event
import hashlib

class Normalizer:
    def __init__(self, model: str = "en_core_web_sm"):
        print(f"Loading SpaCy model: {model}...")
        try:
            self.nlp = spacy.load(model)
        except OSError:
            print(f"Model {model} not found. Please run: python -m spacy download {model}")
            raise

    def clean_html(self, html_content: str) -> str:
        """Remove HTML tags and clean whitespace."""
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(separator=" ")
        return " ".join(text.split())

    def extract_entities(self, text: str) -> dict:
        """Extract ORG, GPE, PERSON entities."""
        doc = self.nlp(text)
        entities = {
            "actors": [],
            "countries": [],
            "sectors": [] # Inferred from ORG context or specific keywords?
        }
        
        # Simple mapping for now
        seen = set()
        for ent in doc.ents:
            if ent.text in seen:
                continue
            seen.add(ent.text)
            
            if ent.label_ == "GPE":
                entities["countries"].append(ent.text)
            elif ent.label_ == "ORG":
                # Maybe treat some ORGs as actors?
                entities["actors"].append(ent.text)
            elif ent.label_ == "PERSON":
                entities["actors"].append(ent.text)
                
        return entities

    def process_all(self, events: List[Event]) -> List[Event]:
        print(f"Processing {len(events)} events...")
        processed = []
        seen_hashes = set()

        for ev in events:
            # 1. Clean Summary
            clean_summary = self.clean_html(ev.summary)
            ev.summary = clean_summary[:500] + "..." if len(clean_summary) > 500 else clean_summary

            # 2. Deduplication (Simple Hash of headline)
            # Normalize headline for hash
            h_str = ev.headline.lower().strip()
            ev_hash = hashlib.md5(h_str.encode()).hexdigest()
            
            if ev_hash in seen_hashes:
                continue
            seen_hashes.add(ev_hash)

            # 3. Entity Extraction (Headline + Summary)
            combined_text = f"{ev.headline}. {ev.summary}"
            ents = self.extract_entities(combined_text)
            
            ev.actors.extend(ents["actors"])
            ev.countries.extend(ents["countries"])
            
            # 4. Basic Keyword Tagging (Sectors)
            text_lower = combined_text.lower()
            if "energy" in text_lower or "grid" in text_lower:
                ev.sectors.append("Energy")
            if "finance" in text_lower or "bank" in text_lower:
                ev.sectors.append("Finance")
            if "healthcare" in text_lower or "hospital" in text_lower:
                ev.sectors.append("Healthcare")
            if "government" in text_lower or "federal" in text_lower:
                ev.sectors.append("Government")
            if "manufacturing" in text_lower or "ics" in text_lower:
                ev.sectors.append("Manufacturing")

            processed.append(ev)
            
        print(f"Reduced to {len(processed)} unique events.")
        return processed
