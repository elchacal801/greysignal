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
        body {{ font-family: sans-serif; background-color: #1e1e1e; color: #fff; }}
        #timeline {{ width: 100%; height: 600px; border: 1px solid #444; }}
        .vis-item {{ border-color: #4cd137; background-color: #4cd137; color: black; }}
        .vis-item.vis-selected {{ border-color: white; background-color: white; }}
    </style>
</head>
<body>
    <h1 style="text-align: center; color: #4cd137;">GreySignal: Cyber Intelligence Timeline</h1>
    <div id="timeline"></div>

    <script type="text/javascript">
        var container = document.getElementById('timeline');
        var data = {json_data}; // Injected JSON
        var items = new vis.DataSet(data);
        var options = {{
            height: '600px',
            start: '{start_date}',
            end: '{end_date}'
        }};
        var timeline = new vis.Timeline(container, items, options);
    </script>
</body>
</html>
        """
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"Timeline saved to {output_path}")
