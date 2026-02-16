"""Data export and search capabilities for intelligence interoperability."""

import csv
import json
import os
import re
from datetime import datetime, timezone
from typing import List, Optional

from ..models import Event
from ..utils.logging import get_logger

log = get_logger("analytics.export")


class DataExporter:
    """
    Exports intelligence events in standard formats:
    - JSON (structured for API consumption / STIX-compatible structure)
    - CSV (for spreadsheet analysis)
    - JSONL (line-delimited JSON for stream processing)
    """

    def __init__(self, events: List[Event]):
        self.events = events

    def to_json(self, output_path: str, pretty: bool = True) -> str:
        """Export as structured JSON with metadata envelope."""
        envelope = {
            "type": "greysignal-intelligence-bundle",
            "version": "2.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "event_count": len(self.events),
            "events": [
                {
                    "headline": ev.headline,
                    "source": ev.source,
                    "url": ev.url,
                    "published_at": ev.published_at.isoformat(),
                    "summary": ev.summary,
                    "severity": ev.severity.value,
                    "tags": ev.tags,
                    "actors": ev.actors,
                    "countries": ev.countries,
                    "sectors": ev.sectors,
                    "content_hash": ev.content_hash,
                }
                for ev in self.events
            ],
        }

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        indent = 2 if pretty else None
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(envelope, f, ensure_ascii=False, indent=indent)

        log.info(f"JSON export saved to {output_path} ({len(self.events)} events)")
        return output_path

    def to_csv(self, output_path: str) -> str:
        """Export as CSV for spreadsheet analysis."""
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

        fieldnames = [
            "published_at", "severity", "source", "headline", "summary",
            "url", "actors", "countries", "sectors", "tags",
        ]

        with open(output_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
            writer.writeheader()
            for ev in self.events:
                writer.writerow({
                    "published_at": ev.published_at.isoformat(),
                    "severity": ev.severity.value,
                    "source": ev.source,
                    "headline": ev.headline,
                    "summary": ev.summary[:500],
                    "url": ev.url,
                    "actors": "; ".join(ev.actors),
                    "countries": "; ".join(ev.countries),
                    "sectors": "; ".join(ev.sectors),
                    "tags": "; ".join(ev.tags),
                })

        log.info(f"CSV export saved to {output_path} ({len(self.events)} events)")
        return output_path


class EventSearcher:
    """
    Advanced search and filtering across the event corpus.

    Supports:
    - Full-text regex search across headlines and summaries
    - Entity-based filtering (actors, countries, sectors)
    - Date range filtering
    - Tag-based filtering
    - Severity filtering
    """

    def __init__(self, events: List[Event]):
        self.events = events

    def search(
        self,
        query: Optional[str] = None,
        actor: Optional[str] = None,
        country: Optional[str] = None,
        sector: Optional[str] = None,
        tag: Optional[str] = None,
        severity: Optional[str] = None,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None,
        source: Optional[str] = None,
        use_regex: bool = False,
        limit: int = 100,
    ) -> List[Event]:
        """
        Search events with multiple filter criteria (AND logic).

        Args:
            query: Text search against headline + summary. Regex if use_regex=True.
            actor: Filter by actor name (case-insensitive substring).
            country: Filter by country (case-insensitive substring).
            sector: Filter by sector (case-insensitive substring).
            tag: Filter by tag (exact match, case-insensitive).
            severity: Filter by severity level.
            after: Only events published after this datetime.
            before: Only events published before this datetime.
            source: Filter by source name (case-insensitive substring).
            use_regex: Treat query as a regex pattern.
            limit: Maximum number of results.

        Returns:
            List of matching Event objects, sorted by date (newest first).
        """
        results: List[Event] = []

        # Pre-compile regex if needed
        regex_pattern = None
        if query and use_regex:
            try:
                regex_pattern = re.compile(query, re.IGNORECASE)
            except re.error as e:
                log.error(f"Invalid regex pattern: {e}")
                return []

        for ev in self.events:
            # Date range filters
            if after and ev.published_at < after:
                continue
            if before and ev.published_at > before:
                continue

            # Text search
            if query:
                combined = f"{ev.headline} {ev.summary}"
                if regex_pattern:
                    if not regex_pattern.search(combined):
                        continue
                else:
                    if query.lower() not in combined.lower():
                        continue

            # Entity filters
            if actor:
                actor_lower = actor.lower()
                if not any(actor_lower in a.lower() for a in ev.actors):
                    continue

            if country:
                country_lower = country.lower()
                if not any(country_lower in c.lower() for c in ev.countries):
                    continue

            if sector:
                sector_lower = sector.lower()
                if not any(sector_lower in s.lower() for s in ev.sectors):
                    continue

            if tag:
                tag_lower = tag.lower()
                if not any(tag_lower == t.lower() for t in ev.tags):
                    continue

            if severity:
                if ev.severity.value != severity.lower():
                    continue

            if source:
                if source.lower() not in ev.source.lower():
                    continue

            results.append(ev)

            if len(results) >= limit:
                break

        # Sort by date, newest first
        results.sort(key=lambda e: e.published_at, reverse=True)

        log.info(f"Search returned {len(results)} results (limit={limit})")
        return results
