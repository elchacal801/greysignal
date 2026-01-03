from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class Event(BaseModel):
    headline: str = Field(..., description="Title of the event/article")
    source: str = Field(..., description="Source name (e.g. CISA)")
    url: str = Field(..., description="Source URL")
    published_at: datetime = Field(..., description="Publication date")
    summary: str = Field(..., description="Short summary or lead paragraph")
    tags: List[str] = Field(default_factory=list, description="Source tags + inferred tags")
    
    # Enrichment fields (filled later)
    actors: List[str] = Field(default_factory=list)
    countries: List[str] = Field(default_factory=list)
    sectors: List[str] = Field(default_factory=list)
    
    raw_id: Optional[str] = None # RSS GUID if available
