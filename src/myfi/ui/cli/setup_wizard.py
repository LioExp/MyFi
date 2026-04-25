import sys
import subprocess
import logging
import requests
import getpass
from rich.console import Console
from rich.prompt import Prompt
from rich.text import Text
from rich.style import Style
from myfi.core.config_manager import ConfigManager

logger = logging.getLogger(__name__)
console = Console()

class SetupWizard:
    """Assistente de configuração inicial do MyFi."""

    def __init__(self, config: ConfigManager = None):
        if config is None:
            config = ConfigManager()
        self.config = config

    @staticmethod
    def _ascii_art():
        return r"""
    ███╗   ███╗██╗   ██╗███████╗██╗
    ████╗ ████║╚██╗ ██╔╝██╔════╝██║
    ██╔████╔██║ ╚████╔╝ █████╗  ██║
    ██║╚██╔╝██║  ╚██╔╝  ██╔══╝  ██║
    ██║ ╚═╝ ██║   ██║   ██║     ██║
    ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝
    """

    def _mostrar_tela_abertura(self):
        console.clear()
        ascii_art = self._ascii_art()
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

    @staticmethod
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

    @staticmethod
    def verificar_dependencias():
        deps = {"tshark": False, "iptables": False}
        for cmd in deps:
            if subprocess.run(['which', cmd], capture_output=True).returncode == 0:
                deps[cmd] = True
        return deps

    @staticmethod
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
            console.print("  [red]✗ tshark is not installed. Install with: sudo apt install tshark[/red]")
            return False
        except subprocess.TimeoutExpired:
            console.print(f"  [yellow]! Capture timed out after 15 seconds on {interface}. Interface may be idle.[/yellow]")
            return False

    @staticmethod
    def verificar_sudo():
        return subprocess.run(['sudo', '-n', 'true'], capture_output=True).returncode == 0

    def _confirm(self, message: str, default: bool = True) -> bool:
        """Confirmação personalizada com estilo Rich (substitui Confirm.ask)."""
        default_str = "Y" if default else "N"
        prompt_text = f"[bold yellow]{message} [y/n][/bold yellow]"

        while True:
            try:
                answer = Prompt.ask(prompt_text, default=default_str).lower()
                if answer in ('y', 'yes'):
                    return True
                elif answer in ('n', 'no'):
                    return False
                console.print("[red]Por favor, responda 'y' para sim ou 'n' para não.[/red]")
            except KeyboardInterrupt:
                raise
            except Exception as e:
                logger.error(f"Erro inesperado na confirmação: {e}")
                return default

    def _configurar_telegram(self):
        """Passo opcional: configurar alertas via Telegram (entrada oculta)."""
        console.print("\n[bold]📢 Alertas Telegram[/bold]")
        console.print("O MyFi pode enviar-lhe alertas sobre a rede diretamente no seu chat do Telegram.")
        if not self._confirm("Deseja configurar alertas Telegram agora?", default=True):
            console.print("[dim]Configuração do Telegram saltada.[/dim]")
            return

        console.print("\nPara criar um bot e obter o token, fale com o [bold]@BotFather[/bold] no Telegram.")
        console.print("Para descobrir o seu chat ID, fale com o [bold]@userinfobot[/bold].")
        console.print("[yellow]🔒 Por segurança, o token e o chat ID serão digitados de forma oculta.[/yellow]")

        token = getpass.getpass("🔐 Token do seu bot Telegram (não será exibido): ")
        chat_id = getpass.getpass("💬 Chat ID (número, não será exibido): ")

        with console.status("[bold cyan]Verificando credenciais Telegram...[/bold cyan]", spinner="dots"):
            validado = self._validar_credenciais_telegram(token, chat_id)

        if validado:
            console.print("[green]✓ Credenciais válidas. O bot está pronto a comunicar.[/green]")
            self.config.set('telegram_token', token)
            self.config.set('telegram_chat_id', chat_id)
        else:
            console.print("[red]✗ Não foi possível validar as credenciais.[/red]")
            console.print("Verifique o token e o chat ID e tente novamente mais tarde.")
            if self._confirm("Guardar mesmo assim?", default=False):
                self.config.set('telegram_token', token)
                self.config.set('telegram_chat_id', chat_id)

    @staticmethod
    def _validar_credenciais_telegram(token: str, chat_id: str) -> bool:
        """Envia uma mensagem de teste para validar o token e o chat ID."""
        try:
            url = f"https://api.telegram.org/bot{token}/sendMessage"
            payload = {"chat_id": chat_id, "text": "✅ MyFi configurado com sucesso!"}
            response = requests.post(url, data=payload, timeout=10)
            return response.json().get("ok", False)
        except Exception:
            return False

    def run(self):
        """Executa o assistente de configuração completo."""
        # Silenciar logs do ConfigManager durante o assistente para manter a UI limpa
        config_logger = logging.getLogger('myfi.core.config_manager')
        original_level = config_logger.level
        config_logger.setLevel(logging.WARNING)

        try:
            if self.config.is_configured():
                console.print("[yellow]⚠️  MyFi já está configurado.[/yellow]")
                if not self._confirm("Deseja reconfigurar o MyFi?"):
                    return
                self.config._config = None

            self._mostrar_tela_abertura()

            # 1. Detetar interfaces
            with console.status("[bold cyan]Detecting network interfaces...[/bold cyan]", spinner="dots"):
                interfaces = self.detectar_interfaces_up()

            if not interfaces:
                console.print("[red]✗ No active interfaces found (excluding loopback).[/red]")
                return

            console.print("[bold]Available interfaces:[/bold]")
            for i, iface_name in enumerate(interfaces, 1):
                console.print(f"  {i}. {iface_name}", style="cyan")
            console.print()

            escolha = Prompt.ask(
                "[bold]🔍 Choose interface number[/bold]",
                choices=[str(i) for i in range(1, len(interfaces)+1)],
                default="1"
            )
            iface = interfaces[int(escolha)-1]
            console.print(f"[green]✓ Selected: {iface}[/green]\n")

            # 2. Verificar dependências
            console.print("[bold]📦 Checking dependencies...[/bold]")
            with console.status("[bold cyan]Checking for tshark and iptables...[/bold cyan]", spinner="dots"):
                deps = self.verificar_dependencias()

            for dep, installed in deps.items():
                if installed:
                    console.print(f"  [green]✓[/green] {dep}")
                else:
                    console.print(f"  [red]✗[/red] {dep}")

            if not all(deps.values()):
                console.print("\n[yellow]! Some dependencies are missing. Install with:[/yellow]")
                console.print("  [dim]$ sudo apt install tshark iptables[/dim]")
                if not self._confirm("Continuar mesmo assim?", default=False):
                    console.print("[yellow]Exiting setup.[/yellow]")
                    return
                console.print()

            # 3. Verificar acesso sudo
            if not self.verificar_sudo():
                console.print("[yellow]🔐 Administrator privileges required.[/yellow]")
                console.print("[dim]Please enter your password when prompted.[/dim]")
                while True:
                    resultado = subprocess.run(['sudo', '-v'], check=False)
                    if resultado.returncode == 0:
                        console.print("[green]✓ Sudo access granted.[/green]")
                        break
                    else:
                        console.print("[red]✗ Authentication failed.[/red]")
                        if not self._confirm("Tentar novamente?", default=True):
                            console.print("[yellow]⚠️ Sudo access is required to continue. Exiting setup.[/yellow]")
                            return
            else:
                console.print("[green]✓ Sudo access already active.[/green]")
            console.print()

            # 4. Teste de captura
            console.print(f"[bold]📡 Testing packet capture on [cyan]{iface}[/cyan]...[/bold]")
            captura_ok = self.testar_captura(iface)

            if not captura_ok:
                console.print("[red]✗ Packet capture test failed. Check interface and permissions.[/red]")
                return

            console.print("[green]✓ Packet capture test passed successfully![/green]")

            # 5. Guardar configuração base
            self.config.set('interface', iface)
            self.config.set('dependencies_ok', all(deps.values()))

            console.print("\n[bold green]✓ Configuração de rede concluída![/bold green]")

            # 6. Configurar Telegram
            self._configurar_telegram()

            # Único save ao terminar todas as etapas
            self.config.save()

            console.print("\n[bold green]✅ Setup concluído com sucesso![/bold green]")
            console.print("MyFi está pronto para monitorizar e proteger a sua rede.", style="white")
            logger.info(f"Setup concluído. Interface: {iface}")

        finally:
            # Restaurar o nível original do logger, aconteça o que acontecer
            config_logger.setLevel(original_level)


def main():
    """Ponto de entrada para o comando 'myfi setup'."""
    try:
        wizard = SetupWizard()
        wizard.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ Setup interrompido. A sair graciosamente.[/yellow]")
        sys.exit(0)
    except Exception as e:
        logger.exception("Erro inesperado durante o setup")
        console.print(f"[red]✗ Erro inesperado: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()