import logging
import subprocess
import socket
import time
from datetime import datetime
from threading import Event
from myfi.core.config_manager import ConfigManager
from myfi.core.alerts import AlertManager
from myfi.db.database import Database

logger = logging.getLogger(__name__)

class MonitorCore:
    """Motor de monitorização de tráfego da rede."""

    def __init__(self, config: ConfigManager):
        self.config = config
        self.db = Database()
        self.alert_mgr = AlertManager(config)

        self.interface = config.get('interface', 'wlan0')
        self.my_ip = self._get_local_ip()
        self.my_mac = self._get_own_mac(self.my_ip)

        self.running = False
        self.stop_event = Event()

        # Carrega limites ativos da BD
        self.limits = self._load_limits()

    @staticmethod
    def _get_local_ip() -> str:
        """Obtém o IP local do dispositivo onde o MyFi corre."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 1))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    @staticmethod
    def _get_own_mac(ip: str) -> str:
        """Tenta obter o MAC do próprio dispositivo a partir da tabela ARP."""
        try:
            resultado = subprocess.run(['arp', '-a'], capture_output=True, text=True)
            for linha in resultado.stdout.splitlines():
                partes = linha.split()
                if len(partes) >= 4 and partes[1].strip('()') == ip:
                    return partes[3]
        except Exception:
            pass
        return "Unknown"

    def _load_limits(self) -> dict:
        """Carrega os limites ativos da BD e retorna um dicionário {mac: {type, max_bytes}}."""
        limits_list = self.db.get_limits()
        limits = {}
        for limit in limits_list:
            limits[limit['mac']] = {
                'type': limit['limit_type'],
                'max_bytes': limit['bytes_max']
            }
        return limits

    def _capture_traffic(self, interface: str, duration: int = 10) -> tuple[int, int]:
        """
        Captura tráfego (bytes recebidos e enviados) para o IP do próprio dispositivo.
        Retorna (bytes_recv, bytes_sent).
        """
        cmd_recv = [
            'sudo', 'tshark', '-i', interface,
            '-a', f'duration:{duration}',
            '-T', 'fields', '-e', 'frame.len',
            '-Y', f'ip.dst == {self.my_ip}'
        ]
        cmd_sent = [
            'sudo', 'tshark', '-i', interface,
            '-a', f'duration:{duration}',
            '-T', 'fields', '-e', 'frame.len',
            '-Y', f'ip.src == {self.my_ip}'
        ]

        try:
            res_recv = subprocess.run(cmd_recv, capture_output=True, text=True, timeout=duration+5)
            res_sent = subprocess.run(cmd_sent, capture_output=True, text=True, timeout=duration+5)
        except subprocess.TimeoutExpired:
            logger.warning("Captura de tráfego excedeu o tempo limite.")
            return 0, 0

        bytes_recv = sum(int(x) for x in res_recv.stdout.split() if x.isdigit())
        bytes_sent = sum(int(x) for x in res_sent.stdout.split() if x.isdigit())
        return bytes_recv, bytes_sent

    def _check_limits(self, mac: str, total_bytes: int) -> bool:
        """
        Verifica se o total_bytes excede algum limite ativo para o MAC.
        Retorna True se um alerta crítico (100%) foi enviado, False caso contrário.
        """
        if mac not in self.limits:
            return False

        limit_info = self.limits[mac]
        max_bytes = limit_info['max_bytes']
        if max_bytes <= 0:
            return False

        usage_mb = total_bytes / (1024 * 1024)
        limit_mb = max_bytes / (1024 * 1024)
        ratio = total_bytes / max_bytes
        name = self.db.get_device(mac)
        name = name['hostname'] if name else mac

        # 80% warning
        if 0.8 <= ratio < 1.0:
            self.alert_mgr.send_and_log(
                mac,
                'warning',
                self.alert_mgr.send_limit_alert(
                    mac, name, usage_mb, limit_mb, is_critical=False
                )
            )
            return False
        # 100% critical
        elif ratio >= 1.0:
            self.alert_mgr.send_and_log(
                mac,
                'critical',
                self.alert_mgr.send_limit_alert(
                    mac, name, usage_mb, limit_mb, is_critical=True
                )
            )
            return True
        return False

    def start(self, live_mode: bool = False, interval: int = 300):
        """
        Inicia a monitorização contínua.
        - live_mode=True: captura a cada 1 segundo.
        - intervalo padrão: 5 minutos (300s) para Low Power.
        """
        self.running = True
        logger.info(f"Monitor iniciado (live={live_mode}, interval={interval}s)")

        while self.running and not self.stop_event.is_set():
            cycle_start = time.time()

            try:
                recv, sent = self._capture_traffic(self.interface, duration=min(10, interval))
                total = recv + sent

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                hostname = socket.getfqdn(self.my_ip)

                # 1. Garantir que o dispositivo está registado (resolve FOREIGN KEY)
                self.db.save_device(
                    self.my_mac,
                    hostname if hostname else self.my_ip,
                    self.my_ip,
                    self.interface
                )

                # 2. Persistir tráfego (agora o MAC já existe na tabela devices)
                self.db.save_traffic(self.my_mac, sent, recv, now)

                # 3. Verificar limites
                self._check_limits(self.my_mac, total)

            except Exception as e:
                logger.error(f"Erro no ciclo de monitorização: {e}")

            # Aguardar o próximo ciclo (considerando o tempo gasto)
            elapsed = time.time() - cycle_start
            wait = max(0, interval - elapsed) if not live_mode else 1
            self.stop_event.wait(wait)

        self.db.close()
        logger.info("Monitor parado.")

    def stop(self):
        """Para a monitorização de forma controlada."""
        self.running = False
        self.stop_event.set()