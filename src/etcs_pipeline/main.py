from pathlib import Path
import typer
from rich.console import Console
from rich.json import JSON

app = typer.Typer(name="etcs-pipeline", help="Agentic pipeline for generating message sequences from the active profile.")
console = Console()


@app.command()
def run(
    query: str = typer.Argument(..., help="Scenario description in natural language"),
    output: Path = typer.Option(None, "--output", "-o", help="Output JSON file"),
    profile: str = typer.Option(None, "--profile", "-p", help="Profile name (default: ACTIVE_PROFILE from .env)"),
):
    """Generate a message sequence from the scenario description using the active profile."""
    from etcs_pipeline.core.runner import PipelineRunner
    from etcs_pipeline.config.settings import get_config

    profile_name = profile or get_config().active_profile
    console.print(f"[bold]Profile:[/bold] {profile_name}")
    console.print(f"[bold]Query:[/bold] {query}")
    console.print("Starting pipeline...")

    runner = PipelineRunner(profile_name)
    result = runner.run(query)

    output_json = result.model_dump_json(indent=2)

    if output:
        output.write_text(output_json, encoding="utf-8")
        console.print(f"[green]Output written to:[/green] {output}")
    else:
        console.print(JSON(output_json))

    if result.status != "SUCCESS":
        console.print(f"[red]Status: {result.status}[/red]")
        raise typer.Exit(code=1)


@app.command()
def index(
    profile: str = typer.Option(None, "--profile", "-p"),
    force: bool = typer.Option(False, "--force", help="Re-index even if the table already exists"),
):
    """Index the spec markdown into the RAG vector store."""
    from etcs_pipeline.rag.retriever import RagRetriever
    from etcs_pipeline.config.loader import ProfileLoader
    from etcs_pipeline.config.settings import get_config

    profile_name = profile or get_config().active_profile
    loader = ProfileLoader(profile_name)
    console.print(f"Indexing spec for profile '{profile_name}'...")
    RagRetriever(loader)
    console.print("[green]Indexing complete.[/green]")


@app.command(name="cache")
def cache_cmd(
    action: str = typer.Argument(..., help="Action: 'add'"),
    chain_file: Path = typer.Argument(..., help="JSON file of the chain to add"),
    profile: str = typer.Option(None, "--profile", "-p"),
):
    """Manage the semantic cache."""
    import json
    from etcs_pipeline.cache.semantic_cache import SemanticCache
    from etcs_pipeline.config.loader import ProfileLoader
    from etcs_pipeline.config.settings import get_config

    if action != "add":
        console.print(f"[red]Unsupported action: {action}[/red]")
        raise typer.Exit(code=1)

    profile_name = profile or get_config().active_profile
    loader = ProfileLoader(profile_name)
    cache = SemanticCache(loader)
    chain = json.loads(chain_file.read_text(encoding="utf-8"))
    cache.add_chain(chain)
    console.print(f"[green]Chain '{chain.get('id', '?')}' added to cache.[/green]")


if __name__ == "__main__":
    app()
