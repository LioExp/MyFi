import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.text import Text

console = Console()

# --- TELA DE ABERTURA ESTILO CLAUDE CODE ---
def tela_abertura():
    console.clear()
    
    # ASCII Art personalizada para MyFi
    ascii_art = r"""
    ███╗   ███╗██╗   ██╗███████╗██╗
    ████╗ ████║╚██╗ ██╔╝██╔════╝██║
    ██╔████╔██║ ╚████╔╝ █████╗  ██║
    ██║╚██╔╝██║  ╚██╔╝  ██╔══╝  ██║
    ██║ ╚═╝ ██║   ██║   ██║     ██║
    ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝
    """
    # Se quiser um ASCII mais caprichado, use uma ferramenta como:
    # https://patorjk.com/software/taag/ (fonte "ANSI Shadow" ou "Big")
    
    console.print(ascii_art, style="bold cyan")
    console.print("* Welcome to MyFi - Network Configuration Assistant!", style="italic green")
    console.print()
    console.print("MYFI", style="bold white underline")
    console.print()
    console.print("MyFi helps you set up network monitoring and firewall rules easily.", style="white")
    console.print("It will detect active interfaces, test packet capture, and prepare your system.", style="white")
    console.print()
    console.print("Press Enter to begin the setup wizard...", style="bold yellow", end="")
    input()  # Aguarda Enter
    console.clear()

# --- Suas funções originais ---
def detectar_interfaces_up():
    resultado = subprocess.run(['ip', 'link', 'show'], capture_output=True, text=True)
    linhas = resultado.stdout.splitlines()
    interfaces = []
    for linha in linhas:
        if linha and linha[0].isdigit() and ':' in linha:
            nome = linha.split(':')[1].strip().split()[0]
            if 'state UP' in linha and nome != 'lo':
                interfaces.append(nome)
    return interfaces

def verificar_dependencias():
    deps = {"tshark": False, "iptables": False}
    for cmd in deps:
        if subprocess.run(['which', cmd], capture_output=True).returncode == 0:
            deps[cmd] = True
    return deps

def testar_captura(interface):
    try:
        cmd = ['tshark', '-c', '5', '-i', interface]
        resultado = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if resultado.returncode == 0:
            return True
        else:
            console.print(f"[red]tshark error: {resultado.stderr}[/red]")
            return False
    except FileNotFoundError:
        console.print("[red]tshark is not installed. Install it with: sudo apt install tshark (or equivalent)[/red]")
        return False
    except subprocess.TimeoutExpired:
        console.print(f"[yellow]The capture timed out after 15 seconds. The interface {interface} may not have traffic.[/yellow]")
        return False

def verificar_sudo():
    return subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0

# --- Wizard principal (agora com tela de abertura) ---
def wizard():
    tela_abertura()  # <-- Adiciona a experiência visual antes de tudo
    
    console.print(Panel.fit("[bold cyan]MyFi - Assistente de Configuração[/bold cyan]", border_style="cyan"))
    interfaces = detectar_interfaces_up()
    if not interfaces:
        console.print("[red]No interfaces found.[/red]")
        return
    
    table = Table(title="Interfaces")
    table.add_column("Nº", style="cyan")
    table.add_column("Nome", style="white")
    for i, iface in enumerate(interfaces, 1):
        table.add_row(str(i), iface)
    console.print(table)
    escolha = Prompt.ask("Choose the number", choices=[str(i) for i in range(1, len(interfaces)+1)])
    iface = interfaces[int(escolha)-1]
    console.print(f"[green]Selected: {iface}[/green]")
    
    console.print("[bold]Checking dependencies...[/bold]")
    deps = verificar_dependencias()
    if not all(deps.values()):
        console.print("[yellow]Some dependencies are missing. Install with: sudo apt install tshark iptables[/yellow]")
        if not Confirm.ask("Should we continue anyway?", default=False):
            return
        
    if not verificar_sudo():
        console.print("[yellow]You will be asked for the sudo password...[/yellow]")
        subprocess.run(['sudo', '-v'])
    console.print("[bold]Testing capture...[/bold]")
    if testar_captura(iface):
        console.print("[green]✓ Capture OK[/green]")
    else:
        console.print("[red]Capture failed[/red]")
        return
    
    console.print("[bold green]Setup complete![/bold green]")

if __name__ == "__main__":
    wizard()