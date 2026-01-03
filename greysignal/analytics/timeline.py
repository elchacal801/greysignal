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
            items.append({
                "id": i,
                "content": content,
                "start": ev.published_at.isoformat(),
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
        .vis-item {{ border-color: #238636; background-color: #238636; color: white; border-radius: 4px; font-size: 14px; }}
        .vis-item.vis-selected {{ border-color: #f0f6fc; background-color: #1f6feb; z-index: 2; }}
        .vis-time-axis .vis-text {{ color: #8b949e; }}
        .vis-loading {{ display: none; }}
    </style>
</head>
<body>
    <h1>GreySignal: Cyber Intelligence Timeline</h1>
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
