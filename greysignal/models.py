"""Data models for GreySignal intelligence events and audit records."""

from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class SeverityLevel(str, Enum):
    """Intelligence event severity classification."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class UserRole(str, Enum):
    """RBAC role definitions."""
    ADMIN = "admin"
    ANALYST = "analyst"
    VIEWER = "viewer"


class Event(BaseModel):
    """
    Core intelligence event — normalized from RSS/API sources.
    All timestamps are timezone-aware UTC.
    """
    headline: str = Field(..., min_length=1, max_length=1000, description="Title of the event/article")
    source: str = Field(..., min_length=1, description="Source name (e.g. CISA)")
    url: str = Field(..., description="Source URL")
    published_at: datetime = Field(..., description="Publication date (UTC)")
    summary: str = Field(default="", max_length=2000, description="Cleaned summary text")
    tags: List[str] = Field(default_factory=list, description="Source tags + inferred tags")

    # Enrichment fields
    actors: List[str] = Field(default_factory=list, description="Extracted threat actors / persons")
    countries: List[str] = Field(default_factory=list, description="Extracted geopolitical entities")
    sectors: List[str] = Field(default_factory=list, description="Inferred target sectors")
    severity: SeverityLevel = Field(default=SeverityLevel.INFO, description="Event severity")

    # Identity
    raw_id: Optional[str] = Field(default=None, description="RSS GUID if available")
    content_hash: Optional[str] = Field(default=None, description="SHA-256 deduplication hash")
    source_weight: float = Field(default=1.0, ge=0.0, le=2.0, description="Source credibility weight")

    @field_validator("published_at", mode="after")
    @classmethod
    def ensure_timezone_aware(cls, v: datetime) -> datetime:
        """Ensure all datetimes are timezone-aware UTC."""
        if isinstance(v, datetime) and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v

    def compute_content_hash(self) -> str:
        """Generate SHA-256 hash for deduplication. Uses headline + URL domain."""
        from urllib.parse import urlparse
        domain = urlparse(self.url).netloc if self.url else ""
        raw = f"{self.headline.lower().strip()}|{domain}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class AuditEntry(BaseModel):
    """
    Tamper-evident audit log entry.
    Hash-chained: each entry includes the hash of the previous entry.
    """
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    action: str = Field(..., description="Operation performed (collect, normalize, report, export)")
    actor: str = Field(default="system", description="User or system that performed the action")
    input_hash: Optional[str] = Field(default=None, description="SHA-256 of input data")
    output_hash: Optional[str] = Field(default=None, description="SHA-256 of output data")
    event_count: int = Field(default=0, description="Number of events processed")
    details: str = Field(default="", description="Human-readable description")
    previous_hash: str = Field(default="GENESIS", description="Hash of previous audit entry")
    entry_hash: Optional[str] = Field(default=None, description="SHA-256 of this entry")

    def compute_entry_hash(self) -> str:
        """Compute tamper-evident hash of this entry (excludes entry_hash field)."""
        raw = (
            f"{self.timestamp.isoformat()}|{self.action}|{self.actor}|"
            f"{self.input_hash or ''}|{self.output_hash or ''}|"
            f"{self.event_count}|{self.details}|{self.previous_hash}"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def finalize(self) -> "AuditEntry":
        """Compute and set the entry hash. Call once before persisting."""
        self.entry_hash = self.compute_entry_hash()
        return self


class SourceConfig(BaseModel):
    """Configuration for a single RSS/API source."""
    name: str
    url: str
    tags: List[str] = Field(default_factory=list)
    weight: float = Field(default=1.0, ge=0.0, le=2.0)
    enabled: bool = Field(default=True)
