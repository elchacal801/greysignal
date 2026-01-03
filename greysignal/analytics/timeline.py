import os
from typing import List
from ..models import Event
import json

class TimelineGenerator:
    def __init__(self, events: List[Event]):
        self.events = events
        
    def generate(self, output_path: str):
        """Generate HTML timeline using Vis.js"""
        
        # Prepare data for Vis.js Timeline
        items = []
        for i, ev in enumerate(self.events):
            content = f"<b>{ev.source}</b><br>{ev.headline}"
            
            # Determine category style
            group_class = "default"
            tags_set = set(ev.tags)
            
            if any(t in tags_set for t in ["cyber", "malware", "vulns", "threat-intel", "ics", "ot"]):
                group_class = "cyber"
            elif any(t in tags_set for t in ["finance", "macro", "quant", "algo", "trading", "crypto"]):
                group_class = "finance"
            elif any(t in tags_set for t in ["maritime", "naval", "cables", "logistics", "nuclear", "infra"]):
                group_class = "maritime"
                
            items.append({
                "id": i,
                "content": content,
                "start": ev.published_at.isoformat(),
                "className": group_class,
                "title": ev.summary[:200] + "..." # Tooltip
            })
            
        json_data = json.dumps(items)
        
        start_date = items[-1]["start"] if items else ""
        end_date = items[0]["start"] if items else ""

        html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <title>GreySignal Timeline</title>
    <script type="text/javascript" src="https://unpkg.com/vis-timeline@latest/standalone/umd/vis-timeline-graph2d.min.js"></script>
    <link href="https://unpkg.com/vis-timeline@latest/styles/vis-timeline-graph2d.min.css" rel="stylesheet" type="text/css" />
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #0d1117; color: #c9d1d9; margin: 0; padding: 20px; }}
        h1 {{ text-align: center; color: #58a6ff; margin-bottom: 20px; }}
        #timeline {{ width: 100%; height: 800px; border: 1px solid #30363d; background-color: #161b22; border-radius: 6px; }}
        
        /* Default Item Style */
        .vis-item {{ border-color: #30363d !important; background-color: #161b22 !important; color: #8b949e !important; border-radius: 4px; font-size: 14px; border-width: 2px; }}
        .vis-item.vis-selected {{ border-color: #f0f6fc !important; background-color: #1f6feb !important; z-index: 2; color: white !important; }}
        
        /* Domain Specific Colors (Cyberpunk Palette) */
        /* Cyber: Neon Red */
        .vis-item.cyber {{ border-color: #ff0055 !important; background-color: #4a0018 !important; color: #ff99bb !important; }}
        /* Finance: Gold */
        .vis-item.finance {{ border-color: #ffd700 !important; background-color: #3b3200 !important; color: #ffe680 !important; }}
        /* Maritime: Ocean Blue */
        .vis-item.maritime {{ border-color: #00bfff !important; background-color: #002b3b !important; color: #80e5ff !important; }}
        
        .vis-time-axis .vis-text {{ color: #8b949e; }}
        .vis-loading {{ display: none; }}
    </style>
</head>
<body>
    <h1>GreySignal: Cyber Intelligence Timeline</h1>
    <div style="text-align: center; margin-bottom: 20px; font-family: monospace; font-size: 16px;">
        <span style="color:#ff0055; margin-right: 20px;">■ Cyber Threat</span>
        <span style="color:#ffd700; margin-right: 20px;">■ Finance & Macro</span>
        <span style="color:#00bfff; margin-right: 20px;">■ Maritime & Infra</span>
        <span style="color:#8b949e;">■ General</span>
    </div>
    <div id="timeline"></div>
    <div id="error-msg" style="color: red; text-align: center; display: none;"></div>

    <script type="text/javascript">
        try {{
            var container = document.getElementById('timeline');
            var rawData = {json_data}; 
            
            if (!rawData || rawData.length === 0) {{
                document.getElementById('timeline').innerHTML = '<p style="text-align:center; padding-top: 50px;">No events to display.</p>';
            }} else {{
                var items = new vis.DataSet(rawData);
                
                // Calculate range with buffers
                var start = '{start_date}';
                var end = '{end_date}';
                
                var options = {{
                    height: '800px',
                    start: start,
                    end: end,
                    zoomMin: 1000 * 60 * 60 * 24, // 1 day min zoom
                    zoomMax: 1000 * 60 * 60 * 24 * 31 * 12, // 1 year max
                    orientation: 'top'
                }};
                
                var timeline = new vis.Timeline(container, items, options);
            }}
        }} catch (e) {{
            console.error("Timeline Error:", e);
            document.getElementById('error-msg').innerText = "Error loading timeline: " + e.message;
            document.getElementById('error-msg').style.display = 'block';
        }}
    </script>
</body>
</html>
        """
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"Timeline saved to {output_path}")
