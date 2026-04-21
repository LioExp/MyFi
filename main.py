import sys
import argparse
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from core.config_manager import is_configured
from ui.cli.setup_wizard import wizard
from core.Scanner import main as scan_main

console = Console()

def show_help():
    console.clear()
    
    ascii_art = r"""
    ███╗   ███╗██╗   ██╗███████╗██╗
    ████╗ ████║╚██╗ ██╔╝██╔════╝██║
    ██╔████╔██║ ╚████╔╝ █████╗  ██║
    ██║╚██╔╝██║  ╚██╔╝  ██╔══╝  ██║
    ██║ ╚═╝ ██║   ██║   ██║     ██║
    ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝
    """
    console.print(ascii_art, style="bold cyan")
    console.print("MyFi - Intelligent Network Monitor", style="bold white underline")
    console.print()
    
    # Tabela de comandos
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column(style="bold cyan", width=8)
    table.add_column(style="white")
    
    table.add_row("setup", "Run the configuration wizard")
    table.add_row("scan", "Scan the network for devices and activity")
    table.add_row("monitor", "Start continuous monitoring (coming soon)")
    
    console.print(table)
    console.print()
    console.print("Usage: [bold]myfi <command>[/bold]", style="dim")
    console.print("Example: [dim]$ myfi setup[/dim]")

class MyFiArgumentParser(argparse.ArgumentParser):
    
    def error(self, message):
        console.print(f"[red]✗ Error: {message}[/red]")
        console.print()
        show_help()
        sys.exit(2)
    
    def print_help(self):
        show_help()

def main():
    parser = MyFiArgumentParser(
        prog="myfi",
        description="MyFi - Intelligent Network Monitor",
        add_help=False  # Desabilitamos a ajuda padrão
    )
    parser.add_argument(
        "command",
        choices=["setup", "scan", "monitor"],
        help="Command to execute"
    )
    parser.add_argument(
        "-h", "--help",
        action="store_true",
        help="Show this help message"
    )
    
    try:
        args, unknown = parser.parse_known_args()
    except SystemExit:
        # Se o argparse tentar sair, mostramos nossa ajuda e saímos
        show_help()
        sys.exit(2)
    
    # Se -h/--help foi usado ou nenhum comando fornecido
    if args.help or not hasattr(args, 'command'):
        show_help()
        sys.exit(0)
    
    if args.command == "setup":
        wizard()
    elif args.command == "scan":
        if not is_configured():
            console.print("[red]✗ MyFi is not configured.[/red]")
            console.print("[yellow]Please run [bold]myfi setup[/bold] first.[/yellow]")
            sys.exit(1)
        scan_main()
    elif args.command == "monitor":
        console.print("[yellow]⚠️  Monitor mode is not yet implemented.[/yellow]")
    else:
        show_help()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Interrupted by user.[/yellow]")
        sys.exit(0)