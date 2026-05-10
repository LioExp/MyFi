# src/myfi/ui/cli/setup_wizard.py
from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

import requests
from rich.prompt import Prompt
from rich.table import Table

from myfi.core.config_manager import ConfigManager
from myfi.ui.cli.theme import make_console

logger = logging.getLogger(__name__)

# ════════════════════════════════════════════════════════════════
# CONSTANTES
# ════════════════════════════════════════════════════════════════

_BANNER = r"""
   ███╗   ███╗██╗   ██╗███████╗██╗
   ████╗ ████║╚██╗ ██╔╝██╔════╝██║
   ██╔████╔██║ ╚████╔╝ █████╗  ██║
   ██║╚██╔╝██║  ╚██╔╝  ██╔══╝  ██║
   ██║ ╚═╝ ██║   ██║   ██║     ██║
   ╚═╝     ╚═╝   ╚═╝   ╚═╝     ╚═╝
        network observability platform
"""

DEVICE_TYPES: dict[str, dict[str, str]] = {
    "1": {
        "key":  "local_pc",
        "name": "This PC / Local Server",
        "desc": "Monitors traffic on this machine only.",
    },
    "2": {
        "key":  "hotspot",
        "name": "Hotspot (MiFi / Phone)",
        "desc": "Collects data from all devices connected to the hotspot.",
    },
    "3": {
        "key":  "router",
        "name": "Home Router",
        "desc": "Collects data from all devices on the local network.",
    },
}


# ════════════════════════════════════════════════════════════════
# WIZARD
# ════════════════════════════════════════════════════════════════

class SetupWizard:
    """Assistente de configuracao inicial do MyFi."""

    def __init__(self, config: ConfigManager | None = None) -> None:
        self.config  = config or ConfigManager()
        self.console = make_console()

    # ── abertura ─────────────────────────────────────────────────

    def _show_opening(self) -> None:
        self.console.clear()
        self.console.print(_BANNER, style="myfi.cyan")
        self.console.rule(
            "[bold myfi.cyan]MyFi[/bold myfi.cyan] "
            "[myfi.dim]Configuration Assistant[/myfi.dim]",
            style="myfi.cyan",
        )
        self.console.print(
            "\n[myfi.body]MyFi will detect active interfaces, verify dependencies,"
            " and prepare your system.[/myfi.body]\n"
        )
        Prompt.ask(
            "[myfi.dim]Press Enter to begin[/myfi.dim]",
            default="",
            show_default=False,
        )
        self.console.print()

    # ── helpers ───────────────────────────────────────────────────

    def _confirm(self, message: str, default: bool = True) -> bool:
        default_str = "y" if default else "n"
        answer = Prompt.ask(
            f"[myfi.amber]{message} [y/n][/myfi.amber]",
            default=default_str,
        ).strip().lower()
        return answer in ("y", "yes")

    # ── detecção de sistema ───────────────────────────────────────

    @staticmethod
    def _detect_interfaces() -> list[str]:
        try:
            result = subprocess.run(
                ["ip", "link", "show"],
                capture_output=True, text=True, check=True,
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"ip link show falhou: {e}")
            return []

        interfaces = []
        for line in result.stdout.splitlines():
            if line and line[0].isdigit() and ":" in line:
                name = line.split(":")[1].strip().split()[0]
                if "state UP" in line and name != "lo":
                    interfaces.append(name)
        return interfaces

    @staticmethod
    def _check_dependencies() -> dict[str, bool]:
        deps = {"tshark": False, "iptables": False}
        for cmd in deps:
            deps[cmd] = (
                subprocess.run(
                    ["which", cmd], capture_output=True
                ).returncode == 0
            )
        return deps

    @staticmethod
    def _test_capture(iface: str) -> tuple[bool, str]:
        """
        Testa captura de pacotes na interface.
        Devolve (sucesso, mensagem).
        """
        try:
            result = subprocess.run(
                ["tshark", "-c", "5", "-i", iface],
                capture_output=True, text=True, timeout=15,
            )
            if result.returncode == 0:
                return True, "capture test passed."
            return False, result.stderr.strip()[:120]
        except FileNotFoundError:
            return False, "tshark not found. Install with: sudo apt install tshark"
        except PermissionError:
            return False, "permission denied. Run with sudo or add user to 'wireshark' group."
        except subprocess.TimeoutExpired:
            return False, "capture timed out (15s). Interface may be idle."

    @staticmethod
    def _check_sudo() -> bool:
        return subprocess.run(
            ["sudo", "-n", "true"], capture_output=True
        ).returncode == 0

    # ── passos do wizard ──────────────────────────────────────────

    def _step_device_type(self) -> str:
        self.console.print(
            "[myfi.dim]── STEP 1 ── Device Type[/myfi.dim]\n"
        )

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="myfi.cyan",  width=4)
        table.add_column(style="myfi.body",  width=28)
        table.add_column(style="myfi.dim")

        for key, info in DEVICE_TYPES.items():
            table.add_row(key, info["name"], info["desc"])

        self.console.print(table)
        self.console.print()

        choice = Prompt.ask(
            "[myfi.cyan]Choose option[/myfi.cyan]",
            choices=list(DEVICE_TYPES.keys()),
            default="1",
        )
        device_type = DEVICE_TYPES[choice]
        self.console.print(
            f"[myfi.green][  OK  ] Selected: {device_type['name']}[/myfi.green]\n"
        )
        return device_type["key"]

    def _step_interface(self) -> str | None:
        self.console.print(
            "[myfi.dim]── STEP 2 ── Network Interface[/myfi.dim]\n"
        )

        with self.console.status(
            "[myfi.cyan]Detecting active interfaces...[/myfi.cyan]", spinner="dots"
        ):
            interfaces = self._detect_interfaces()

        if not interfaces:
            self.console.print(
                "[myfi.red][ FAIL ] No active interfaces found.[/myfi.red]"
            )
            return None

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="myfi.cyan", width=4)
        table.add_column(style="myfi.body")

        for i, name in enumerate(interfaces, 1):
            table.add_row(str(i), name)

        self.console.print(table)
        self.console.print()

        choice = Prompt.ask(
            "[myfi.cyan]Choose interface[/myfi.cyan]",
            choices=[str(i) for i in range(1, len(interfaces) + 1)],
            default="1",
        )
        iface = interfaces[int(choice) - 1]
        self.console.print(
            f"[myfi.green][  OK  ] Interface: {iface}[/myfi.green]\n"
        )
        return iface

    def _step_dependencies(self) -> bool:
        """Verifica dependencias. Devolve True se tudo ok ou utilizador aceita continuar."""
        self.console.print(
            "[myfi.dim]── STEP 3 ── Dependencies[/myfi.dim]\n"
        )

        with self.console.status(
            "[myfi.cyan]Checking dependencies...[/myfi.cyan]", spinner="dots"
        ):
            deps = self._check_dependencies()

        all_ok = True
        for name, found in deps.items():
            if found:
                self.console.print(
                    f"  [myfi.green][ OK ][/myfi.green]  [myfi.body]{name}[/myfi.body]"
                )
            else:
                self.console.print(
                    f"  [myfi.red][MISS][/myfi.red]  [myfi.body]{name}[/myfi.body]"
                )
                all_ok = False

        self.console.print()

        if not all_ok:
            self.console.print(
                "[myfi.amber][ WARN ] Missing dependencies.[/myfi.amber]\n"
                "[myfi.dim]         Install tshark: sudo apt install tshark[/myfi.dim]\n"
            )
            if not self._confirm("Continue without all dependencies?", default=False):
                return False

        return True

    def _step_capture_test(self, iface: str) -> bool:
        self.console.print(
            f"[myfi.dim]── STEP 4 ── Capture Test ({iface})[/myfi.dim]\n"
        )

        with self.console.status(
            f"[myfi.cyan]Testing capture on {iface}...[/myfi.cyan]", spinner="dots"
        ):
            ok, msg = self._test_capture(iface)

        if ok:
            self.console.print(
                f"[myfi.green][  OK  ] {msg}[/myfi.green]\n"
            )
        else:
            self.console.print(
                f"[myfi.red][ FAIL ] {msg}[/myfi.red]\n"
            )
        return ok

    def _step_sudo(self) -> bool:
        self.console.print(
            "[myfi.dim]── STEP 4a ── Sudo Access[/myfi.dim]\n"
        )

        if self._check_sudo():
            self.console.print(
                "[myfi.green][  OK  ] Sudo access active.[/myfi.green]\n"
            )
            return True

        self.console.print(
            "[myfi.amber][ WARN ] Administrator privileges required.[/myfi.amber]\n"
            "[myfi.dim]         You will be prompted for your password.[/myfi.dim]\n"
        )

        for attempt in range(3):
            result = subprocess.run(["sudo", "-v"], check=False)
            if result.returncode == 0:
                self.console.print(
                    "[myfi.green][  OK  ] Sudo access granted.[/myfi.green]\n"
                )
                return True
            self.console.print(
                f"[myfi.red][ FAIL ] Authentication failed "
                f"(attempt {attempt + 1}/3).[/myfi.red]"
            )
            if attempt < 2 and not self._confirm("Try again?", default=True):
                break

        self.console.print(
            "[myfi.red][ FAIL ] Sudo access required. Exiting setup.[/myfi.red]"
        )
        return False

    def _step_hotspot(self) -> None:
        self.console.print(
            "[myfi.dim]── STEP 3 ── Hotspot Configuration[/myfi.dim]\n"
        )

        hotspot_url = Prompt.ask(
            "[myfi.cyan]Hotspot address[/myfi.cyan]",
            default="http://192.168.1.1",
        )

        models = ["Huawei_E5576", "ZTE_MF927U", "generic"]
        table  = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="myfi.cyan", width=4)
        table.add_column(style="myfi.body")
        for i, m in enumerate(models, 1):
            table.add_row(str(i), m)
        self.console.print(table)
        self.console.print()

        model_choice = Prompt.ask(
            "[myfi.cyan]Choose model[/myfi.cyan]",
            choices=[str(i) for i in range(1, len(models) + 1)],
            default=str(len(models)),
        )
        model = models[int(model_choice) - 1]

        self.console.print(
            "\n[myfi.dim]Hotspot admin credentials:[/myfi.dim]"
        )
        username = Prompt.ask("[myfi.cyan]Username[/myfi.cyan]", default="admin")
        password = Prompt.ask(
            "[myfi.cyan]Password[/myfi.cyan]", password=True
        )

        self.config.set("device_type",      "hotspot")
        self.config.set("hotspot_url",      hotspot_url)
        self.config.set("hotspot_model",    model)
        self.config.set("hotspot_username", username)
        self.config.set("hotspot_password", password)

        self.console.print(
            "[myfi.dim]Connection to hotspot will be validated during monitoring.[/myfi.dim]\n"
        )

    def _step_telegram(self) -> None:
        self.console.print(
            "[myfi.dim]── OPTIONAL ── Telegram Alerts[/myfi.dim]\n"
        )
        self.console.print(
            "[myfi.body]MyFi can send network alerts directly to your Telegram chat.[/myfi.body]\n"
            "[myfi.dim]Get a token from @BotFather · Get your chat ID from @userinfobot[/myfi.dim]\n"
        )

        if not self._confirm("Configure Telegram alerts now?", default=True):
            self.console.print("[myfi.dim]Telegram setup skipped.[/myfi.dim]\n")
            return

        token   = Prompt.ask("[myfi.cyan]Bot token[/myfi.cyan]",   password=True)
        chat_id = Prompt.ask("[myfi.cyan]Chat ID[/myfi.cyan]",     password=True)

        with self.console.status(
            "[myfi.cyan]Validating Telegram credentials...[/myfi.cyan]", spinner="dots"
        ):
            ok, msg = self._validate_telegram(token, chat_id)

        if ok:
            self.console.print(
                "[myfi.green][  OK  ] Credentials valid. Bot is ready.[/myfi.green]\n"
            )
            self.config.set("telegram_token",   token)
            self.config.set("telegram_chat_id", chat_id)
        else:
            self.console.print(
                f"[myfi.red][ FAIL ] Could not validate credentials: {msg}[/myfi.red]"
            )
            self.console.print(
                "[myfi.dim]Check your token and chat ID and try again later.[/myfi.dim]\n"
            )
            if self._confirm("Save credentials anyway?", default=False):
                self.config.set("telegram_token",   token)
                self.config.set("telegram_chat_id", chat_id)

    @staticmethod
    def _validate_telegram(token: str, chat_id: str) -> tuple[bool, str]:
        """
        Envia mensagem de teste ao Telegram.
        Devolve (sucesso, mensagem de erro ou vazio).
        """
        try:
            url  = f"https://api.telegram.org/bot{token}/sendMessage"
            resp = requests.post(
                url,
                data={"chat_id": chat_id, "text": "[  OK  ] MyFi configured successfully."},
                timeout=10,
            )
            resp.raise_for_status()
            if resp.json().get("ok"):
                return True, ""
            return False, resp.json().get("description", "API returned ok=false.")
        except requests.Timeout:
            return False, "timeout connecting to Telegram."
        except requests.ConnectionError:
            return False, "no network connection."
        except requests.HTTPError as e:
            return False, f"HTTP {e.response.status_code}."
        except Exception as e:
            logger.error(f"_validate_telegram: {e}")
            return False, str(e)

    # ════════════════════════════════════════════════════════════
    # ENTRY POINT
    # ════════════════════════════════════════════════════════════

    def run(self) -> None:
        # silencia logs do ConfigManager durante o wizard
        cfg_logger = logging.getLogger("myfi.core.config_manager")
        original   = cfg_logger.level
        cfg_logger.setLevel(logging.WARNING)

        try:
            self._run()
        finally:
            cfg_logger.setLevel(original)

    def _run(self) -> None:
        if self.config.is_configured():
            self.console.print(
                "[myfi.amber][ WARN ] MyFi is already configured.[/myfi.amber]"
            )
            if not self._confirm("Reconfigure MyFi?"):
                return
            self.config.reset()          # método público — sem acesso a _config

        self._show_opening()

        # ── step 1: tipo de dispositivo ──────────────────────────
        device_type = self._step_device_type()
        self.config.set("device_type", device_type)

        # ── step 2: interface ────────────────────────────────────
        iface = self._step_interface()
        if iface is None:
            return
        self.config.set("interface", iface)

        # ── steps específicos por tipo ───────────────────────────
        if device_type == "local_pc":
            if not self._step_dependencies():
                return
            if not self._step_sudo():
                return
            ok, _ = self._test_capture(iface)
            if not self._step_capture_test(iface):
                if not self._confirm(
                    "Capture test failed. Continue anyway?", default=False
                ):
                    return
            self.config.set("dependencies_ok", True)

        elif device_type == "hotspot":
            self._step_hotspot()

        elif device_type == "router":
            self.console.print(
                "[myfi.amber][ WARN ] Router mode is under development.[/myfi.amber]\n"
                "[myfi.dim]         Functionality will be limited in this version.[/myfi.dim]\n"
            )
            # não faz silent fallback — guarda 'router' e avisa
            self.config.set("dependencies_ok", False)

        # ── telegram (opcional) ──────────────────────────────────
        self._step_telegram()

        # ── save único no final ──────────────────────────────────
        self.config.save()

        self.console.print(
            "\n[myfi.green][  OK  ] Setup completed successfully.[/myfi.green]"
        )
        self.console.print(
            "[myfi.dim]MyFi is ready. Run [/myfi.dim]"
            "[myfi.cyan]myfi monitor start[/myfi.cyan]"
            "[myfi.dim] to begin.[/myfi.dim]\n"
        )
        logger.info(f"Setup completed. Interface: {iface}, Type: {device_type}")


# ════════════════════════════════════════════════════════════════
# ENTRY POINT STANDALONE
# ════════════════════════════════════════════════════════════════

def main() -> None:
    try:
        SetupWizard().run()
    except KeyboardInterrupt:
        make_console().print(
            "\n[myfi.amber][ WARN ] Setup interrupted.[/myfi.amber]"
        )
        sys.exit(0)
    except Exception as e:
        logger.exception("Unexpected error during setup.")
        make_console().print(f"[myfi.red][ FAIL ] {e}[/myfi.red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
