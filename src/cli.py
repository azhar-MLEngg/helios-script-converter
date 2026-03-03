"""Command-line interface for the conversion system."""

import sys
from pathlib import Path
from typing import Optional

import click
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .orchestrator import ConversionOrchestrator


console = Console()


def setup_logging(verbose: bool = False) -> None:
    """Setup logging configuration.
    
    Args:
        verbose: Enable verbose logging.
    """
    logger.remove()
    
    log_level = "DEBUG" if verbose else "INFO"
    
    # Console logging
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level=log_level,
        colorize=True
    )
    
    # File logging
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    logger.add(
        log_dir / "converter.log",
        rotation="10 MB",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}"
    )


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Snowflake to StarRocks Conversion System.
    
    Convert Snowflake Python scripts to StarRocks-compatible format using AI agents.
    """
    pass


@cli.command()
@click.argument('input_file', type=click.Path(exists=True, path_type=Path))
@click.option(
    '-o', '--output',
    type=click.Path(path_type=Path),
    help='Output file path (default: <input>.converted.py)'
)
@click.option(
    '-c', '--config',
    type=click.Path(exists=True, path_type=Path),
    help='Path to config.yaml file'
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Enable verbose logging'
)
@click.option(
    '--no-validate',
    is_flag=True,
    help='Skip validation step'
)
def convert(
    input_file: Path,
    output: Optional[Path],
    config: Optional[Path],
    verbose: bool,
    no_validate: bool
):
    """Convert a Snowflake Python script to StarRocks format.
    
    Example:
        script-converter convert snowflake_script.py -o starrocks_script.py
    """
    setup_logging(verbose)
    
    console.print(Panel.fit(
        "[bold blue]Snowflake to StarRocks Conversion System[/bold blue]\n"
        "Powered by Claude Agent SDK",
        border_style="blue"
    ))
    
    # Determine output file
    if output is None:
        output = input_file.with_suffix('.converted.py')
    
    try:
        # Initialize orchestrator
        orchestrator = ConversionOrchestrator(config)
        
        # Override validation setting if flag is set
        if no_validate:
            orchestrator.config.settings.enable_validation = False
        
        # Perform conversion
        console.print(f"\n[bold]Input:[/bold] {input_file}")
        console.print(f"[bold]Output:[/bold] {output}\n")
        
        result = orchestrator.convert_script(input_file)
        
        # Save result
        orchestrator.save_result(result, output)
        
        # Display results
        _display_results(result, output)
        
        # Exit with appropriate code
        sys.exit(0 if result.success else 1)
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        logger.exception("Conversion failed")
        sys.exit(1)


@cli.command()
@click.option(
    '-c', '--config',
    type=click.Path(exists=True, path_type=Path),
    help='Path to config.yaml file'
)
def validate_connection(config: Optional[Path]):
    """Validate StarRocks database connection.
    
    Example:
        script-converter validate-connection
    """
    setup_logging()
    
    try:
        from .config_loader import load_config
        from .validator import ScriptValidator
        
        cfg = load_config(config)
        validator = ScriptValidator(cfg)
        
        console.print("\n[bold]Testing StarRocks connection...[/bold]")
        console.print(f"Host: {cfg.starrocks.host}:{cfg.starrocks.port}")
        console.print(f"Database: {cfg.starrocks.database}")
        console.print(f"User: {cfg.starrocks.user}\n")
        
        success, error = validator.validate_connection()
        
        if success:
            console.print("[bold green]✓ Connection successful![/bold green]")
            sys.exit(0)
        else:
            console.print(f"[bold red]✗ Connection failed:[/bold red] {error}")
            sys.exit(1)
            
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


@cli.command()
@click.argument('query', type=str)
@click.option(
    '-c', '--config',
    type=click.Path(exists=True, path_type=Path),
    help='Path to config.yaml file'
)
@click.option(
    '-v', '--verbose',
    is_flag=True,
    help='Enable verbose logging'
)
def convert_query(query: str, config: Optional[Path], verbose: bool):
    """Convert a single SQL query from Snowflake to StarRocks format.
    
    Example:
        script-converter convert-query "SELECT * FROM table"
    """
    setup_logging(verbose)
    
    try:
        from .config_loader import load_config
        from .query_converter import QueryConverter
        
        cfg = load_config(config)
        converter = QueryConverter(cfg)
        
        console.print("\n[bold]Original Query:[/bold]")
        console.print(Panel(query, border_style="yellow"))
        
        converted = converter.convert(query)
        
        console.print("\n[bold]Converted Query:[/bold]")
        console.print(Panel(converted, border_style="green"))
        
    except Exception as e:
        console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
        logger.exception("Query conversion failed")
        sys.exit(1)


def _display_results(result, output_file: Path) -> None:
    """Display conversion results in a formatted table.
    
    Args:
        result: ConversionResult object.
        output_file: Path to output file.
    """
    table = Table(title="Conversion Results", show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Status", "✓ Success" if result.success else "✗ Failed")
    table.add_row("Output File", str(output_file))
    table.add_row("Iterations", str(result.iterations))
    table.add_row("Manual Review", "Yes" if result.needs_manual_review else "No")
    
    if result.error_message:
        table.add_row("Error", result.error_message[:100] + "..." if len(result.error_message) > 100 else result.error_message)
    
    console.print("\n")
    console.print(table)
    
    if result.needs_manual_review:
        console.print("\n[bold yellow]⚠ Manual review required[/bold yellow]")
        console.print("Check the error log for details.")
    elif result.success:
        console.print("\n[bold green]✓ Conversion completed successfully![/bold green]")


if __name__ == "__main__":
    cli()
