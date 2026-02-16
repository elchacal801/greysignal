"""Interactive HTML timeline generator with XSS protection and enhanced UX."""

import html
import json
import os
from typing import List

from ..models import Event
from ..utils.logging import get_logger

log = get_logger("analytics.timeline")

# Pinned Vis.js version for reproducibility and security
VIS_JS_VERSION = "7.7.3"
VIS_JS_URL = f"https://unpkg.com/vis-timeline@{VIS_JS_VERSION}/standalone/umd/vis-timeline-graph2d.min.js"
VIS_CSS_URL = f"https://unpkg.com/vis-timeline@{VIS_JS_VERSION}/styles/vis-timeline-graph2d.min.css"


class TimelineGenerator:
    """
    Generates an interactive HTML timeline using Vis.js.

    Security: All user-supplied content is HTML-escaped before insertion.
    UX: Includes search/filter bar, clickable items, severity indicators.
    """

    def __init__(self, events: List[Event]):
        self.events = events

    def _classify_group(self, event: Event) -> str:
        """Classify event into visual group based on tags."""
        tags_set = set(t.lower() for t in event.tags)
        if tags_set & {"cyber", "malware", "vulns", "threat-intel", "ics", "ot", "apt"}:
            return "cyber"
        if tags_set & {"finance", "macro", "quant", "algo", "trading", "crypto"}:
            return "finance"
        if tags_set & {"maritime", "naval", "cables", "logistics", "nuclear", "infra"}:
            return "maritime"
        if tags_set & {"espionage", "intelligence", "osint", "geopolitics", "defense"}:
            return "geopolitics"
        return "default"

        return mapping.get(event.severity.value, "")

    def generate(self, output_path: str) -> None:
        """Generate and save the HTML timeline."""

        # Build Vis.js data items — ALL content is HTML-escaped
        items: List[dict] = []
        for i, ev in enumerate(self.events):
            safe_source = html.escape(ev.source, quote=True)
            safe_headline = html.escape(ev.headline, quote=True)
            safe_summary = html.escape(ev.summary[:300], quote=True)
            safe_url = html.escape(ev.url, quote=True)
            content = f"<b>{safe_source}</b><br>{safe_headline}"

            items.append({
                "id": i,
                "content": content,
                "start": ev.published_at.isoformat(),
                "className": self._classify_group(ev),
                "title": f"{safe_headline}\n\n{safe_summary}",
                "url": safe_url,
                "source": safe_source,
                "severity": ev.severity.value,
            })

        # JSON-encode the data (json.dumps handles escaping)
        json_data = json.dumps(items, ensure_ascii=True)

        start_date = items[-1]["start"] if items else ""
        end_date = items[0]["start"] if items else ""

        html_template = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>GreySignal Timeline</title>
    <script type="text/javascript" src="{VIS_JS_URL}"></script>
    <link href="{VIS_CSS_URL}" rel="stylesheet" type="text/css" />
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: 'SF Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace;
            background-color: #0a0e14;
            color: #b0b8c4;
            padding: 16px;
        }}
        .header {{
            text-align: center;
            padding: 16px 0;
            border-bottom: 1px solid #1a1f2e;
            margin-bottom: 16px;
        }}
        .header h1 {{
            color: #58a6ff;
            font-size: 1.4em;
            font-weight: 600;
            letter-spacing: 2px;
            text-transform: uppercase;
        }}
        .header .subtitle {{
            color: #6e7681;
            font-size: 0.85em;
            margin-top: 4px;
        }}

        /* Controls Bar */
        .controls {{
            display: flex;
            gap: 12px;
            align-items: center;
            padding: 10px 16px;
            background: #111822;
            border: 1px solid #1a1f2e;
            border-radius: 6px;
            margin-bottom: 12px;
            flex-wrap: wrap;
        }}
        .controls input[type="text"] {{
            flex: 1;
            min-width: 200px;
            padding: 8px 12px;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 4px;
            color: #c9d1d9;
            font-family: inherit;
            font-size: 0.9em;
        }}
        .controls input[type="text"]:focus {{
            outline: none;
            border-color: #58a6ff;
        }}
        .controls select {{
            padding: 8px 12px;
            background: #0d1117;
            border: 1px solid #30363d;
            border-radius: 4px;
            color: #c9d1d9;
            font-family: inherit;
        }}
        .controls .btn {{
            padding: 8px 16px;
            background: #1f6feb;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-family: inherit;
            font-size: 0.85em;
        }}
        .controls .btn:hover {{ background: #388bfd; }}
        .controls .btn.secondary {{
            background: #21262d;
            border: 1px solid #30363d;
        }}
        .controls .btn.secondary:hover {{ background: #30363d; }}
        .event-count {{
            color: #58a6ff;
            font-weight: 600;
            font-size: 0.9em;
            white-space: nowrap;
        }}

        /* Legend */
        .legend {{
            text-align: center;
            margin-bottom: 12px;
            font-size: 0.85em;
        }}
        .legend span {{ margin: 0 12px; }}

        /* Timeline Container */
        #timeline {{
            width: 100%;
            height: calc(100vh - 220px);
            min-height: 400px;
            border: 1px solid #1a1f2e;
            background-color: #0d1117;
            border-radius: 6px;
        }}

        /* Vis.js Item Styles */
        .vis-item {{
            border-width: 2px !important;
            border-radius: 4px;
            font-size: 12px;
            cursor: pointer;
        }}
        .vis-item.default {{
            border-color: #30363d !important;
            background-color: #161b22 !important;
            color: #8b949e !important;
        }}
        .vis-item.cyber {{
            border-color: #ff4466 !important;
            background-color: #2d0a14 !important;
            color: #ff99aa !important;
        }}
        .vis-item.finance {{
            border-color: #ffd700 !important;
            background-color: #2d2a00 !important;
            color: #ffe680 !important;
        }}
        .vis-item.maritime {{
            border-color: #00bfff !important;
            background-color: #002233 !important;
            color: #80e5ff !important;
        }}
        .vis-item.geopolitics {{
            border-color: #a855f7 !important;
            background-color: #1a0a2e !important;
            color: #d4a5ff !important;
        }}
        .vis-item.vis-selected {{
            border-color: #f0f6fc !important;
            box-shadow: 0 0 12px rgba(88, 166, 255, 0.4);
            z-index: 10;
        }}
        .vis-time-axis .vis-text {{ color: #6e7681; }}
        .vis-panel.vis-background {{ background-color: #0d1117; }}

        /* Responsive */
        @media (max-width: 768px) {{
            .controls {{ flex-direction: column; }}
            .controls input[type="text"] {{ width: 100%; }}
            #timeline {{ height: 60vh; }}
            .header h1 {{ font-size: 1.1em; }}
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>GreySignal — Intelligence Timeline</h1>
        <div class="subtitle">Click any event to open source article | Scroll to zoom | Drag to pan</div>
    </div>

    <div class="controls">
        <input type="text" id="searchBox" placeholder="Search events..." />
        <select id="domainFilter">
            <option value="all">All Domains</option>
            <option value="cyber">Cyber Threat</option>
            <option value="finance">Finance & Macro</option>
            <option value="maritime">Maritime & Infra</option>
            <option value="geopolitics">Geopolitics & Intel</option>
        </select>
        <select id="severityFilter">
            <option value="all">All Severity</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
        </select>
        <button class="btn secondary" onclick="resetFilters()">Reset</button>
        <span class="event-count" id="eventCount"></span>
    </div>

    <div class="legend">
        <span style="color:#ff4466;">&#9632; Cyber</span>
        <span style="color:#ffd700;">&#9632; Finance</span>
        <span style="color:#00bfff;">&#9632; Maritime</span>
        <span style="color:#a855f7;">&#9632; Geopolitics</span>
        <span style="color:#6e7681;">&#9632; General</span>
    </div>

    <div id="timeline"></div>

    <script type="text/javascript">
        var ALL_DATA = {json_data};
        var timeline, dataSet;

        function initTimeline(data) {{
            var container = document.getElementById('timeline');
            if (!data || data.length === 0) {{
                container.innerHTML = '<p style="text-align:center; padding:50px; color:#6e7681;">No events to display.</p>';
                updateCount(0);
                return;
            }}
            dataSet = new vis.DataSet(data);
            var options = {{
                height: '100%',
                start: '{start_date}',
                end: '{end_date}',
                zoomMin: 1000 * 60 * 60 * 12,
                zoomMax: 1000 * 60 * 60 * 24 * 365,
                orientation: 'top',
                tooltip: {{ followMouse: true, overflowMethod: 'cap' }},
                clickToUse: false,
            }};
            timeline = new vis.Timeline(container, dataSet, options);

            // Click to open source URL
            timeline.on('select', function(props) {{
                if (props.items && props.items.length > 0) {{
                    var item = dataSet.get(props.items[0]);
                    if (item && item.url) {{
                        window.open(item.url, '_blank', 'noopener,noreferrer');
                    }}
                }}
            }});
            updateCount(data.length);
        }}

        function updateCount(n) {{
            document.getElementById('eventCount').textContent = n + ' events';
        }}

        function applyFilters() {{
            var query = document.getElementById('searchBox').value.toLowerCase();
            var domain = document.getElementById('domainFilter').value;
            var severity = document.getElementById('severityFilter').value;

            var filtered = ALL_DATA.filter(function(item) {{
                if (query && item.content.toLowerCase().indexOf(query) === -1 &&
                    item.title.toLowerCase().indexOf(query) === -1) {{
                    return false;
                }}
                if (domain !== 'all' && item.className !== domain) return false;
                if (severity !== 'all' && item.severity !== severity) return false;
                return true;
            }});

            if (timeline) timeline.destroy();
            initTimeline(filtered);
        }}

        function resetFilters() {{
            document.getElementById('searchBox').value = '';
            document.getElementById('domainFilter').value = 'all';
            document.getElementById('severityFilter').value = 'all';
            if (timeline) timeline.destroy();
            initTimeline(ALL_DATA);
        }}

        // Event listeners
        document.getElementById('searchBox').addEventListener('input', applyFilters);
        document.getElementById('domainFilter').addEventListener('change', applyFilters);
        document.getElementById('severityFilter').addEventListener('change', applyFilters);

        // Initialize
        try {{
            initTimeline(ALL_DATA);
        }} catch (e) {{
            console.error("Timeline Error:", e);
            document.getElementById('timeline').innerHTML =
                '<p style="text-align:center; padding:50px; color:#ff4466;">Error loading timeline: ' + e.message + '</p>';
        }}
    </script>
</body>
</html>"""

        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)

        log.info(f"Timeline saved to {output_path} ({len(items)} events)")
