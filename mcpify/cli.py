#!/usr/bin/env python3
"""
MCPify CLI - Transform Git repositories into MCP tools
"""

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import List, Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from .core.analysis.detector import DependencyDetector
from .core.analysis.python_parser import PythonParser
from .core.generation.mcp_generator import MCPGenerator
from .core.generation.runner import MCPServerRunner
from .core.semantic.api_matcher import APIMatcher

app = typer.Typer(
    name="mcpify",
    help="Transform Git repositories into intelligent MCP tools automatically",
    add_completion=False,
)
console = Console()


@app.command()
def analyze(
    repo_url: str = typer.Argument(..., help="GitHub repository URL or local path"),
    api_request: str = typer.Option(
        ..., "--api", "-a", help="API requirements description"
    ),
    output: Optional[Path] = typer.Option(
        None, "--output", "-o", help="Output directory for generated server"
    ),
    llm_provider: str = typer.Option(
        "openai", "--llm", help="LLM provider (openai, anthropic)"
    ),
    llm_model: Optional[str] = typer.Option(
        None, "--model", help="Specific LLM model to use"
    ),
    embedding_provider: str = typer.Option(
        "sentence_transformers",
        "--embedding",
        help="Embedding provider (sentence_transformers, openai)",
    ),
    embedding_model: Optional[str] = typer.Option(
        None, "--embedding-model", help="Specific embedding model"
    ),
    transport: str = typer.Option(
        "stdio", "--transport", "-t", help="MCP transport mode (stdio, http)"
    ),
    start_server: bool = typer.Option(
        None,
        "--start/--no-start",
        help="Start the MCP server after generation (auto-determined by transport if not specified)",
    ),
    test_server: bool = typer.Option(
        True, "--test/--no-test", help="Test server communication"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
):
    """Analyze a repository and generate MCP tools."""

    # Validate transport mode
    if transport not in ["stdio", "http"]:
        console.print(
            f"[red]Error: Invalid transport '{transport}'. Must be 'stdio' or 'http'[/red]"
        )
        raise typer.Exit(1)

    # Auto-determine start_server behavior based on transport
    if start_server is None:
        if transport == "stdio":
            start_server = False  # stdio servers should be started by MCP clients
            if verbose:
                console.print(
                    "[yellow]Note: stdio transport - server will not be auto-started[/yellow]"
                )
        elif transport == "http":
            start_server = True  # http servers can run independently
            if verbose:
                console.print(
                    "[blue]Note: http transport - server will be auto-started[/blue]"
                )

    console.print(
        Panel.fit(
            f"[bold blue]MCPify[/bold blue] - Transforming [green]{repo_url}[/green] into MCP tools ([cyan]{transport}[/cyan] transport)",
            border_style="blue",
        )
    )

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            # Step 1: Clone or prepare repository
            task1 = progress.add_task("Preparing repository...", total=None)
            repo_path = _prepare_repository(repo_url, verbose)
            progress.update(task1, completed=True, description="✓ Repository prepared")

            # Step 2: Analyze repository
            task2 = progress.add_task("Analyzing Python code...", total=None)
            repository, functions = _analyze_repository(repo_path, repo_url, verbose)
            progress.update(
                task2, completed=True, description=f"✓ Found {len(functions)} functions"
            )

            if not functions:
                console.print("[red]No Python functions found in repository![/red]")
                raise typer.Exit(1) from None

            # Step 3: Generate MCP tools
            task3 = progress.add_task("Generating MCP tools with LLM...", total=None)
            tools = _generate_tools(
                api_request,
                functions,
                llm_provider,
                llm_model,
                embedding_provider,
                embedding_model,
                verbose,
            )
            progress.update(
                task3, completed=True, description=f"✓ Generated {len(tools)} tools"
            )

            if not tools:
                console.print(
                    "[red]No relevant tools could be generated for your request![/red]"
                )
                raise typer.Exit(1)

            # Step 4: Generate MCP server
            task4 = progress.add_task("Creating MCP server...", total=None)
            server_path = _generate_server(
                tools, repository, output, transport, verbose
            )
            progress.update(task4, completed=True, description="✓ MCP server generated")

            # Step 5: Start server (optional)
            server_process = None
            if start_server:
                task5 = progress.add_task("Starting MCP server...", total=None)
                server_process = _start_server(
                    repository, server_path, test_server, verbose
                )
                if server_process:
                    progress.update(
                        task5, completed=True, description="✓ MCP server started"
                    )
                else:
                    progress.update(
                        task5, completed=True, description="✗ Failed to start server"
                    )

        # Display results
        _display_results(tools, server_path, server_process, transport)

    except KeyboardInterrupt:
        console.print("\n[red]Operation cancelled by user[/red]")
        raise typer.Exit(1) from None
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        if verbose:
            import traceback

            console.print(traceback.format_exc())
        raise typer.Exit(1) from e


@app.command()
def test(
    server_path: Path = typer.Argument(..., help="Path to MCP server file"),
    timeout: int = typer.Option(10, "--timeout", "-t", help="Test timeout in seconds"),
):
    """Test an existing MCP server."""

    if not server_path.exists():
        console.print(f"[red]Server file not found: {server_path}[/red]")
        raise typer.Exit(1) from None

    console.print(f"Testing MCP server: [green]{server_path}[/green]")

    try:
        runner = MCPServerRunner()

        # Start server process
        python_exe = shutil.which("python")
        process = subprocess.Popen(
            [python_exe, str(server_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Test communication
        success, message = runner.test_server_communication(process, timeout)

        if success:
            console.print(f"[green]✓ Server test passed: {message}[/green]")
        else:
            console.print(f"[red]✗ Server test failed: {message}[/red]")
            raise typer.Exit(1)

        # Clean up
        runner.stop_server(process=process)

    except Exception as e:
        console.print(f"[red]Error testing server: {e}[/red]")
        raise typer.Exit(1) from e


def _prepare_repository(repo_url: str, verbose: bool) -> Path:
    """Prepare repository (clone or use local path)."""

    if Path(repo_url).exists():
        # Local path
        repo_path = Path(repo_url).resolve()
        if verbose:
            console.print(f"Using local repository: {repo_path}")
        return repo_path

    # Git URL - clone to temporary directory
    temp_dir = Path(tempfile.mkdtemp(prefix="mcpify_"))
    repo_name = repo_url.split("/")[-1].replace(".git", "")
    repo_path = temp_dir / repo_name

    try:
        _ = subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, str(repo_path)],
            capture_output=True,
            text=True,
            check=True,
        )
        if verbose:
            console.print(f"Cloned repository to: {repo_path}")
        return repo_path

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Failed to clone repository: {e.stderr}[/red]")
        raise typer.Exit(1) from e


def _analyze_repository(repo_path: Path, repo_url: str, verbose: bool) -> tuple:
    """Analyze repository structure and extract functions."""

    # Analyze repository metadata
    detector = DependencyDetector()
    repository = detector.analyze_repository(repo_path)
    repository.url = repo_url

    if verbose:
        console.print(f"Repository: {repository.name}")
        console.print(f"Python files: {len(repository.python_files)}")
        console.print(f"Dependencies: {len(repository.dependencies)}")

    # Parse Python functions
    parser = PythonParser()
    all_functions = []

    for py_file in repository.python_files:
        functions = parser.parse_file(py_file)
        all_functions.extend(functions)

    if verbose:
        console.print(f"Total functions found: {len(all_functions)}")

    return repository, all_functions


def _generate_tools(
    api_request: str,
    functions: List,
    llm_provider: str,
    llm_model: Optional[str],
    embedding_provider: str,
    embedding_model: Optional[str],
    verbose: bool,
):
    """Generate MCP tools using LLM."""

    try:
        matcher = APIMatcher(
            llm_provider=llm_provider,
            llm_model=llm_model,
            embedding_provider=embedding_provider,
            embedding_model=embedding_model,
        )

        # Filter functions to improve quality
        filtered_functions = matcher.filter_functions(
            functions,
            {
                "include_private": False,
                "min_docstring_length": 0,  # Allow functions without docstrings for Phase 0
                "max_parameters": 8,
            },
        )

        if verbose:
            console.print(f"Functions after filtering: {len(filtered_functions)}")

        # Generate tools
        tools = matcher.generate_tools(api_request, filtered_functions)

        return tools

    except Exception as e:
        console.print(f"[red]Error generating tools: {e}[/red]")
        raise


def _generate_server(
    tools, repository, output: Optional[Path], transport: str, verbose: bool
) -> Path:
    """Generate MCP server code using official MCP SDK."""

    if output is None:
        output = Path.cwd() / f"mcpify_{repository.name}"

    generator = MCPGenerator()
    server_path = generator.generate_server(tools, repository, output, transport)

    if verbose:
        console.print(
            f"Server generated at: {server_path} (using MCP SDK, {transport} transport)"
        )

    return server_path


def _start_server(
    repository, server_path: Path, test_communication: bool, verbose: bool
):
    """Start the MCP server."""

    try:
        runner = MCPServerRunner()
        success, message, process = runner.setup_and_run_server(repository, server_path)

        if not success:
            console.print(f"[red]Failed to start server: {message}[/red]")
            return None

        if verbose:
            console.print(f"Server started: {message}")

        # Test communication if requested
        if test_communication and process:
            success, test_message = runner.test_server_communication(process)
            if verbose:
                if success:
                    console.print(f"[green]Server test: {test_message}[/green]")
                else:
                    console.print(
                        f"[yellow]Server test failed: {test_message}[/yellow]"
                    )

        return process

    except Exception as e:
        console.print(f"[red]Error starting server: {e}[/red]")
        return None


def _display_results(tools, server_path: Path, server_process, transport: str):
    """Display final results."""

    # Tools table
    table = Table(title="Generated MCP Tools")
    table.add_column("Tool Name", style="cyan")
    table.add_column("Description", style="green")
    table.add_column("Source Function", style="yellow")

    for tool in tools:
        table.add_row(
            tool.name,
            tool.description[:60] + "..."
            if len(tool.description) > 60
            else tool.description,
            f"{tool.function_info.qualified_name} ({tool.function_info.file_path.name})",
        )

    console.print(table)

    # Server info
    console.print(f"\n[green]✓ MCP Server generated at:[/green] {server_path}")
    console.print(f"[green]✓ Server directory:[/green] {server_path.parent}")
    console.print(f"[green]✓ Transport mode:[/green] {transport}")

    if transport == "stdio":
        console.print("\n[blue]📋 STDIO Transport Usage:[/blue]")
        console.print(
            "[yellow]This server should be started by MCP clients, not directly.[/yellow]"
        )
        console.print("\n[cyan]For Claude Desktop:[/cyan]")
        console.print(f'Add to config: "command": "python", "args": ["{server_path}"]')
        console.print("\n[cyan]For testing:[/cyan]")
        console.print(f"Test manually: python {server_path}")
        console.print("[dim](The server will wait for JSON-RPC input via stdin)[/dim]")

    elif transport == "http":
        if server_process:
            console.print(
                f"[green]✓ HTTP Server running with PID:[/green] {server_process.pid}"
            )
            console.print("\n[cyan]HTTP Server endpoints:[/cyan]")
            console.print("  • Health check: http://127.0.0.1:8000/health")
            console.print("  • List tools: http://127.0.0.1:8000/tools")
            console.print("  • Call tool: POST http://127.0.0.1:8000/tools/{tool_name}")
            console.print(
                "\n[yellow]Note:[/yellow] Server is running in background. Use Ctrl+C to stop."
            )

            # Keep process alive
            try:
                server_process.wait()
            except KeyboardInterrupt:
                console.print("\n[yellow]Stopping HTTP server...[/yellow]")
                server_process.terminate()
        else:
            console.print(
                f"\n[yellow]Start HTTP server manually:[/yellow] python {server_path} --host 127.0.0.1 --port 8000"
            )


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
