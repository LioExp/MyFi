import logging
import subprocess
from myfi.core.base_chunk import BaseChunk
from myfi.plugins.geoip_plugin import GeoIPPlugin
from myfi.core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

# Tráfego que nunca devia aparecer na tabela
_BOGUS_PREFIXES = ("0.", "127.", "169.254.", "192.168.", "10.", "172.16.", "224.", "239.", "255.")

class GeoLocateChunk(BaseChunk):
    """Chunk que geolocaliza os IPs externos contactados pela rede."""

    def __init__(self, config=None):
        super().__init__(config)
        self.geoip = GeoIPPlugin()
        self.config = config or ConfigManager()
        self.interface = self.config.get("interface", "wlan0")

    @staticmethod
    def manifest():
        return {
            "name": "GeoLocate",
            "version": "1.0.0",
            "description": "Geolocaliza IPs externos contactados pela rede.",
            "inputs": {},
            "outputs": {"connections": {"type": "list"}},
            "permissions": ["network:capture", "network:outbound"],
        }

    # ----------------------------------------------------------------
    # captura leve – 15 s por defeito, filtrando tráfego local
    # ----------------------------------------------------------------
    def _capture_ips(self, duration: int = 15) -> list:
        cmd = [
            "tshark", "-i", self.interface,
            "-a", f"duration:{duration}",
            "-T", "fields", "-e", "ip.dst",
            "-Y", "ip.dst",
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=duration + 10)
            ips = set()
            for line in result.stdout.splitlines():
                ip = line.strip()
                if not ip:
                    continue
                if ip.startswith(_BOGUS_PREFIXES):
                    continue
                ips.add(ip)
            return list(ips)
        except Exception as e:
            logger.error(f"Erro ao capturar IPs: {e}")
            return []

    # ----------------------------------------------------------------
    # run() – agora aceita duração configurável via input_data
    # ----------------------------------------------------------------
    def run(self, input_data=None):
        duration = 15
        if input_data and "duration" in input_data:
            duration = int(input_data["duration"])

        ips = self._capture_ips(duration=duration)

        if not ips:
            return {"connections": [], "message": "Nenhum tráfego externo capturado."}

        connections = []
        for ip in ips:
            geo_data = self.geoip.lookup(ip)
            if geo_data:
                connections.append(geo_data)
            else:
                connections.append({
                    "ip": ip,
                    "country": "Desconhecido",
                    "city": "Desconhecido",
                    "isp": "Desconhecido",
                    "maps_url": "#",
                })

        return {"connections": connections}