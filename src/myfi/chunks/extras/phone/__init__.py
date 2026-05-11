from __future__ import annotations

import logging
from typing import Any

from rich.prompt import Confirm
from rich.table import Table

from myfi.core.base_chunk import BaseChunk
from myfi.chunks.extras.phone.phone_intel_plugin import PhoneIntelPlugin
from myfi.core.config_manager import ConfigManager
from myfi.ui.cli.theme import make_console

logger = logging.getLogger(__name__)


class PhoneIntelChunk(BaseChunk):

    def __init__(self, config: Any = None):
        super().__init__(config)
        self.plugin = PhoneIntelPlugin(config)

    @staticmethod
    def manifest() -> dict:
        return {
            "name":        "PhoneIntel",
            "version":     "1.0.0",
            "description": "Analyzes a phone number (carrier, country, validity).",
            "inputs":      {"phone": {"type": "str", "required": True}},
            "outputs":     {"result": {"type": "dict"}},
            "permissions": [],
            "cli_commands": [
                "phone --number <number>",
                "phone --number <number> --deep",
            ],
        }

    def run(self, input_data: dict = None) -> dict:
        input_data = input_data or {}
        if "phone" not in input_data:
            return {"result": None, "error": "Phone number not provided."}
        try:
            data = self.plugin.lookup(input_data["phone"])
            return {"result": data}
        except TimeoutError:
            logger.warning(f"PhoneIntel: timeout querying {input_data['phone']}")
            return {"result": None, "error": "Timeout contacting the lookup service."}
        except ConnectionError as e:
            logger.error(f"PhoneIntel: network error: {e}")
            return {"result": None, "error": "No connection to the lookup service."}
        except Exception as e:
            logger.exception(f"PhoneIntel: unexpected error: {e}")
            return {"result": None, "error": str(e)}


def register_chunk(engine, subparsers) -> None:
    chunk = PhoneIntelChunk(ConfigManager())
    engine.register(chunk)

    p = subparsers.add_parser("phone", help="Analyze phone number")
    p.add_argument("--number", type=str, required=True)
    p.add_argument("--deep",   action="store_true")

    engine.register_cli_handler("phone", _make_phone_callback(chunk))


def _make_phone_callback(chunk: PhoneIntelChunk):

    def _callback(args) -> None:
        console   = make_console()
        deep_mode = getattr(args, "deep", False)

        section = "[ deep scan ]" if deep_mode else "[ lookup ]"
        console.print(
            f"\n[myfi.dim]── PHONE INTEL {'─' * 22} {section}[/myfi.dim]"
        )

        if deep_mode:
            console.print(
                "[myfi.amber][ WARN ] This mode searches public sources[/myfi.amber]\n"
                "[myfi.dim]         (social networks, directories, forums)[/myfi.dim]\n"
                "[myfi.dim]         by the provided number. The search is aggressive.[/myfi.dim]"
            )
            console.print()
            if not Confirm.ask("[myfi.amber]Continue with deep scan?[/myfi.amber]"):
                console.print("[myfi.dim]Deep scan cancelled.[/myfi.dim]")
                return

        deep_data = None
        if deep_mode:
            with console.status("[myfi.red]Running deep scan...[/myfi.red]", spinner="dots"):
                try:
                    deep_data = chunk.plugin.deep_search(args.number)
                except Exception as e:
                    console.print(f"[myfi.red][ FAIL ] Deep scan failed: {e}[/myfi.red]")
                    return

        with console.status(
            f"[myfi.cyan]Analyzing {args.number}...[/myfi.cyan]", spinner="dots"
        ):
            result = chunk.run({"phone": args.number})

        if error := result.get("error"):
            console.print(f"[myfi.red][ FAIL ] {error}[/myfi.red]")
            return

        data = result.get("result")
        if data is None:
            console.print(
                f"[myfi.red][ FAIL ] Invalid or unrecognized number: {args.number}[/myfi.red]"
            )
            return

        valid_str = (
            "[myfi.green]yes[/myfi.green]"
            if data.get("valid")
            else "[myfi.red]no[/myfi.red]"
        )

        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column(style="myfi.dim",  width=16)
        table.add_column(style="myfi.body")

        for label, value in [
            ("number",       data.get("formatted_international", args.number)),
            ("country",      data.get("location",    "unknown")),
            ("carrier",      data.get("carrier",     "unknown")),
            ("timezone",     data.get("timezone",    "unknown")),
            ("type",         data.get("number_type", "unknown")),
            ("valid",        valid_str),
        ]:
            table.add_row(label, value)

        console.print(table)

        if deep_data is not None:
            console.print(
                f"\n[myfi.dim]── DEEP SCAN RESULTS {'─' * 30}[/myfi.dim]"
            )
            if not deep_data:
                console.print("[myfi.dim]No results found.[/myfi.dim]")
            else:
                errors = deep_data.pop("_errors", {})
                deep_data.pop("_warning", None)

                ds_table = Table(show_header=True, box=None, padding=(0, 2))
                ds_table.add_column("SOURCE",   style="myfi.cyan", width=22)
                ds_table.add_column("RESULT",   style="myfi.body")

                for source, value in deep_data.items():
                    ds_table.add_row(source, str(value))

                console.print(ds_table)

                if errors:
                    console.print(
                        f"\n[myfi.amber][ WARN ] {len(errors)} source(s) failed: "
                        f"{', '.join(errors.keys())}[/myfi.amber]"
                    )

            console.print(f"[myfi.dim]{'─' * 52}[/myfi.dim]")

        console.print()

    return _callback
