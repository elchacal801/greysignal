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

        # Prepare context (truncate if necessary to save tokens/cost)
        max_events = 50 
        context_lines = []
        for ev in events[:max_events]:
            context_lines.append(f"- [{ev.source}] {ev.headline}: {ev.summary[:200]}...")
            
        context_str = "\n".join(context_lines)
        
        system_prompt = """
You are a Senior Cyber Intelligence Analyst for a national security agency. 
Your goal is to produce a high-quality, actionable Intelligence Summary (INTSUM) based on the provided raw event data.

Structure your response exactly as follows (Markdown):

## 🚨 Executive Summary (BLUF)
[A concise 3-4 sentence paragraph summarizing the most critical threats. focus on STATE-ALIGNED methodology and confirmed high-impact breaches.]

## 🌍 Geopolitical Impact
[Analyze how these cyber events correlate with current global tensions. Mention specific countries (Russia, China, Iran, etc.) if they appear in the data.]

## 🛡️ Key Threat Narratives
### [Narrative 1 Title]
[Details...]
### [Narrative 2 Title]
[Details...]

## 🎯 Recommended Actions
- [Bullet point 1]
- [Bullet point 2]
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
