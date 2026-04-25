import subprocess
import socket
import logging
from datetime import datetime
from myfi.core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class Scanner:
    """Descobre dispositivos na rede local via ARP."""

    def __init__(self, config: ConfigManager = None):
        """
        Inicializa o scanner.

        Args:
            config: Instância do ConfigManager. Se None, carrega a configuração padrão.
        """
        if config is None:
            config = ConfigManager()
        self.config = config
        self.interface = config.get('interface', 'wlan0')  # interface padrão se não configurada

    @staticmethod
    def _reverse_dns(ip_address: str) -> str:
        """Tenta resolver o hostname reverso do IP."""
        try:
            hostname, _, _ = socket.gethostbyaddr(ip_address)
            return hostname
        except socket.herror:
            return "Unknown"

    def scan(self) -> list[dict]:
        """
        Executa o scan ARP e retorna uma lista de dispositivos encontrados.

        Returns:
            Lista de dicionários com chaves: 'hostname', 'ip', 'mac', 'interface'.
        """
        logger.info("Iniciando scan ARP na rede local.")
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            resultado = subprocess.run(
                ['arp', '-a'],
                capture_output=True,
                text=True,
                check=True
            )
        except subprocess.CalledProcessError as e:
            logger.error(f"Falha ao executar arp -a: {e}")
            raise RuntimeError("Comando ARP falhou") from e

        dispositivos = []
        for linha in resultado.stdout.splitlines():
            if not linha.strip():
                continue
            partes = linha.split()
            try:
                nome = partes[0]
                ip = partes[1].strip('()')
                mac = partes[3]
                interface = partes[6] if len(partes) > 6 else "N/A"
                hostname = self._reverse_dns(ip)

                dispositivos.append({
                    'hostname': hostname,
                    'ip': ip,
                    'mac': mac,
                    'interface': interface
                })
            except IndexError:
                logger.debug(f"Linha ignorada do ARP (formato inesperado): {linha}")

        logger.info(f"Scan concluído. {len(dispositivos)} dispositivo(s) encontrado(s).")
        return dispositivos

    def save_to_db(self, dispositivos: list[dict]):
        """
        Salva os dispositivos encontrados na base de dados (opcional, chamado pela CLI).
        Requer o módulo db.database.
        """
        try:
            from myfi.db.database import save_to_db
            for d in dispositivos:
                save_to_db(d['mac'], d['hostname'], d['ip'], 0, 0)  # bytes a 0 no scan
        except ImportError:
            logger.warning("Módulo de base de dados não disponível. Dispositivos não foram persistidos.")
        except Exception as e:
            logger.error(f"Erro ao salvar dispositivos na BD: {e}")