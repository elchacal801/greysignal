from typing import List, Counter
from ..models import Event
import os
from datetime import datetime

class BriefingGenerator:
    def __init__(self, events: List[Event]):
        self.events = events
        
    def generate(self, output_path: str, title_suffix: str = ""):
        """Generate Markdown Briefing."""
        
        # Analytics
        total_events = len(self.events)
        sources = Counter([e.source for e in self.events])
        top_actors = Counter([a for e in self.events for a in e.actors]).most_common(10)
        top_countries = Counter([c for e in self.events for c in e.countries]).most_common(5)
        
        md = f"# GreySignal Intelligence Briefing: {title_suffix}\n"
        md += f"**Date**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
        
        md += "## Executive Summary\n"
        md += f"Analysis of **{total_events}** cyber intelligence events collected from **{len(sources)}** sources.\n\n"
        
        md += "### Key Statistics\n"
        md += f"- **Top Sources**: {', '.join([f'{s} ({c})' for s, c in sources.most_common(3)])}\n"
        if top_countries:
            md += f"- **Targeted Countries**: {', '.join([f'{c} ({n})' for c, n in top_countries])}\n"
        if top_actors:
            md += f"- **Identified Actors/Entities**: {', '.join([f'{a} ({n})' for a, n in top_actors])}\n"
            
        md += "\n## Event Feed\n"
        
        for ev in self.events:
            emoji = "🛡️"
            if "apt" in str(ev.tags).lower(): emoji = "🚨"
            if "crime" in str(ev.tags).lower(): emoji = "💰"
            
            md += f"### {emoji} {ev.headline}\n"
            md += f"**Source**: {ev.source} | **Date**: {ev.published_at.strftime('%Y-%m-%d')}\n\n"
            md += f"{ev.summary}\n\n"
            if ev.url:
                md += f"[Read Original Report]({ev.url})\n\n"
            if ev.actors or ev.countries:
                md += f"*Entities: {', '.join(ev.actors + ev.countries)}*\n\n"
            md += "---\n"
            
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(md)
        print(f"Briefing saved to {output_path}")
