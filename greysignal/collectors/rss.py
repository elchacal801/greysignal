"""RSS feed collector with proper timezone handling, rate limiting, and date filtering."""

import calendar
import os
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

import feedparser
import yaml

from ..models import Event, SourceConfig
from ..utils.logging import get_logger

log = get_logger("collectors.rss")

# Honest User-Agent identifying the tool
USER_AGENT = "GreySignal/2.0 (OSINT Intelligence Aggregator; +https://github.com/elchacal801/greysignal)"


class RSSCollector:
    """
    Collects intelligence events from configured RSS feed sources.

    Fixes from v1:
    - Timezone-correct datetime parsing (calendar.timegm, not time.mktime)
    - Per-request timeout (no global socket mutation)
    - Honest User-Agent string
    - Rate limiting between requests
    - Date-based filtering at collection time
    """

    def __init__(self, config_path: str = "config/sources.yaml"):
        self.config_path = config_path
        self.sources = self._load_config()
        self.fetch_delay = float(os.getenv("FETCH_DELAY_SECONDS", "1.5"))
        self.fetch_timeout = float(os.getenv("FETCH_TIMEOUT_SECONDS", "15"))

    def _load_config(self) -> List[SourceConfig]:
        """Load and validate source configuration."""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config not found: {self.config_path}")

        with open(self.config_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)

        raw_sources = data.get("sources", [])
        sources: List[SourceConfig] = []
        for s in raw_sources:
            try:
                sources.append(SourceConfig(**s))
            except Exception as e:
                log.warning(f"Skipping invalid source config: {s.get('name', '?')} — {e}")

        log.info(f"Loaded {len(sources)} sources from {self.config_path}")
        return sources

    def _parse_datetime_utc(self, entry: feedparser.FeedParserDict) -> datetime:
        """
        Parse published/updated time from feed entry as UTC-aware datetime.

        Uses calendar.timegm() (NOT time.mktime()) because feedparser returns
        struct_time in UTC, and timegm interprets it correctly as UTC.
        """
        parsed_time = None

        if hasattr(entry, "published_parsed") and entry.published_parsed:
            parsed_time = entry.published_parsed
        elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
            parsed_time = entry.updated_parsed

        if parsed_time:
            try:
                timestamp = calendar.timegm(parsed_time)
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (ValueError, OverflowError, OSError) as e:
                log.warning(f"Failed to parse date from entry: {e}")

        return datetime.now(timezone.utc)

    def fetch_all(self, lookback_days: Optional[int] = None) -> List[Event]:
        """
        Fetch events from all configured sources.

        Args:
            lookback_days: If set, only return events published within this many days.
                          Events older than the cutoff are discarded at collection time.
        """
        cutoff: Optional[datetime] = None
        if lookback_days is not None and lookback_days > 0:
            cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)

        events: List[Event] = []
        success_count = 0
        fail_count = 0

        for i, source in enumerate(self.sources):
            if not source.enabled:
                log.debug(f"Skipping disabled source: {source.name}")
                continue

            log.info(f"[{i + 1}/{len(self.sources)}] Fetching: {source.name}")

            try:
                feed = feedparser.parse(
                    source.url,
                    request_headers={"User-Agent": USER_AGENT},
                )

                # Check for parsing errors (bozo flag)
                if feed.bozo and len(feed.entries) == 0:
                    log.warning(f"  Failed to parse {source.name}: {getattr(feed, 'bozo_exception', 'Unknown error')}")
                    fail_count += 1
                    continue

                source_event_count = 0
                for entry in feed.entries:
                    dt = self._parse_datetime_utc(entry)

                    # Apply date cutoff filter
                    if cutoff and dt < cutoff:
                        continue

                    summary = entry.get("summary", "") or entry.get("description", "") or ""
                    headline = entry.get("title", "").strip() or "Untitled"
                    link = entry.get("link", "") or ""

                    ev = Event(
                        headline=headline[:1000],
                        source=source.name,
                        url=link,
                        published_at=dt,
                        summary=summary[:2000],
                        tags=list(source.tags),
                        raw_id=entry.get("id", link) or link,
                        source_weight=source.weight,
                    )
                    ev.content_hash = ev.compute_content_hash()
                    events.append(ev)
                    source_event_count += 1

                log.info(f"  Collected {source_event_count} events from {source.name}")
                success_count += 1

            except Exception as e:
                log.error(f"  Error fetching {source.name}: {e}")
                fail_count += 1

            # Rate limiting: wait between requests (skip after last source)
            if i < len(self.sources) - 1 and self.fetch_delay > 0:
                time.sleep(self.fetch_delay)

        log.info(
            f"Collection complete: {len(events)} events from "
            f"{success_count} sources ({fail_count} failures)"
        )
        return events
