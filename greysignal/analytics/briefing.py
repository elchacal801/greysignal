"""Intelligence briefing generator — Markdown output with analytics."""

import html
import os
from collections import Counter
from datetime import datetime, timezone
from typing import List, Optional

from ..models import Event
from ..utils.logging import get_logger

log = get_logger("analytics.briefing")


class BriefingGenerator:
    """
    Generates Markdown intelligence briefings with:
    - Statistical overview (top sources, actors, countries, sectors)
    - Optional AI executive summary
    - Full event feed with severity indicators
    """

    def __init__(self, events: List[Event]):
        self.events = events

    def _severity_label(self, event: Event) -> str:
        """Get text label for severity."""
        return event.severity.value.upper()

    def _domain_label(self, event: Event) -> str:
        """Get text label for domain."""
        tags_str = " ".join(event.tags).lower()
        if any(t in tags_str for t in ("apt", "malware", "cyber", "vulns", "ics")):
            return "CYBER"
        if any(t in tags_str for t in ("crypto", "finance", "macro", "quant")):
            return "FINANCE"
        if any(t in tags_str for t in ("maritime", "cables", "logistics")):
            return "MARITIME"
        if any(t in tags_str for t in ("espionage", "intelligence", "osint")):
            return "INTEL"
        if any(t in tags_str for t in ("geopolitics", "defense", "strategy")):
            return "GEO"
        return "GEN"

    def generate(
        self,
        output_path: str,
        title_suffix: str = "",
        ai_summary: Optional[str] = None,
        timeline_link: str = "timeline.html",
    ) -> str:
        """
        Generate and save Markdown briefing.

        Returns the generated Markdown content.
        """
        now = datetime.now(timezone.utc)
        total_events = len(self.events)

        # Analytics
        sources = Counter(e.source for e in self.events)
        top_actors = Counter(a for e in self.events for a in e.actors).most_common(10)
        top_countries = Counter(c for e in self.events for c in e.countries).most_common(10)
        top_sectors = Counter(s for e in self.events for s in e.sectors).most_common(5)
        severity_dist = Counter(e.severity.value for e in self.events)

        # Build Markdown
        lines: List[str] = []

        # Front matter
        lines.append("---")
        lines.append("layout: default")
        lines.append("title: GreySignal Briefing")
        lines.append("---")
        lines.append("")
        lines.append(f"# GreySignal Intelligence Briefing: {title_suffix}")
        lines.append(f"**Generated**: {now.strftime('%Y-%m-%d %H:%M UTC')}")
        lines.append(f"**Classification**: TLP:RED (Internal Use Only)")
        lines.append(f"**Interactive Timeline**: [View Timeline (HTML)]({timeline_link})")
        lines.append("")

        # AI Summary
        if ai_summary:
            lines.append(ai_summary)
            lines.append("")
            lines.append("---")
            lines.append("")

        # Statistics
        lines.append("## Overview")
        lines.append("")
        lines.append(f"**{total_events}** events collected from **{len(sources)}** sources.")
        lines.append("")

        # Severity breakdown
        if severity_dist:
            sev_parts = []
            for level in ("critical", "high", "medium", "low", "info"):
                count = severity_dist.get(level, 0)
                if count > 0:
                    sev_parts.append(f"{level.upper()}: {count}")
            if sev_parts:
                lines.append(f"**Severity**: {' | '.join(sev_parts)}")
                lines.append("")

        lines.append("### Key Statistics")
        lines.append(f"- **Top Sources**: {', '.join(f'{s} ({c})' for s, c in sources.most_common(5))}")

        if top_countries:
            lines.append(f"- **Targeted Countries**: {', '.join(f'{c} ({n})' for c, n in top_countries[:5])}")
        if top_actors:
            lines.append(f"- **Identified Actors/Entities**: {', '.join(f'{a} ({n})' for a, n in top_actors[:5])}")
        if top_sectors:
            lines.append(f"- **Targeted Sectors**: {', '.join(f'{s} ({n})' for s, n in top_sectors)}")

        lines.append("")

        # Event Feed — grouped by severity
        lines.append("## Event Feed")
        lines.append("")

        for ev in self.events:
            sev_label = self._severity_label(ev)
            domain_label = self._domain_label(ev)

            # Escape headline for Markdown safety
            safe_headline = ev.headline.replace("[", "\\[").replace("]", "\\]")

            lines.append(f"### [{sev_label}] [{domain_label}] {safe_headline}")
            lines.append(
                f"**Source**: {ev.source} | "
                f"**Date**: {ev.published_at.strftime('%Y-%m-%d')} | "
                f"**Severity**: {ev.severity.value.upper()}"
            )
            lines.append("")

            if ev.summary:
                lines.append(ev.summary)
                lines.append("")

            if ev.url:
                lines.append(f"[Read Original Report]({ev.url})")
                lines.append("")

            entity_parts: List[str] = []
            if ev.actors:
                entity_parts.append(f"Actors: {', '.join(ev.actors[:5])}")
            if ev.countries:
                entity_parts.append(f"Countries: {', '.join(ev.countries[:5])}")
            if ev.sectors:
                entity_parts.append(f"Sectors: {', '.join(ev.sectors)}")
            if entity_parts:
                lines.append(f"*{' | '.join(entity_parts)}*")
                lines.append("")

            lines.append("---")
            lines.append("")

        # Footer
        lines.append(f"*Generated by GreySignal v2.0 at {now.strftime('%Y-%m-%d %H:%M UTC')}*")

        content = "\n".join(lines)

        # Write to file
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content + "\n")

        log.info(f"Briefing saved to {output_path} ({total_events} events)")
        return content
