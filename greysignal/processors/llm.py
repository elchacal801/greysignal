import os
from typing import List
from ..models import Event
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

class LLMSummarizer:
    def __init__(self, api_key: str = None, model: str = "gpt-4-turbo-preview"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model
        self.client = None
        
        if self.api_key and OpenAI:
            self.client = OpenAI(api_key=self.api_key)
        else:
            print("[Warning] OpenAI client not initialized. Missing key or library.")

    def generate_briefing(self, events: List[Event], period: str) -> str:
        """
        Generates a high-level executive summary using LLM.
        """
        if not self.client:
            return "<!-- LLM Summary Unavailable: Check API Key -->"

        # Prepare context (Increase limit for deeper analysis)
        max_events = 100
        context_lines = []
        for ev in events[:max_events]:
            context_lines.append(f"- [{ev.source}] {ev.headline}: {ev.summary[:250]}...")
            
        context_str = "\n".join(context_lines)
        
        system_prompt = """
You are a Senior Intelligence Analyst (DarkAnalytica) producing a "Unified Executive Summary" for a high-value client (Avondale Capital).
Your tone must be TLP:RED, formal, predictive, and highly actionable.

Input: Raw cyber intelligence feed.
Output: A structured Markdown report. Avoid generic advice. Focus on "So What?" and "Now What?".

Structure required:

## 🚨 Key Judgments
[3-4 bullet points. Synthesize specific campaigns (e.g., Lazarus, Volt Typhoon) into strategic trends. Don't just list events; connect the dots.]
- **[Theme 1]**: [Analysis]
- **[Theme 2]**: [Analysis]

## 🌍 Geopolitical & Financial Implications
[Analyze the intersection of these cyber threats with global stability and financial markets. Mention specific regions or sectors at risk.]

## 🛡️ Strategic Recommendations
### For Executive Leadership
- [Strategic Action 1]
- [Strategic Action 2]

### For Security & Risk Teams
- [Technical Action 1]
- [Technical Action 2]

## 🔍 Top Critical Alerts (Selected High-Risk Events)
[Pick the top 3 most dangerous events from the feed and format them as follows:]
**1. [Headline]**
- **Risk/Opportunity**: [Why this matters]
- **Stakeholders**: [Who needs to act]
- **Context**: [Brief analysis]
        """
        
        user_prompt = f"Period: {period}\n\nRaw Intelligence Feed:\n{context_str}"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"<!-- LLM Generation Failed: {e} -->"
