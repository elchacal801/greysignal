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
):
    """
    Generate intelligence briefing (Markdown) and Timeline (HTML).
    """
    from .analytics.timeline import TimelineGenerator
    from .analytics.briefing import BriefingGenerator
    from .models import Event
    import ujson
    
    if not os.path.exists(input):
        console.print(f"[bold red]Input file {input} not found. Run 'collect' first.[/bold red]")
        raise typer.Exit(code=1)
        
    console.print(f"[bold green]Generating Intelligence Reports...[/bold green]")
    
    # Load Events
    events = []
    with open(input, "r", encoding="utf-8") as f:
        for line in f:
            events.append(Event.model_validate_json(line))
            
    # Sort by date desc
    events.sort(key=lambda x: x.published_at, reverse=True)
    
    # 1. Timeline
    timeline_gen = TimelineGenerator(events)
    timeline_gen.generate(os.path.join(out_dir, "timeline.html"))
    
    # 2. Briefing
    briefing_gen = BriefingGenerator(events)
    briefing_gen.generate(os.path.join(out_dir, "briefing.md"))
    
    console.print(f"[bold blue]Reports generated in {out_dir}/[/bold blue]")

if __name__ == "__main__":
    app()
