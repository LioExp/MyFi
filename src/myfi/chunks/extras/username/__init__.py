from __future__ import annotations

import logging
from typing import Any

from rich.table import Table

from myfi.core.base_chunk import BaseChunk
from myfi.chunks.extras.username.username_intel_plugin import UsernameIntelPlugin
from myfi.core.config_manager import ConfigManager
from myfi.ui.cli.theme import make_console

logger = logging.getLogger(__name__)


class UsernameIntelChunk(BaseChunk):

    def __init__(self, config: Any = None) -> None:
        super().__init__(config)
        self.plugin = UsernameIntelPlugin()

    @staticmethod
    def manifest() -> dict:
        return {
            "name":        "UsernameIntel",
            "version":     "4.0.0",
            "description": (
                "Verifica username em 600+ plataformas via WhatsMyName dataset. "
                "Engine própria com regras de detecção por plataforma — sem subprocess, "
                "sem Sherlock, sem falsos positivos por HTTP 200."
            ),
            "inputs":      {"username": {"type": "str", "required": True}},
            "outputs":     {
                "results": {"type": "list"},
                "intel":   {"type": "dict"},
                "engine":  {"type": "str"},
            },
            "permissions":  ["network:outbound"],
            "cli_commands": ["username --query <nome>"],
        }

    def run(self, input_data: dict = None) -> dict:
        input_data = input_data or {}
        raw = input_data.get("username", "").strip()

        if not raw:
            return {
                "results": [], "intel": {}, "engine": "none",
                "error": "Username não fornecido.",
            }

        try:
            return self.plugin.search(raw)

        except ValueError as e:
            logger.warning(f"UsernameIntel: input inválido: {e}")
            return {"results": [], "intel": {}, "engine": "none", "error": str(e)}

        except RuntimeError as e:
            # dataset não disponível
            logger.error(f"UsernameIntel: {e}")
            return {"results": [], "intel": {}, "engine": "none", "error": str(e)}

        except Exception as e:
            logger.exception(f"UsernameIntel: erro inesperado: {e}")
            return {"results": [], "intel": {}, "engine": "none", "error": str(e)}


def register_chunk(engine, subparsers) -> None:
    chunk = UsernameIntelChunk(ConfigManager())
    engine.register(chunk)

    p = subparsers.add_parser("username", help="Verificar username em plataformas")
    p.add_argument("--query", type=str, required=True)

    engine.register_cli_handler("username", _make_username_callback(chunk))


def _make_username_callback(chunk: UsernameIntelChunk):

    def _callback(args) -> None:
        console = make_console()

        console.print(
            f"\n[myfi.dim]── USERNAME INTEL {'─' * 22} [ {args.query} ][/myfi.dim]"
        )

        with console.status(
            f"[myfi.cyan]A pesquisar '{args.query}' via WhatsMyName...[/myfi.cyan]",
            spinner="dots",
        ):
            result = chunk.run({"username": args.query})

        # ── Erro ─────────────────────────────────────────────────
        if error := result.get("error"):
            console.print(f"[myfi.red][ FAIL ] {error}[/myfi.red]")
            return

        results  = result.get("results", [])
        intel    = result.get("intel", {})
        found    = [r for r in results if r.get("found")]
        n_found  = intel.get("total_found",        len(found))
        n_total  = intel.get("total_checked",       len(results))
        n_incl   = intel.get("total_inconclusive",  0)
        n_errors = intel.get("total_errors",        0)
        elapsed  = intel.get("elapsed_s",           "--")
        score    = intel.get("exposure_score",      "--")
        cats     = intel.get("categories",          {})

        if not results:
            console.print("[myfi.amber][ WARN ] Nenhuma plataforma verificada.[/myfi.amber]")
            return

        # ── Score color ───────────────────────────────────────────
        _SCORE_STYLE = {
            "none":     "myfi.dim",
            "low":      "myfi.green",
            "medium":   "myfi.amber",
            "high":     "myfi.red",
            "critical": "bold myfi.red",
        }
        sc  = _SCORE_STYLE.get(score, "myfi.body")
        score_str = f"[{sc}]{score}[/{sc}]"

        # ── Cabeçalho ─────────────────────────────────────────────
        console.print(
            f"\n"
            f"  [myfi.dim]username[/myfi.dim]        [myfi.cyan]{args.query}[/myfi.cyan]\n"
            f"  [myfi.dim]engine[/myfi.dim]          [myfi.body]wmn (WhatsMyName)[/myfi.body]\n"
            f"  [myfi.dim]checked[/myfi.dim]         [myfi.body]{n_total} platforms[/myfi.body]\n"
            f"  [myfi.dim]found[/myfi.dim]           [bold myfi.green]{n_found}[/bold myfi.green]\n"
            f"  [myfi.dim]inconclusive[/myfi.dim]    [myfi.dim]{n_incl}[/myfi.dim]\n"
            f"  [myfi.dim]errors[/myfi.dim]          [myfi.amber]{n_errors}[/myfi.amber]\n"
            f"  [myfi.dim]elapsed[/myfi.dim]         [myfi.body]{elapsed}s[/myfi.body]\n"
            f"  [myfi.dim]exposure score[/myfi.dim]  {score_str}"
        )

        # ── Categorias ────────────────────────────────────────────
        if cats:
            console.print(f"\n[myfi.dim]── CATEGORIES[/myfi.dim]")
            for cat, platforms in sorted(cats.items()):
                console.print(
                    f"  [myfi.cyan]{cat:<16}[/myfi.cyan]"
                    f"[myfi.body]{', '.join(platforms)}[/myfi.body]"
                )

        # ── Plataformas encontradas ───────────────────────────────
        console.print(f"\n[myfi.dim]── FOUND ({n_found})[/myfi.dim]")
        if found:
            table = Table(show_header=False, box=None, padding=(0, 2))
            table.add_column(style="myfi.green", width=6)
            table.add_column(style="myfi.body",  width=24)
            table.add_column(style="myfi.dim",   width=10)
            table.add_column(style="myfi.blue")
            for r in found:
                table.add_row("[ ON ]", r["platform"], f"[{r['cat']}]", r["url"])
            console.print(table)
        else:
            console.print("  [myfi.dim]nenhum[/myfi.dim]")

        # ── Inconclusive (sites que não confirmaram nem negaram) ──
        incl_list = [r for r in results if "inconclusive" in r.get("status", "")]
        if incl_list:
            console.print(
                f"\n[myfi.dim]── INCONCLUSIVE ({n_incl}) "
                f"— verificação não confirmada, pode requerer investigação manual[/myfi.dim]"
            )
            incl_table = Table(show_header=False, box=None, padding=(0, 2))
            incl_table.add_column(style="myfi.dim", width=6)
            incl_table.add_column(style="myfi.body", width=24)
            incl_table.add_column(style="myfi.dim")
            for r in incl_list[:20]:   # mostra só os primeiros 20
                incl_table.add_row("[?]", r["platform"], r["status"])
            if len(incl_list) > 20:
                console.print(f"  [myfi.dim]... e mais {len(incl_list) - 20}[/myfi.dim]")
            console.print(incl_table)

        # ── Google Dorks ──────────────────────────────────────────
        dorks = intel.get("google_dorks", [])
        if dorks:
            console.print(f"\n[myfi.dim]── GOOGLE DORKS[/myfi.dim]")
            dork_table = Table(show_header=False, box=None, padding=(0, 2))
            dork_table.add_column(style="myfi.dim",  width=24)
            dork_table.add_column(style="myfi.blue")
            for d in dorks:
                dork_table.add_row(d["name"], d["url"])
            console.print(dork_table)

        # ── Rodapé ────────────────────────────────────────────────
        console.print(
            f"\n[myfi.dim]{'─' * 60}[/myfi.dim]\n"
            f"[myfi.dim]checked: [/myfi.dim][myfi.cyan]{n_total}[/myfi.cyan]"
            f"[myfi.dim]  ·  found: [/myfi.dim][myfi.green]{n_found}[/myfi.green]"
            f"[myfi.dim]  ·  inconclusive: [/myfi.dim][myfi.dim]{n_incl}[/myfi.dim]"
            f"[myfi.dim]  ·  exposure: [/myfi.dim]{score_str}"
            f"[myfi.dim]  ·  {elapsed}s[/myfi.dim]"
        )
        console.print()

    return _callback
