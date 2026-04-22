import sys
import subprocess
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.text import Text
from rich.style import Style
from src.myfi.core.config_manager import save_config, is_configured

console = Console()

def tela_abertura():
    console.clear()

    ascii_art = r"""
    ███╗   ███╗██╗   ██╗███████╗██╗
    ████╗ ████║╚██╗ ██╔╝██╔════╝██║
    ██╔████╔██║ ╚████╔╝ █████╗  ██║
    ██║╚██╔╝██║  ╚██╔╝  ██╔══╝  ██║
    ██║ ╚═╝ ██║   ██║   ██║     ██║
    ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝
    """

    texto = Text()
    linhas = ascii_art.splitlines()
    total = max(len(linhas), 1)
    for i, linha in enumerate(linhas):
        p = i / (total - 1) if total > 1 else 0
        r = int(0 * (1 - p) + 255 * p)
        g = int(255 * (1 - p) + 255 * p)
        b = int(255 * (1 - p) + 255 * p)
        texto.append(linha + "\n", style=Style(color=f"#{r:02x}{g:02x}{b:02x}", bold=True))

    console.print(texto)
    console.print()
    console.print("✨ Welcome to MyFi - Network Configuration Assistant! ✨", style="bold italic green")
    console.print()
    console.print("MYFI", style="bold cyan underline2")
    console.print()
    console.print("MyFi helps you set up network monitoring and firewall rules easily.", style="white")
    console.print("It will detect active interfaces, test packet capture, and prepare your system.", style="white")
    console.print()
    console.print("▸ Press Enter to begin the setup wizard...", style="bold yellow", end="")
    input()

    console.print("\n" + "─" * 50, style="dim")
    console.print("[bold cyan]⚙️  Configuration Assistant[/bold cyan]\n")

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
            console.print(f"  [red]✗ tshark error: {resultado.stderr.strip()}[/red]")
            return False
    except FileNotFoundError:
        console.print("  [red]✗ tshark is not installed. Install with: sudo apt install tshark (or equivalent)[/red]")
        return False
    except subprocess.TimeoutExpired:
        console.print(f"  [yellow]! Capture timed out after 15 seconds on {interface}. Interface may be idle.[/yellow]")
        return False

def verificar_sudo():
    return subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0

def wizard():
    try:
        if is_configured():
            console.print("[green]✓ MyFi is already configured. Use 'myfi setup' to reconfigure it.[/green]")
            return
        tela_abertura()

        with console.status("[bold cyan]Detecting network interfaces...[/bold cyan]", spinner="dots"):
            interfaces = detectar_interfaces_up()

        if not interfaces:
            console.print("[red]✗ No active interfaces found (excluding loopback).[/red]")
            return

        console.print("[bold]Available interfaces:[/bold]")
        for i, iface in enumerate(interfaces, 1):
            console.print(f"  {i}. {iface}", style="cyan")
        console.print()

        escolha = Prompt.ask(
            "[bold]🔍 Choose interface number[/bold]",
            choices=[str(i) for i in range(1, len(interfaces)+1)],
            default="1"
        )
        iface = interfaces[int(escolha)-1]
        console.print(f"[green]✓ Selected: {iface}[/green]\n")

        console.print("[bold]📦 Checking dependencies...[/bold]")
        with console.status("[bold cyan]Checking for tshark and iptables...[/bold cyan]", spinner="dots"):
            deps = verificar_dependencias()

        for dep, installed in deps.items():
            if installed:
                console.print(f"  [green]✓[/green] {dep}")
            else:
                console.print(f"  [red]✗[/red] {dep}")

        if not all(deps.values()):
            console.print("\n[yellow]! Some dependencies are missing. Install with:[/yellow]")
            console.print("  [dim]$ sudo apt install tshark iptables[/dim]")
            if not Confirm.ask("[bold]Continue anyway?[/bold]", default=False):
                console.print("[yellow]Exiting setup.[/yellow]")
                return
            console.print()

        # --- SUDO com tratamento de falha de senha ---
        if not verificar_sudo():
            console.print("[yellow]🔐 Administrator privileges required.[/yellow]")
            console.print("[dim]Please enter your password when prompted.[/dim]")
            while True:
                resultado = subprocess.run(['sudo', '-v'], check=False)
                if resultado.returncode == 0:
                    console.print("[green]✓ Sudo access granted.[/green]")
                    break
                else:
                    console.print("[red]✗ Authentication failed.[/red]")
                    if not Confirm.ask("[bold]Try again?[/bold]", default=True):
                        console.print("[yellow]⚠️ Sudo access is required to continue. Exiting setup.[/yellow]")
                        return
        else:
            console.print("[green]✓ Sudo access already active.[/green]")
        console.print()

        # --- Teste de captura ---
        console.print(f"[bold]📡 Testing packet capture on [cyan]{iface}[/cyan]...[/bold]")
        captura_ok = testar_captura(iface)

        if captura_ok:
            console.print("[green]✓ Packet capture test passed successfully![/green]")
        else:
            console.print("[red]✗ Packet capture test failed. Check interface and permissions.[/red]")
            return

        console.print("\n[bold green]✅ Setup completed successfully![/bold green]")
        console.print("MyFi is ready to monitor and protect your network.", style="white")
        save_config({'interface':iface,'dependencies_ok': all(deps.values())})

    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Setup interrupted by user. Exiting gracefully.[/yellow]")
        sys.exit(0)


if __name__ == "__main__":
    wizard()