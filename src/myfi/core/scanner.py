from __future__ import annotations

import logging
import re
import socket
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from myfi.core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

_MAX_DNS_WORKERS = 8
_DNS_TIMEOUT     = 2    # segundos por query reversa


def _is_windows() -> bool:
    return sys.platform == "win32"


class Scanner:
    """Descobre dispositivos na rede local via ARP."""

    def __init__(self, config: ConfigManager | None = None) -> None:
        self.config    = config or ConfigManager()
        self.interface = self.config.get("interface", "wlan0")

    # ARP — Windows vs Linux
    def _arp_via_ip_neigh(self) -> list[dict]:
        """
        Usa 'ip neigh show' — disponivel apenas em Linux.
        """
        if _is_windows():
            return []

        try:
            result = subprocess.run(
                ["ip", "neigh", "show"],
                capture_output=True, text=True, check=True,
            )
        except FileNotFoundError:
            logger.debug("'ip neigh' nao disponivel — a tentar fallback arp -a.")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"ip neigh falhou: {e}")
            return []

        pattern = re.compile(
            r"^(?P<ip>\d+\.\d+\.\d+\.\d+)\s+"
            r"dev\s+(?P<iface>\S+)\s+"
            r"lladdr\s+(?P<mac>[\da-fA-F:]{17})\s+"
            r"(?P<state>\S+)"
        )
        devices = []
        for line in result.stdout.splitlines():
            m = pattern.match(line.strip())
            if not m:
                continue
            state = m.group("state").upper()
            if state in ("FAILED", "INCOMPLETE"):
                continue
            devices.append({
                "ip":        m.group("ip"),
                "mac":       m.group("mac").lower(),
                "interface": m.group("iface"),
                "hostname":  None,
            })
        return devices

    def _parse_arp_windows(self, output: str) -> list[dict]:
        """
        Parse do 'arp -a' no Windows.
        Formato:
          Interface: 192.168.1.6 --- 0x3
            Internet Address      Physical Address      Type
            192.168.1.1           e4-18-6b-aa-39-eb     dynamic
        """
        devices = []
        lines = output.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            # Detetar cabeçalho de interface
            iface_match = re.match(r"Interface:\s*(\d+\.\d+\.\d+\.\d+)\s*---", line)
            if iface_match:
                # Avançar para a linha de cabeçalho (Internet Address...)
                i += 1
                if i < len(lines) and "Internet Address" in lines[i]:
                    i += 1
                    # Processar entradas até linha vazia ou fim
                    while i < len(lines) and lines[i].strip():
                        entry = lines[i].strip()
                        parts = entry.split()
                        if len(parts) >= 2:
                            ip = parts[0]
                            mac = parts[1].replace("-", ":")  # Windows usa hífens
                            if re.match(r"[\da-fA-F:]{17}", mac):
                                devices.append({
                                    "ip":        ip,
                                    "mac":       mac.lower(),
                                    "interface": self.interface,
                                    "hostname":  None,
                                })
                        i += 1
                else:
                    i += 1
            else:
                i += 1
        return devices

    def _arp_via_arp_a(self) -> list[dict]:
        """
        Fallback: parse de 'arp -a'.
        Funciona tanto em Linux como em Windows.
        """
        try:
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True, text=True, check=True,
            )
        except FileNotFoundError:
            logger.error("Comando 'arp' nao disponivel.")
            return []
        except subprocess.CalledProcessError as e:
            logger.error(f"arp -a falhou: {e}")
            return []

        output = result.stdout

        # Se for Windows, usar parser especifico
        if _is_windows():
            devices = self._parse_arp_windows(output)
            if devices:
                logger.debug(f"ARP Windows: {len(devices)} dispositivo(s) encontrado(s).")
                return devices

        # Parser Linux
        pattern = re.compile(
            r"(?P<hostname>\S+)\s+\((?P<ip>\d+\.\d+\.\d+\.\d+)\)\s+"
            r"at\s+(?P<mac>[\da-fA-F:]{17})"
            r"(?:.*\s+on\s+(?P<iface>\S+))?"
        )
        devices = []
        for line in output.splitlines():
            m = pattern.search(line)
            if not m:
                logger.debug(f"Linha ARP ignorada: {line!r}")
                continue
            devices.append({
                "ip":        m.group("ip"),
                "mac":       m.group("mac").lower(),
                "interface": m.group("iface") or self.interface,
                "hostname":  None,
            })
        return devices

    # SCAPY (opcional, cross-platform)
    def _arp_via_scapy(self, timeout: int = 2) -> list[dict]:
        """
        Usa scapy para ARP scan — funciona em Windows e Linux.
        Requer privilégios de administrador/root.
        """
        try:
            from scapy.all import ARP, Ether, srp
        except ImportError:
            logger.debug("Scapy nao disponivel.")
            return []

        # Obter o IP local e a rede
        ip = self._get_local_ip()
        if ip == "127.0.0.1":
            return []
        network = ".".join(ip.split(".")[:3]) + ".0/24"

        try:
            logger.debug(f"Scapy ARP scan em {network}...")
            arp_request = ARP(pdst=network)
            broadcast = Ether(dst="ff:ff:ff:ff:ff:ff")
            packet = broadcast / arp_request
            answered, _ = srp(packet, timeout=timeout, verbose=False)

            devices = []
            for _, received in answered:
                devices.append({
                    "ip":        received.psrc,
                    "mac":       received.hwsrc.lower(),
                    "interface": self.interface,
                    "hostname":  None,
                })
            logger.debug(f"Scapy: {len(devices)} dispositivo(s) encontrado(s).")
            return devices
        except Exception as e:
            logger.error(f"Scapy scan falhou: {e}")
            return []

    def _get_local_ip(self) -> str:
        """Obtem o IP local (funciona em Windows e Linux)."""
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(1)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    # DNS REVERSO EM PARALELO
    @staticmethod
    def _resolve_hostname(ip: str) -> str | None:
        try:
            hostname, _, _ = socket.gethostbyaddr(ip)
            return hostname
        except (socket.herror, socket.gaierror):
            return None

    def _resolve_all(self, devices: list[dict]) -> list[dict]:
        if not devices:
            return devices
        with ThreadPoolExecutor(max_workers=_MAX_DNS_WORKERS) as pool:
            futures = {
                pool.submit(self._resolve_hostname, d["ip"]): i
                for i, d in enumerate(devices)
            }
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    devices[idx]["hostname"] = future.result()
                except Exception as e:
                    logger.debug(f"DNS reverso falhou para {devices[idx]['ip']}: {e}")
        return devices

    # SCAN PRINCIPAL
    def scan(self) -> list[dict]:
        logger.info(f"Iniciando scan ARP — interface: {self.interface} | SO: {'Windows' if _is_windows() else 'Linux'}")

        devices = []

        #Linux: tenta ip neigh
        if not _is_windows():
            devices = self._arp_via_ip_neigh()

        #Fallback: arp -a (funciona em ambos)
        if not devices:
            logger.debug("A usar arp -a.")
            devices = self._arp_via_arp_a()

        #Scapy (tenta como complemento, especialmente no Windows)
        if _is_windows() and not devices:
            logger.debug("ARP Windows sem resultados — a tentar Scapy.")
            devices = self._arp_via_scapy(timeout=3)

        if not devices:
            logger.warning("Scan concluido sem dispositivos encontrados.")
            return []

        devices = self._resolve_all(devices)
        logger.info(f"Scan concluido — {len(devices)} dispositivo(s) encontrado(s).")
        return devices

    # PERSISTÊNCIA
    def save_to_db(self, devices: list[dict]) -> None:
        from myfi.db.database import Database
        if not devices:
            return
        try:
            db = Database()
            for d in devices:
                db.save_device(
                    mac       = d["mac"],
                    hostname  = d["hostname"] or d["ip"],
                    ip        = d["ip"],
                    interface = d["interface"],
                )
            db.close()
            logger.debug(f"{len(devices)} dispositivo(s) persistido(s) na BD.")
        except Exception as e:
            logger.error(f"Erro ao persistir dispositivos na BD: {e}")
