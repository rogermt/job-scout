#!/usr/bin/env python3
"""Main entry point for Job Scout CLI.

This module provides the command-line interface for Job Scout following
ForgeSyte standards with proper CLI design and error handling.
"""

import sys
import logging
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from config_manager import get_settings
from src.discovery.platforms import get_scraper, list_scrapers
from logging_config import setup_logging
from tracking.database import init_database

# Import database models

# Console for rich output
console = Console()

# Get logger for this module
logger = logging.getLogger(__name__)


@click.group()
@click.version_option(version="0.1.0")
@click.option("--debug", is_flag=True, help="Enable debug mode")
@click.option(
    "--log-level",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="DEBUG",  # Set default to DEBUG
)
@click.pass_context
def cli(ctx: click.Context, debug: bool, log_level: str) -> None:
    """Job Scout - Autonomous job hunting tool for UK and worldwide remote positions.

    Job Scout helps you discover job opportunities across multiple platforms.
    """
    # Setup logging using logging_config.py
    setup_logging(log_level=log_level)
    logger = logging.getLogger(__name__)
    logger.debug(f"Debug mode: {debug}, Log level: {log_level}")
    # Initialize settings
    settings = get_settings()

    # Override with CLI options
    if debug:
        settings.debug = True
        log_level = "DEBUG"
    settings.log_level = log_level

    # Setup logging
    setup_logging(settings.output.log_file, log_level)

    # Store in context
    ctx.ensure_object(dict)
    ctx.obj = {"settings": settings, "db": None}

    # Initialize database
    try:
        db_manager = init_database(settings.database)
        ctx.obj["db"] = db_manager
    except Exception as e:
        console.print(f"[red]Failed to initialize database: {e}[/red]")
        sys.exit(1)


@cli.command()
@click.option("--query", "-q", required=True, help="Job search query")
@click.option(
    "--location", "-l", required=False, help="Location filter (e.g., 'UK Remote')"
)
@click.option(
    "--max-pages", "-p", type=int, default=3, help="Max pages to scrape per platform"
)
@click.pass_context
def search(
    ctx: click.Context, query: str, location: Optional[str], max_pages: int
) -> None:
    """Search for jobs across configured platforms.

    Examples:
        job-scout search -q "software engineer" -l "UK Remote"
        job-scout search -q "python developer"
    """
    settings = ctx.obj["settings"]

    console.print("[bold blue]Searching for jobs...[/bold blue]")
    console.print(f"Query: [cyan]{query}[/cyan]")
    if location:
        console.print(f"Location: [cyan]{location}[/cyan]")
    console.print()

    # Get enabled platforms
    enabled_platforms = settings.get_enabled_platforms()

    if not enabled_platforms:
        console.print("[yellow]No platforms are enabled.[/yellow]")
        return

    total_jobs = 0

    # Iterate through platforms
    for platform_name, platform_config in enabled_platforms.items():
        console.print(f"\n[bold]Platform:[/bold] {platform_name.title()}")

        # Get scraper
        scraper = get_scraper(platform_name, platform_config)
        if not scraper:
            console.print("  [red]✗[/red] Scraper not available")
            continue

        try:
            # Get and log the search URL
            search_url = scraper.get_search_url(query, location)
            logger.debug(f"Searching {platform_name}: {search_url}")

            jobs_scraped = 0
            # Scrape jobs
            for job_data in scraper.scrape_jobs(query, location, max_pages=max_pages):
                jobs_scraped += 1

                # Save to database
                scraper.save_job(job_data)

                # Display
                console.print(f"  [green]✓[/green] {job_data['title'][:50]}")
                console.print(f"      [dim]{job_data['company']}[/]")

            total_jobs += jobs_scraped
            console.print(f"  [bold]Found:[/bold] {jobs_scraped} jobs")

        except Exception as e:
            console.print(f"  [red]✗[/red] Error: {str(e)[:80]}")
            continue

    console.print(f"\n[bold green]Total jobs found: {total_jobs}[/bold green]")


@cli.group()
def platforms() -> None:
    """Manage job platforms."""
    pass


@platforms.command("list")
@click.pass_context
def list_platforms(ctx: click.Context) -> None:
    """List all available platforms."""
    settings = ctx.obj["settings"]

    enabled_platforms = settings.get_enabled_platforms()
    all_scrapers = list_scrapers()

    table = Table(title="Job Platforms")
    table.add_column("Platform", style="cyan")
    table.add_column("Status", style="green")

    for scraper_name in all_scrapers:
        is_enabled = scraper_name in enabled_platforms
        status = "✓ Enabled" if is_enabled else "✗ Disabled"
        table.add_row(scraper_name.title(), status)

    console.print(table)


if __name__ == "__main__":
    cli()

__all__ = ["cli"]
