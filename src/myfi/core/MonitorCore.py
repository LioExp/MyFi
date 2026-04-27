import logging
import subprocess
import socket
import time
import re
from datetime import datetime, date
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
        self.my_ip = self._get_ip_from_interface(self.interface)
        self.my_mac = self._get_mac_from_interface(self.interface) 

        self.running = False
        self.stop_event = Event()

        self.limits = self._load_limits()
        self.daily_totals = {}
        self.alerts_sent_today = {'warning': set(), 'critical': set()}

        self.session_recv = 0
        self.session_sent = 0

    @staticmethod
    def _get_ip_from_interface(interface: str) -> str:
        try:
            cmd = ['ip', '-4', '-o', 'addr', 'show', interface]
            resultado = subprocess.run(cmd, capture_output=True, text=True, check=True)
            match = re.search(r'inet\s+(\d+\.\d+\.\d+\.\d+)', resultado.stdout)
            if match:
                return match.group(1)
        except Exception as e:
            logger.warning(f"Não foi possível obter IP da interface {interface}: {e}")
        return '127.0.0.1'

    @staticmethod
    def _get_mac_from_interface(interface: str) -> str:
        """
        Lê o endereço MAC diretamente do sistema de ficheiros.
        Retorna o MAC ou 'Unknown' em caso de erro.
        """
        try:
            mac_path = f'/sys/class/net/{interface}/address'
            with open(mac_path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            logger.warning(f"Não foi possível ler o MAC da interface {interface}: {e}")
        return "Unknown"

    def _load_limits(self) -> dict:
        limits_list = self.db.get_limits()
        limits = {}
        for limit in limits_list:
            limits[limit['mac']] = {
                'type': limit['limit_type'],
                'max_bytes': limit['bytes_max']
            }
        return limits

    def _check_tshark_permissions(self) -> bool:
        try:
            test_cmd = ['tshark', '-i', 'lo', '-c', '1', '-a', 'duration:1']
            subprocess.run(test_cmd, capture_output=True, text=True, timeout=5, check=True)
            return True
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _capture_traffic(self, interface: str, duration: int = 10, tight_timeout: bool = False) -> tuple[int, int]:
        """
        Captura tráfego usando um único comando tshark com filtro 'ip host'.
        Retorna (bytes_recv, bytes_sent).
        """
        filter_expr = f'ip host {self.my_ip}'
        cmd = [
            'tshark', '-i', interface,
            '-a', f'duration:{duration}',
            '-T', 'fields', '-e', 'frame.len', '-e', 'ip.dst', '-e', 'ip.src'
        ]
        cmd.append(filter_expr)

        timeout = duration + (2 if tight_timeout else 4)
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            logger.warning("Captura de tráfego excedeu o tempo limite.")
            return 0, 0

        bytes_recv = 0
        bytes_sent = 0
        for line in res.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) >= 3:
                try:
                    length = int(parts[0])
                    dst = parts[1]
                    src = parts[2]
                    if dst == self.my_ip:
                        bytes_recv += length
                    if src == self.my_ip:
                        bytes_sent += length
                except (ValueError, IndexError):
                    continue
        return bytes_recv, bytes_sent

    def _check_limits(self, mac: str, total_bytes: int) -> bool:
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
        if ratio >= 0.8 and mac not in self.alerts_sent_today['warning']:
            self.alert_mgr.send_and_log(mac, 'warning',
                self.alert_mgr.send_limit_alert(mac, name, usage_mb, limit_mb, is_critical=False))
            self.alerts_sent_today['warning'].add(mac)
            return False
        elif ratio >= 1.0 and mac not in self.alerts_sent_today['critical']:
            self.alert_mgr.send_and_log(mac, 'critical',
                self.alert_mgr.send_limit_alert(mac, name, usage_mb, limit_mb, is_critical=True))
            self.alerts_sent_today['critical'].add(mac)
            return True
        return False

    def start(self, live_mode: bool = False, interval: int = 300, status_callback=None):
        if not self._check_tshark_permissions():
            error_msg = (
                "O tshark não tem permissões para capturar tráfego sem sudo.\n"
                "Execute: sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/tshark\n"
                "Ou adicione o seu utilizador ao grupo wireshark e reinicie a sessão."
            )
            logger.error(error_msg)
            raise PermissionError(error_msg)

        today_str = datetime.now().strftime("%Y-%m-%d")
        for mac in self.limits:
            summary = self.db.get_traffic_summary(mac, since=today_str + " 00:00:00")
            self.daily_totals[mac] = summary['bytes_sent'] + summary['bytes_recv']

        self.running = True
        capture_duration = max(2, min(10, interval)) if live_mode else min(10, interval)
        logger.info(f"Monitor iniciado (live={live_mode}, interval={interval}s, capture_duration={capture_duration}s) com IP {self.my_ip} e MAC {self.my_mac}")

        while self.running and not self.stop_event.is_set():
            cycle_start = time.time()
            try:
                recv, sent = self._capture_traffic(
                    self.interface, duration=capture_duration, tight_timeout=live_mode
                )
                total = recv + sent

                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                hostname = socket.getfqdn(self.my_ip)

                self.db.save_device(self.my_mac, hostname if hostname else self.my_ip, self.my_ip, self.interface)
                self.db.save_traffic(self.my_mac, sent, recv, now)

                self.daily_totals[self.my_mac] = self.daily_totals.get(self.my_mac, 0) + total
                accumulated = self.daily_totals[self.my_mac]

                self.session_recv += recv
                self.session_sent += sent

                self._check_limits(self.my_mac, accumulated)

                if status_callback:
                    status_callback(recv, sent, self.session_recv, self.session_sent)

            except Exception as e:
                logger.error(f"Erro no ciclo de monitorização: {e}")

            elapsed = time.time() - cycle_start
            wait = max(0, interval - elapsed)
            self.stop_event.wait(wait)

        self.db.close()
        logger.info("Monitor parado.")

    def stop(self):
        self.running = False
        self.stop_event.set()
