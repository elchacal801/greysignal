"""LLM-powered intelligence summarization via OpenAI API."""

import os
from typing import List, Optional

from ..models import Event
from ..utils.logging import get_logger

log = get_logger("processors.llm")

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None  # type: ignore[misc,assignment]


SYSTEM_PROMPT = """
You are a Senior Intelligence Analyst (DarkAnalytica) producing a "Unified Executive Summary" for a high-value client.
Your tone must be TLP:RED, formal, predictive, and highly actionable.

Input: Raw cyber intelligence feed.
Output: A structured Markdown report. Avoid generic advice. Focus on "So What?" and "Now What?".

Structure required:

## Key Judgments
[3-4 bullet points. Synthesize specific campaigns (e.g., Lazarus, Volt Typhoon) into strategic trends. Don't just list events; connect the dots.]
- **[Theme 1]**: [Analysis]
- **[Theme 2]**: [Analysis]

## Geopolitical & Financial Implications
[Analyze the intersection of these cyber threats with global stability and financial markets. Mention specific regions or sectors at risk.]

## Strategic Recommendations
### For Executive Leadership
- [Strategic Action 1]
- [Strategic Action 2]

### For Security & Risk Teams
- [Technical Action 1]
- [Technical Action 2]

## Top Critical Alerts (Selected High-Risk Events)
[Pick the top 3 most dangerous events from the feed and format them as follows:]
**1. [Headline]**
- **Risk/Opportunity**: [Why this matters]
- **Stakeholders**: [Who needs to act]
- **Context**: [Brief analysis]
""".strip()


class LLMSummarizer:
    """
    Generates AI-powered executive summaries from intelligence events.

    Security: Error messages are sanitized before inclusion in output.
    The OpenAI API key is never logged or included in output artifacts.
    """

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
        self.client: Optional["OpenAI"] = None  # type: ignore[name-defined]

        if self.api_key and OpenAI is not None:
            self.client = OpenAI(api_key=self.api_key)
            log.info(f"LLM client initialized (model={self.model})")
        else:
            if OpenAI is None:
                log.warning("OpenAI library not installed. AI summaries unavailable.")
            else:
                log.warning("OPENAI_API_KEY not set. AI summaries unavailable.")

    def generate_briefing(self, events: List[Event], period: str) -> str:
        """
        Generate an executive summary from intelligence events.

        Args:
            events: List of normalized Event objects.
            period: Time period label (e.g., "Daily (24h)", "Weekly (7d)").

        Returns:
            Markdown-formatted executive summary string.
            Returns a safe fallback message on any failure (no error details leaked).
        """
        if not self.client:
            return "*AI Executive Summary unavailable — API key not configured.*"

        # Build context (cap at 800 events for token safety)
        max_events = min(len(events), 800)
        context_lines: List[str] = []
        for ev in events[:max_events]:
            severity_tag = f"[{ev.severity.value.upper()}]" if ev.severity else ""
            summary_excerpt = ev.summary[:350].replace("\n", " ")
            context_lines.append(
                f"- {severity_tag} [{ev.source}] {ev.headline}: {summary_excerpt}"
            )

        context_str = "\n".join(context_lines)
        user_prompt = f"Period: {period}\nTotal Events: {len(events)}\n\nRaw Intelligence Feed:\n{context_str}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.5,
                max_tokens=4000,
            )
            content = response.choices[0].message.content
            if content:
                log.info(f"AI summary generated ({len(content)} chars)")
                return content
            return "*AI Executive Summary: Empty response received.*"

        except Exception as e:
            # SECURITY: Never include raw exception in output artifacts.
            # The exception may contain API keys, internal URLs, or request IDs.
            log.error(f"LLM generation failed: {e}")
            return "*AI Executive Summary unavailable — generation error. Check server logs.*"
