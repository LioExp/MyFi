# src/myfi/chunks/extras/telegram_notifier.py
from __future__ import annotations

import logging

from myfi.core.alerts import AlertManager
from myfi.core.base_chunk import BaseChunk
from myfi.core.config_manager import ConfigManager

logger = logging.getLogger(__name__)


class TelegramNotifierChunk(BaseChunk):
    """Sends notifications via Telegram using AlertManager."""

    def __init__(self, config: ConfigManager) -> None:
        super().__init__(config)
        self.alert_mgr = AlertManager(config)

    @staticmethod
    def manifest() -> dict:
        return {
            "name":        "TelegramNotifier",
            "version":     "1.0.0",
            "description": "Sends notifications via Telegram using AlertManager.",
            "inputs": {
                "message":    {"type": "str",  "required": True},
                "parse_mode": {"type": "str",  "required": False, "default": "HTML"},
            },
            "outputs": {
                "success": {"type": "bool"},
            },
            "permissions": ["network:outbound"],
        }

    def run(self, input_data: dict = None) -> dict:
        input_data = input_data or {}
        message    = input_data.get("message")

        if not message:
            return {"success": False, "error": "Message not provided."}

        parse_mode = input_data.get("parse_mode", "HTML")

        try:
            success = self.alert_mgr.send(message, parse_mode=parse_mode)
            return {"success": success}
        except TimeoutError:
            logger.warning("TelegramNotifier: timeout sending message.")
            return {"success": False, "error": "Timeout contacting Telegram."}
        except ConnectionError as e:
            logger.error(f"TelegramNotifier: no connection: {e}")
            return {"success": False, "error": "No connection to Telegram."}
        except Exception as e:
            logger.exception(f"TelegramNotifier: unexpected error: {e}")
            return {"success": False, "error": str(e)}
