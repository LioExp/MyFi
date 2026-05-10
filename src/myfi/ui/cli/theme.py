from rich.theme import Theme
from rich.console import Console

MYFI_THEME = Theme({
    "myfi.cyan":  "color(51)",
    "myfi.green": "color(48)",
    "myfi.amber": "color(215)",
    "myfi.blue":  "color(69)",
    "myfi.red":   "color(167)",
    "myfi.dim":   "color(240)",
    "myfi.body":  "color(151)",
})

def make_console() -> Console:
    """Instância de Console com a paleta MyFi. Usar em todos os módulos."""
    return Console(theme=MYFI_THEME)
