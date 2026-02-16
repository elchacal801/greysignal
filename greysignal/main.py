"""GreySignal CLI — Cyber Counterintelligence OSINT Pipeline."""

from __future__ import annotations

import os
import sys
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import typer
from dotenv import load_dotenv

# Load .env before anything else
load_dotenv()

from .utils.logging import get_console, get_logger

log = get_logger("main")
console = get_console()

app = typer.Typer(
    name="greysignal",
    help="GreySignal: Cyber Counterintelligence & Financial OSINT Pipeline.",
    no_args_is_help=True,
)


# ─────────────────────────────────────────────
# COLLECT
# ─────────────────────────────────────────────
@app.command()
def collect(
    days: int = typer.Option(3, help="Number of days to look back for feeds"),
    output: str = typer.Option("data/events.jsonl", help="Output file path"),
    append: bool = typer.Option(True, help="Append to existing file (dedup by URL). Use --no-append to overwrite."),
) -> None:
    """Collect latest cyber threat intelligence from configured RSS sources."""
    from .collectors.rss import RSSCollector
    from .processors.normalizer import Normalizer
    from .utils.audit import record_audit

    console.print(f"[bold green]Starting Collection (lookback={days}d, append={append})[/bold green]")

    # 1. Fetch with date filtering
    collector = RSSCollector()
    raw_events = collector.fetch_all(lookback_days=days)

    # 2. Normalize
    try:
        normalizer = Normalizer()
        events = normalizer.process_all(raw_events)
    except Exception as e:
        log.error(f"Normalization failed: {e}")
        console.print("[bold red]Normalization failed — using raw events as fallback[/bold red]")
        events = raw_events

    # 3. Deduplicate against existing data if appending
    os.makedirs(os.path.dirname(output) or ".", exist_ok=True)
    existing_urls: set[str] = set()

    if append and os.path.exists(output):
        from .models import Event as EventModel
        try:
            with open(output, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        existing_ev = EventModel.model_validate_json(line)
                        if existing_ev.url:
                            existing_urls.add(existing_ev.url)
                    except Exception:
                        pass
            log.info(f"Loaded {len(existing_urls)} existing URLs for dedup")
        except Exception as e:
            log.warning(f"Could not read existing data for dedup: {e}")

    # Filter out duplicates
    new_events = [ev for ev in events if ev.url not in existing_urls]

    # 4. Write
    mode = "a" if append else "w"
    with open(output, mode, encoding="utf-8") as f:
        for ev in new_events:
            f.write(ev.model_dump_json() + "\n")

    console.print(
        f"[bold blue]Saved {len(new_events)} new events "
        f"({len(events) - len(new_events)} duplicates skipped). "
        f"Total raw: {len(raw_events)}[/bold blue]"
    )

    # 5. Audit
    record_audit(
        action="collect",
        event_count=len(new_events),
        details=f"lookback={days}d, raw={len(raw_events)}, normalized={len(events)}, new={len(new_events)}",
    )


# ─────────────────────────────────────────────
# REPORT
# ─────────────────────────────────────────────
@app.command()
def report(
    input: str = typer.Option("data/events.jsonl", help="Input events file"),
    out_dir: str = typer.Option("docs", help="Output directory"),
    period: str = typer.Option("weekly", help="Filter: daily, weekly, all"),
    ai: bool = typer.Option(False, help="Enable AI Executive Summary (requires OPENAI_API_KEY)"),
) -> None:
    """Generate intelligence briefing (Markdown) and interactive timeline (HTML)."""
    from .analytics.briefing import BriefingGenerator
    from .analytics.timeline import TimelineGenerator
    from .models import Event
    from .utils.audit import record_audit

    if not os.path.exists(input):
        console.print(f"[bold red]Input file '{input}' not found. Run 'collect' first.[/bold red]")
        raise typer.Exit(code=1)

    # Determine cutoff
    now = datetime.now(timezone.utc)
    cutoff: Optional[datetime] = None
    period_name = "Full History"

    if period == "daily":
        cutoff = now - timedelta(days=1)
        period_name = "Daily (24h)"
    elif period == "weekly":
        cutoff = now - timedelta(days=7)
        period_name = "Weekly (7d)"

    console.print(f"[bold green]Generating Reports ({period_name})...[/bold green]")

    # Load events with date filtering
    events: list[Event] = []
    with open(input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = Event.model_validate_json(line)
                if cutoff and ev.published_at < cutoff:
                    continue
                events.append(ev)
            except Exception as e:
                log.warning(f"Skipping invalid event line: {e}")

    events.sort(key=lambda x: x.published_at, reverse=True)

    if not events:
        console.print("[bold yellow]No events found for the selected period.[/bold yellow]")
        raise typer.Exit()

    console.print(f"Loaded {len(events)} events for {period_name}")

    # 1. Timeline
    timeline_path = os.path.join(out_dir, "timeline.html")
    timeline_gen = TimelineGenerator(events)
    timeline_gen.generate(timeline_path)

    # 2. AI Summary (optional)
    ai_summary: Optional[str] = None
    if ai:
        from .processors.llm import LLMSummarizer
        console.print("[bold purple]Generating AI Executive Summary...[/bold purple]")
        llm = LLMSummarizer()
        ai_summary = llm.generate_briefing(events, period_name)

    # 3. Briefing
    briefing_path = os.path.join(out_dir, "briefing.md")
    briefing_gen = BriefingGenerator(events)
    briefing_gen.generate(briefing_path, title_suffix=period_name, ai_summary=ai_summary)

    # 4. Archive
    today = datetime.now(timezone.utc)
    archive_dir = os.path.join(out_dir, "archive", f"{today.year:04d}", f"{today.month:02d}")
    os.makedirs(archive_dir, exist_ok=True)

    archive_id = f"{today.strftime('%Y-%m-%d')}_{period}"
    archive_timeline_path = os.path.join(archive_dir, f"{archive_id}_timeline.html")
    archive_briefing_path = os.path.join(archive_dir, f"{archive_id}_briefing.md")

    timeline_gen.generate(archive_timeline_path)
    briefing_gen.generate(
        archive_briefing_path,
        title_suffix=period_name,
        ai_summary=ai_summary,
        timeline_link=f"{archive_id}_timeline.html",
    )

    # 5. Update archive index
    _generate_archive_index(out_dir)

    # 6. Audit
    record_audit(
        action="report",
        event_count=len(events),
        details=f"period={period_name}, ai={'yes' if ai else 'no'}, archived={archive_dir}",
    )

    console.print(f"[bold blue]Reports generated in {out_dir}/ and archived to {archive_dir}/[/bold blue]")


# ─────────────────────────────────────────────
# SEARCH
# ─────────────────────────────────────────────
@app.command()
def search(
    query: Optional[str] = typer.Argument(None, help="Search text or regex pattern"),
    input: str = typer.Option("data/events.jsonl", help="Input events file"),
    actor: Optional[str] = typer.Option(None, help="Filter by actor name"),
    country: Optional[str] = typer.Option(None, help="Filter by country"),
    sector: Optional[str] = typer.Option(None, help="Filter by sector"),
    tag: Optional[str] = typer.Option(None, help="Filter by tag"),
    severity: Optional[str] = typer.Option(None, help="Filter by severity: critical/high/medium/low/info"),
    source: Optional[str] = typer.Option(None, help="Filter by source name"),
    regex: bool = typer.Option(False, help="Treat query as regex"),
    limit: int = typer.Option(50, help="Maximum results"),
) -> None:
    """Search and filter the intelligence event corpus."""
    from .analytics.export import EventSearcher
    from .models import Event

    if not os.path.exists(input):
        console.print(f"[bold red]Input file '{input}' not found.[/bold red]")
        raise typer.Exit(code=1)

    # Load all events
    events: list[Event] = []
    with open(input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                events.append(Event.model_validate_json(line))
            except Exception:
                pass

    searcher = EventSearcher(events)
    results = searcher.search(
        query=query,
        actor=actor,
        country=country,
        sector=sector,
        tag=tag,
        severity=severity,
        source=source,
        use_regex=regex,
        limit=limit,
    )

    if not results:
        console.print("[bold yellow]No matching events found.[/bold yellow]")
        return

    console.print(f"[bold green]Found {len(results)} matching events:[/bold green]\n")
    for i, ev in enumerate(results, 1):
        sev_color = {
            "critical": "red", "high": "yellow", "medium": "cyan", "low": "green", "info": "blue"
        }.get(ev.severity.value, "white")

        console.print(
            f"  [{sev_color}]{ev.severity.value.upper():>8}[/{sev_color}] "
            f"[dim]{ev.published_at.strftime('%Y-%m-%d')}[/dim] "
            f"[bold]{ev.headline[:80]}[/bold]"
        )
        console.print(f"           [dim]{ev.source} — {ev.url}[/dim]")
        if ev.actors or ev.countries:
            console.print(f"           [dim italic]Entities: {', '.join(ev.actors[:3] + ev.countries[:3])}[/dim italic]")
        console.print()


# ─────────────────────────────────────────────
# EXPORT
# ─────────────────────────────────────────────
@app.command()
def export(
    format: str = typer.Argument("json", help="Export format: json, csv"),
    input: str = typer.Option("data/events.jsonl", help="Input events file"),
    output: Optional[str] = typer.Option(None, help="Output file path (auto-generated if not set)"),
    period: str = typer.Option("all", help="Filter: daily, weekly, all"),
) -> None:
    """Export intelligence events in standard formats (JSON, CSV)."""
    from .analytics.export import DataExporter
    from .models import Event
    from .utils.audit import record_audit

    if not os.path.exists(input):
        console.print(f"[bold red]Input file '{input}' not found.[/bold red]")
        raise typer.Exit(code=1)

    # Determine cutoff
    now = datetime.now(timezone.utc)
    cutoff: Optional[datetime] = None
    if period == "daily":
        cutoff = now - timedelta(days=1)
    elif period == "weekly":
        cutoff = now - timedelta(days=7)

    # Load events
    events: list[Event] = []
    with open(input, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = Event.model_validate_json(line)
                if cutoff and ev.published_at < cutoff:
                    continue
                events.append(ev)
            except Exception:
                pass

    events.sort(key=lambda x: x.published_at, reverse=True)

    if not events:
        console.print("[bold yellow]No events to export.[/bold yellow]")
        raise typer.Exit()

    # Auto-generate output path
    format_lower = format.lower()
    if not output:
        timestamp = now.strftime("%Y%m%d_%H%M")
        output = f"data/export_{timestamp}.{format_lower}"

    exporter = DataExporter(events)
    if format_lower == "json":
        exporter.to_json(output)
    elif format_lower == "csv":
        exporter.to_csv(output)
    else:
        console.print(f"[bold red]Unsupported format: {format}. Use 'json' or 'csv'.[/bold red]")
        raise typer.Exit(code=1)

    record_audit(
        action="export",
        event_count=len(events),
        details=f"format={format_lower}, period={period}, output={output}",
    )

    console.print(f"[bold blue]Exported {len(events)} events to {output}[/bold blue]")


# ─────────────────────────────────────────────
# AUDIT
# ─────────────────────────────────────────────
@app.command()
def audit(
    verify: bool = typer.Option(False, help="Verify audit chain integrity"),
    path: str = typer.Option("data/audit.jsonl", help="Audit log file path"),
) -> None:
    """View or verify the tamper-evident audit log."""
    from .utils.audit import verify_audit_chain

    if verify:
        console.print("[bold]Verifying audit chain integrity...[/bold]")
        is_valid = verify_audit_chain(path)
        if is_valid:
            console.print("[bold green]Audit chain: VALID — no tampering detected.[/bold green]")
        else:
            console.print("[bold red]Audit chain: INTEGRITY FAILURE — possible tampering![/bold red]")
        raise typer.Exit(code=0 if is_valid else 1)

    # Display recent audit entries
    if not os.path.exists(path):
        console.print("[bold yellow]No audit log found.[/bold yellow]")
        return

    from .models import AuditEntry
    entries: list[AuditEntry] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(AuditEntry.model_validate_json(line))
            except Exception:
                pass

    console.print(f"[bold]Audit Log ({len(entries)} entries):[/bold]\n")
    for entry in entries[-20:]:  # Last 20
        console.print(
            f"  [dim]{entry.timestamp.strftime('%Y-%m-%d %H:%M')}[/dim] "
            f"[bold]{entry.action:>10}[/bold] "
            f"events={entry.event_count:>4} "
            f"[dim]{entry.details}[/dim]"
        )


# ─────────────────────────────────────────────
# ARCHIVE INDEX GENERATOR (Internal)
# ─────────────────────────────────────────────
def _generate_archive_index(out_dir: str) -> None:
    """Scan archive directory and generate docs/archive.md index."""
    archive_root = os.path.join(out_dir, "archive")
    if not os.path.exists(archive_root):
        return

    index_lines = [
        "---", "layout: default", "title: Intelligence Archive", "---", "",
        "# Intelligence Archive", "",
        "Access historical intelligence briefings and timelines.", "",
    ]

    years = sorted(
        [d for d in os.listdir(archive_root) if d.isdigit()],
        reverse=True,
    )

    for year in years:
        year_path = os.path.join(archive_root, year)
        if not os.path.isdir(year_path):
            continue
        months = sorted(
            [d for d in os.listdir(year_path) if d.isdigit()],
            reverse=True,
        )

        index_lines.append(f"## {year}")

        for month in months:
            month_path = os.path.join(year_path, month)
            if not os.path.isdir(month_path):
                continue

            files = sorted(
                [f for f in os.listdir(month_path) if f.endswith("_briefing.md")],
                reverse=True,
            )
            if not files:
                continue

            month_name = date(int(year), int(month), 1).strftime("%B")
            index_lines.append(f"\n### {month_name}")

            for f_name in files:
                parts = f_name.replace("_briefing.md", "").split("_")
                date_str = parts[0]
                period_label = parts[1].title() if len(parts) > 1 else "Report"

                timeline_file = f_name.replace("briefing.md", "timeline.html")
                timeline_link = ""
                if os.path.exists(os.path.join(month_path, timeline_file)):
                    timeline_link = f" | [Timeline]({year}/{month}/{timeline_file})"

                index_lines.append(
                    f"- **{date_str} ({period_label})**: "
                    f"[Briefing]({year}/{month}/{f_name}){timeline_link}"
                )

        index_lines.append("\n---\n")

    index_path = os.path.join(out_dir, "archive.md")
    with open(index_path, "w", encoding="utf-8") as f:
        f.write("\n".join(index_lines))

    log.info(f"Archive index updated: {index_path}")


if __name__ == "__main__":
    app()
