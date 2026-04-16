import sys
import argparse
from core.config_manager import is_configured
from ui.cli.setup_wizard import wizard
from core.Scanner import main as scan_main 

def main():
    parser = argparse.ArgumentParser(description="MyFi - Monitor de Rede Inteligente")
    parser.add_argument("command", choices=["setup", "scan", "monitor"], help="Comando a executar")
    args = parser.parse_args()

    if args.command == "setup":
        wizard()
    elif args.command == "scan":
        if not is_configured():
            print("MyFi não configurado. Execute 'myfi setup' primeiro.")
            sys.exit(1)
        scan_main()
    # ... outros comandos
if __name__ == "__main__":
    main()