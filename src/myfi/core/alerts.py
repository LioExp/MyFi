import logging
import requests
from myfi.core.config_manager import ConfigManager

logger = logging.getLogger(__name__)

class AlertManager:
    """Gerencia o envio de alertas via Telegram."""

    def __init__(self, config: ConfigManager):
        """
        Inicializa o gerenciador de alertas.

        Args:
            config: Instância do ConfigManager com as configurações carregadas.
        """
        self.config = config
        self.token = config.get("telegram_token")
        self.chat_id = config.get("telegram_chat_id")
        self.enabled = bool(self.token and self.chat_id)

        if not self.enabled:
            logger.warning("Alertas Telegram desativados: token ou chat_id não configurados.")

    def send(self, message: str, parse_mode: str = "HTML") -> bool:
        """
        Envia uma mensagem via Telegram.

        Args:
            message: Texto da mensagem (pode conter tags HTML se parse_mode='HTML').
            parse_mode: Modo de parsing ('HTML' ou 'MarkdownV2').

        Returns:
            True se enviado com sucesso, False caso contrário.
        """
        if not self.enabled:
            logger.debug("Tentativa de envio com alertas desativados.")
            return False

        url = f"https://api.telegram.org/bot{self.token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            "parse_mode": parse_mode
        }

        try:
            response = requests.post(url, data=payload, timeout=10)
            response.raise_for_status()
            result = response.json()

            if result.get("ok"):
                logger.info(f"Alerta enviado com sucesso: {message[:50]}...")
                # TODO: Persistir no banco de dados (tabela alerts_log)
                return True
            else:
                logger.error(f"Erro da API Telegram: {result.get('description')}")
                return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Falha na conexão ao enviar alerta: {e}")
            # TODO: Adicionar à fila de retry (pending_alerts)
            return False
        except Exception as e:
            logger.exception(f"Erro inesperado ao enviar alerta: {e}")
            return False

    def send_limit_alert(self, mac: str, name: str, usage_mb: float, limit_mb: float, is_critical: bool = False) -> bool:
        """
        Envia um alerta de limite de consumo para um dispositivo.

        Args:
            mac: Endereço MAC do dispositivo.
            name: Nome do dispositivo.
            usage_mb: Consumo atual em MB.
            limit_mb: Limite configurado em MB.
            is_critical: Se True, é um alerta crítico (100%), caso contrário é aviso (80%).

        Returns:
            True se enviado com sucesso.
        """
        percentage = (usage_mb / limit_mb) * 100 if limit_mb > 0 else 0

        if is_critical:
            title = "🚨 LIMITE EXCEDIDO"
            body = (
                f"<b>Dispositivo:</b> {name} ({mac})\n"
                f"<b>Consumo:</b> {usage_mb:.1f} MB / {limit_mb:.0f} MB ({percentage:.0f}%)\n"
                f"<b>Ação:</b> O acesso foi bloqueado automaticamente."
            )
        else:
            title = "⚠️ AVISO DE CONSUMO"
            body = (
                f"<b>Dispositivo:</b> {name} ({mac})\n"
                f"<b>Consumo:</b> {usage_mb:.1f} MB / {limit_mb:.0f} MB ({percentage:.0f}%)\n"
                f"<b>Nota:</b> Atingiu 80% do limite diário."
            )

        message = f"{title}\n\n{body}"
        return self.send(message)
    # Dentro da classe AlertManager em src/myfi/core/alerts.py:

    def send_and_log(self, mac: str, alert_type: str, message: str):
        """Envia o alerta e regista no histórico da BD."""
        success = self.send(message)
        try:
            from myfi.db.database import Database
            db = Database()
            db.log_alert(mac, alert_type, message, success=success)
            if not success:
                db.add_pending_alert(mac, alert_type, message)
            db.close()
        except Exception as e:
            logger.error(f"Falha ao persistir alerta: {e}")
        return success
