import yaml
import feedparser
import os
import time
from datetime import datetime
from typing import List, Dict
from ..models import Event

class RSSCollector:
    def __init__(self, config_path: str = "config/sources.yaml"):
        self.config_path = config_path
        self.sources = self._load_config()
        
    def _load_config(self) -> List[Dict]:
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"Config not found: {self.config_path}")
            
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
            return data.get("sources", [])
            
    def fetch_all(self) -> List[Event]:
        events = []
        for source in self.sources:
            print(f"Fetching {source['name']}...")
            try:
                # Use a custom User-Agent to avoid bot blocking & Enforce Timeout
                import socket
                socket.setdefaulttimeout(15) # Global timeout safety
                
                feed = feedparser.parse(
                    source['url'],
                    request_headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
                )
                
                # Check for parsing errors
                if feed.bozo and len(feed.entries) == 0:
                    print(f"  WARNING: Failed to parse {source['url']}")
                    continue
                    
                for entry in feed.entries:
                    # Parse Date
                    dt = datetime.now()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        dt = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        dt = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                        
                    # Parse Summary (clean tags?)
                    summary = entry.get('summary', '') or entry.get('description', '')
                    
                    # Create Event
                    ev = Event(
                        headline=entry.get('title', 'No Title'),
                        source=source['name'],
                        url=entry.get('link', ''),
                        published_at=dt,
                        summary=summary,
                        tags=source.get('tags', []),
                        raw_id=entry.get('id', entry.get('link'))
                    )
                    events.append(ev)
                    
            except Exception as e:
                print(f"  ERROR: {e}")
                
        return events
