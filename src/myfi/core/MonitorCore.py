# src/myfi/core/MonitorCore.py
from __future__ import annotations

import logging
import re
import socket
import subprocess
import time
from datetime import datetime
from threading import Event
from typing import Callable

from myfi.core.alerts import AlertManager
from myfi.core.config_manager import ConfigManager
from myfi.db.database import Database

logger = logging.getLogger(__name__)


class MonitorCore:
    """Motor de monitorizacao de trafego da rede."""

    def __init__(self, config: ConfigManager) -> None:
        self.config    = config
        self.interface = config.get("interface", "wlan0")
        self.my_ip     = self._get_ip(self.interface)
        self.my_mac    = self._get_mac(self.interface)

        self.alert_mgr = AlertManager(config)

        # estado de execucao
        self.running    = False
        self._stop      = Event()

        # acumuladores de sessao
        self.session_recv = 0
        self.session_sent = 0

        # alertas por dia — resetados quando o dia muda
        self._alert_day: str         = ""
        self._warned:    set[str]    = set()
        self._critical:  set[str]    = set()

        # totais diarios por MAC
        self._daily: dict[str, int]  = {}

    # ════════════════════════════════════════════════════════════
    # SISTEMA — IP / MAC
    # ════════════════════════════════════════════════════════════

    @staticmethod
    def _get_ip(iface: str) -> str:
        try:
            result = subprocess.run(
                ["ip", "-4", "-o", "addr", "show", iface],
                capture_output=True, text=True, check=True,
            )
            m = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", result.stdout)
            if m:
                return m.group(1)
        except Exception as e:
            logger.warning(f"Nao foi possivel obter IP de {iface}: {e}")
        return "127.0.0.1"

    @staticmethod
    def _get_mac(iface: str) -> str:
        try:
            return (
                open(f"/sys/class/net/{iface}/address").read().strip()
            )
        except Exception as e:
            logger.warning(f"Nao foi possivel ler MAC de {iface}: {e}")
        return "unknown"

    # ════════════════════════════════════════════════════════════
    # VERIFICAÇÕES PRÉ-ARRANQUE
    # ════════════════════════════════════════════════════════════

    def _tshark_ok(self) -> bool:
        """Verifica se tshark existe e tem permissoes para capturar."""
        try:
            result = subprocess.run(
                ["tshark", "-i", "lo", "-c", "1", "-a", "duration:1"],
                capture_output=True, text=True, timeout=5,
            )
            # returncode 0 = ok; 1 pode ser "no packets" mas permissoes ok
            return result.returncode in (0, 1)
        except FileNotFoundError:
            logger.error("tshark nao encontrado. Instala com: sudo apt install tshark")
            return False
        except subprocess.TimeoutExpired:
            # timeout na loopback e improvavel mas nao fatal
            return True
        except Exception as e:
            logger.error(f"_tshark_ok: {e}")
            return False

    # ════════════════════════════════════════════════════════════
    # CAPTURA
    # ════════════════════════════════════════════════════════════

    def _capture(self, duration: int, tight: bool = False) -> tuple[int, int]:
        """
        Captura trafego com tshark e devolve (bytes_recv, bytes_sent).
        Usa -Y para filtro BPF correcto.
        """
        cmd = [
            "tshark", "-i", self.interface,
            "-a", f"duration:{duration}",
            "-T", "fields",
            "-e", "frame.len",
            "-e", "ip.dst",
            "-e", "ip.src",
            "-Y", f"ip host {self.my_ip}",      # -Y é o filtro de display correcto
        ]
        timeout = duration + (2 if tight else 5)

        try:
            res = subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
            )
        except FileNotFoundError:
            logger.error("tshark nao encontrado durante captura.")
            return 0, 0
        except subprocess.TimeoutExpired:
            logger.warning(f"Captura excedeu {timeout}s — dados parciais descartados.")
            return 0, 0
        except Exception as e:
            logger.error(f"_capture: erro inesperado: {e}")
            return 0, 0

        recv = sent = 0
        for line in res.stdout.strip().splitlines():
            parts = line.split()
            if len(parts) < 3:
                continue
            try:
                length = int(parts[0])
                dst, src = parts[1], parts[2]
                if dst == self.my_ip:
                    recv += length
                if src == self.my_ip:
                    sent += length
            except (ValueError, IndexError):
                continue

        return recv, sent

    # ════════════════════════════════════════════════════════════
    # LIMITES E ALERTAS
    # ════════════════════════════════════════════════════════════

    def _reset_alerts_if_new_day(self) -> None:
        today = datetime.now().strftime("%Y-%m-%d")
        if today != self._alert_day:
            self._alert_day = today
            self._warned.clear()
            self._critical.clear()
            self._daily.clear()
            logger.debug("Alertas e totais diarios resetados para o novo dia.")

    def _check_limits(self, db: Database, mac: str, total_bytes: int) -> None:
        """
        Verifica limites e envia alertas se necessario.
        Separado do loop principal para manter responsabilidade unica.
        """
        limits = db.get_limits(mac)
        if not limits:
            return

        max_bytes = limits[0]["bytes_max"]
        if max_bytes <= 0:
            return

        ratio = total_bytes / max_bytes
        if ratio < 0.8:
            return

        device   = db.get_device(mac)
        name     = device["hostname"] if device else mac
        usage_mb = total_bytes  / (1024 * 1024)
        limit_mb = max_bytes    / (1024 * 1024)

        if ratio >= 1.0 and mac not in self._critical:
            try:
                self.alert_mgr.send_limit_alert(
                    mac, name, usage_mb, limit_mb, is_critical=True
                )
                self._critical.add(mac)
                logger.info(f"Alerta CRITICO enviado para {mac} ({usage_mb:.0f}/{limit_mb:.0f} MB)")
            except Exception as e:
                logger.error(f"Falha ao enviar alerta critico para {mac}: {e}")

        elif 0.8 <= ratio < 1.0 and mac not in self._warned:
            try:
                self.alert_mgr.send_limit_alert(
                    mac, name, usage_mb, limit_mb, is_critical=False
                )
                self._warned.add(mac)
                logger.info(f"Alerta AVISO enviado para {mac} ({usage_mb:.0f}/{limit_mb:.0f} MB)")
            except Exception as e:
                logger.error(f"Falha ao enviar alerta de aviso para {mac}: {e}")

    # ════════════════════════════════════════════════════════════
    # LOOP PRINCIPAL
    # ════════════════════════════════════════════════════════════

    def start(
        self,
        live_mode: bool = False,
        interval: int = 300,
        status_callback: Callable | None = None,
    ) -> None:
        if not self._tshark_ok():
            raise PermissionError(
                "tshark nao tem permissoes para capturar trafego.\n"
                "Executa: sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/tshark\n"
                "Ou adiciona o utilizador ao grupo 'wireshark' e reinicia a sessao."
            )

        self._stop.clear()
        self.running      = True
        self.session_recv = 0
        self.session_sent = 0

        capture_duration = max(2, min(10, interval)) if live_mode else min(10, interval)

        logger.info(
            f"Monitor iniciado — iface={self.interface} ip={self.my_ip} "
            f"mac={self.my_mac} live={live_mode} interval={interval}s "
            f"capture={capture_duration}s"
        )

        db = Database()
        try:
            self._reset_alerts_if_new_day()
            today   = datetime.now().strftime("%Y-%m-%d")
            summary = db.get_traffic_summary(self.my_mac, since=f"{today} 00:00:00")
            self._daily[self.my_mac] = summary["bytes_sent"] + summary["bytes_recv"]

            while self.running and not self._stop.is_set():
                self._reset_alerts_if_new_day()
                cycle_start = time.time()

                try:
                    recv, sent = self._capture(capture_duration, tight=live_mode)
                    now        = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    try:
                        hostname = socket.gethostbyaddr(self.my_ip)[0]
                    except (socket.herror, socket.gaierror):
                        hostname = self.my_ip

                    db.save_device(self.my_mac, hostname, self.my_ip, self.interface)
                    db.save_traffic(self.my_mac, sent, recv, now)

                    self._daily[self.my_mac] = (
                        self._daily.get(self.my_mac, 0) + recv + sent
                    )
                    self.session_recv += recv
                    self.session_sent += sent

                    self._check_limits(db, self.my_mac, self._daily[self.my_mac])

                    if status_callback:
                        status_callback(recv, sent, self.session_recv, self.session_sent)

                except Exception as e:
                    logger.error(f"Erro no ciclo de monitorizacao: {e}")

                elapsed = time.time() - cycle_start
                # KeyboardInterrupt apanhado aqui — nao propaga
                try:
                    self._stop.wait(max(0.0, interval - elapsed))
                except KeyboardInterrupt:
                    logger.info("Monitor interrompido pelo utilizador.")
                    break

        except KeyboardInterrupt:
            logger.info("Monitor interrompido pelo utilizador.")
        finally:
            db.close()
            self.running = False
            self._stop.set()
            logger.info("Monitor parado.")
