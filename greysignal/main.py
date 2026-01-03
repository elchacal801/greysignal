import typer
from rich.console import Console
import os

app = typer.Typer(help="GreySignal: Cyber Counterintelligence OSINT Pipeline.")
console = Console()

@app.command()
def collect(
    days: int = typer.Option(3, help="Number of days to look back for feeds"),
    output: str = typer.Option("data/events.jsonl", help="Output file path"),
    verbose: bool = False
):
    """
    Collect latest cyber threat intelligence from configured sources.
    """
    from .collectors.rss import RSSCollector
    from .processors.normalizer import Normalizer
    
    console.print(f"[bold green]Starting Data Collection (Lookback: {days} days)[/bold green]")
    
    # 1. Fetch
    collector = RSSCollector()
    raw_events = collector.fetch_all()
    
    # 2. Normalize & Process
    try:
        normalizer = Normalizer()
        events = normalizer.process_all(raw_events)
    except Exception as e:
        console.print(f"[bold red]Normalization failed: {e}[/bold red]")
        events = raw_events # Fallback
    
    # Filter by date (simple implementation for now)
    # in a real app, we'd filter inside fetch, or use a database
    
    console.print(f"Collected and processed {len(events)} events (from {len(raw_events)} raw). Saving to {output}...")
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output), exist_ok=True)
    
    saved_count = 0
    with open(output, "w", encoding="utf-8") as f:
        for ev in events:
            # Serialize to JSON lines
            # Using model_dump_json() from Pydantic v2
            f.write(ev.model_dump_json() + "\n")
            saved_count += 1
            
    console.print(f"[bold blue]Successfully saved {saved_count} events.[/bold blue]")

@app.command()
def report(
    input: str = typer.Option("data/events.jsonl", help="Input events file"),
    out_dir: str = typer.Option("docs", help="Output directory"),
    period: str = typer.Option("weekly", help="Filter: daily, weekly, all"),
    ai: bool = typer.Option(False, help="Enable AI Executive Summary (requires OPENAI_API_KEY)"),
):
    """
    Generate intelligence briefing (Markdown) and Timeline (HTML).
    """
    from .analytics.timeline import TimelineGenerator
    from .analytics.briefing import BriefingGenerator
    from .models import Event
    import ujson
    
    from datetime import datetime, timedelta, timezone
    
    if not os.path.exists(input):
        console.print(f"[bold red]Input file {input} not found. Run 'collect' first.[/bold red]")
        raise typer.Exit(code=1)

    # Determine cutoff
    now = datetime.now(timezone.utc)
    cutoff = None
    period_name = "Full History"
    
    if period == "daily":
        cutoff = now - timedelta(days=1)
        period_name = "Daily (24h)"
    elif period == "weekly":
        cutoff = now - timedelta(days=7)
        period_name = "Weekly (7d)"
        
    console.print(f"[bold green]Generating Intelligence Reports ({period_name})...[/bold green]")
    
    # Load Events
    events = []
    with open(input, "r", encoding="utf-8") as f:
        for line in f:
            try:
                ev = Event.model_validate_json(line)
                # Ensure timezone awareness for comparison
                if ev.published_at.tzinfo is None:
                     ev.published_at = ev.published_at.replace(tzinfo=timezone.utc)
                
                if cutoff and ev.published_at < cutoff:
                    continue
                    
                events.append(ev)
            except Exception as e:
                console.print(f"[yellow]Skipping invalid event: {e}[/yellow]")
            
    # Sort by date desc
    events.sort(key=lambda x: x.published_at, reverse=True)
    
    if not events:
        console.print("[bold yellow]No events found for the selected period.[/bold yellow]")
        raise typer.Exit()
    
    # 1. Timeline (Latest)
    timeline_gen = TimelineGenerator(events)
    timeline_gen.generate(os.path.join(out_dir, "timeline.html"))
    
    # AI Summary
    ai_summary = None
    if ai:
        from .processors.llm import LLMSummarizer
        console.print("[bold purple]Querying AI Intelligence Engine...[/bold purple]")
        llm = LLMSummarizer()
        ai_summary = llm.generate_briefing(events, period_name)
    
    # 2. Briefing (Latest)
    briefing_gen = BriefingGenerator(events)
    briefing_gen.generate(os.path.join(out_dir, "briefing.md"), title_suffix=period_name, ai_summary=ai_summary)
    
    # 3. Archiving
    # Format: docs/archive/YYYY/MM/YYYY-MM-DD_ID_briefing.md
    today = datetime.now(timezone.utc)
    archive_dir = os.path.join(out_dir, "archive", f"{today.year:04d}", f"{today.month:02d}")
    os.makedirs(archive_dir, exist_ok=True)
    
    archive_id = today.strftime("%Y-%m-%d")
    archive_briefing_path = os.path.join(archive_dir, f"{archive_id}_briefing.md")
    archive_timeline_path = os.path.join(archive_dir, f"{archive_id}_timeline.html")
    
    # Save Archive Timeline
    timeline_gen.generate(archive_timeline_path)
    
    # Save Archive Briefing (with adjusted link to timeline)
    # We re-generate or copy? Re-generating allows changing the link.
    # The BriefingGenerator currently hardcodes the link or takes it?
    # It hardcodes [View Timeline (HTML)](timeline.html).
    # We can rely on relative paths properly.
    # docs/archive/2026/01/timeline.html is sibling to briefing.md.
    # So `(timeline.html)` link works fine if we rename the file to `timeline.html`?
    # No, we named it `{archive_id}_timeline.html`.
    # Let's simple copy the content and replace the link, or update generator.
    # For now, let's keep it simple: Archive filenames match.
    
    # Actually, let's update BriefingGenerator to accept timeline_link argument or just Post-process the file.
    # Post-process is easier here.
    with open(os.path.join(out_dir, "briefing.md"), "r", encoding="utf-8") as f:
        content = f.read()
        
    # Replace link for archive
    archive_content = content.replace("(timeline.html)", f"({os.path.basename(archive_timeline_path)})")
    
    with open(archive_briefing_path, "w", encoding="utf-8") as f:
        f.write(archive_content)
        
    # 4. Update Archive Index (docs/archive.md)
    generate_archive_index(out_dir)
    
    console.print(f"[bold blue]Reports generated in {out_dir}/ and archived to {archive_dir}/[/bold blue]")

def generate_archive_index(out_dir: str):
    """
    Scans docs/archive/YYYY/MM/*.md and generates docs/archive.md
    """
    archive_root = os.path.join(out_dir, "archive")
    if not os.path.exists(archive_root):
        return
        
    index_lines = ["# 🗄️ Intelligence Archive\n", "Access historical intelligence briefings and timelines.\n"]
    
    # Walk Years
    years = sorted([d for d in os.listdir(archive_root) if d.isdigit()], reverse=True)
    
    for year in years:
        year_path = os.path.join(archive_root, year)
        months = sorted([d for d in os.listdir(year_path) if d.isdigit()], reverse=True)
        
        index_lines.append(f"## {year}")
        
        for month in months:
            month_path = os.path.join(year_path, month)
            # Find briefing files
            files = [f for f in os.listdir(month_path) if f.endswith("_briefing.md")]
            files.sort(reverse=True) # Sort by date desc
            
            if not files:
                continue
                
            from datetime import date
            month_name = date(int(year), int(month), 1).strftime("%B")
            index_lines.append(f"\n### {month_name}")
            
            for f_name in files:
                # 2026-01-03_briefing.md
                date_str = f_name.split("_briefing.md")[0]
                timeline_name = f"{date_str}_timeline.html"
                
                # Relative link from docs/archive.md (root/docs/archive.md) -> archive/YYYY/MM/...
                rel_path = f"archive/{year}/{month}"
                
                # Check if timeline exists
                timeline_link = ""
                if os.path.exists(os.path.join(month_path, timeline_name)):
                    timeline_link = f" | [Interactive Timeline]({rel_path}/{timeline_name})"
                    
                index_lines.append(f"- **{date_str}**: [Briefing]({rel_path}/{f_name}){timeline_link}")
        
        index_lines.append("\n---\n")
        
    with open(os.path.join(out_dir, "archive.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))
    
    console.print("[bold green]Updated Intelligence Archive Index (docs/archive.md)[/bold green]")

if __name__ == "__main__":
    app()
