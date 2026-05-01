import logging
from myfi.core.base_chunk import BaseChunk
from myfi.core.alerts import AlertManager
from myfi.core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class TelegramNotifierChunk(BaseChunk):
    """Chunk que envia notificações via Telegram."""

    @staticmethod
    def manifest():
        return {
            "name": "TelegramNotifier",
            "version": "1.0.0",
            "description": "Envia notificações via Telegram usando o AlertManager.",
            "inputs": {
                "message": {"type": "str", "required": True},
                "parse_mode": {"type": "str", "required": False, "default": "HTML"}
            },
            "outputs": {
                "success": {"type": "bool"}
            },
            "permissions": ["network:outbound"]
        }

    def __init__(self, config: ConfigManager):
        super().__init__(config)
        self.alert_mgr = AlertManager(config)

    def run(self, input_data: dict) -> dict:
        message = input_data.get("message")
        if not message:
            return {"success": False, "error": "Mensagem não fornecida."}

        parse_mode = input_data.get("parse_mode", "HTML")
        success = self.alert_mgr.send(message, parse_mode=parse_mode)
        return {"success": success}