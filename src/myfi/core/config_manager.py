import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class ConfigManager:
    """Gestor centralizado de configuração do MyFi."""

    DEFAULT_CONFIG = {
        "interface": None,
        "dependencies_ok": False,
        "telegram_token": None,
        "telegram_chat_id": None,
        "default_limit_mb": 200,          # limite diário padrão (se não definido por dispositivo)
        "retention_days": 30              # dias para retenção de logs (futuro)
    }

    def __init__(self, config_dir: Path = None):
        if config_dir is None:
            config_dir = Path.home() / ".myfi"
        self.config_dir = config_dir
        self.config_file = self.config_dir / "config.json"
        self._config = None
        self._ensure_dir()

    def _ensure_dir(self):
        """Cria o diretório de configuração se não existir."""
        try:
            self.config_dir.mkdir(exist_ok=True)
        except OSError as e:
            logger.error(f"Não foi possível criar o diretório de configuração {self.config_dir}: {e}")
            raise

    def load(self) -> dict:
        """Carrega a configuração do ficheiro e aplica valores padrão."""
        if self._config is not None:
            return self._config

        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                logger.debug(f"Configuração carregada de {self.config_file}")
            else:
                data = {}
                logger.info(f"Ficheiro de configuração não encontrado em {self.config_file}, usando valores padrão.")
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler ficheiro de configuração: {e}. Usando valores padrão.")
            data = {}

        # Mescla com valores padrão (os valores do ficheiro têm prioridade)
        merged = {**self.DEFAULT_CONFIG, **data}
        self._config = merged
        return self._config

    def save(self, config: dict = None):
        """Guarda a configuração atual no ficheiro."""
        if config is not None:
            self._config = config
        if self._config is None:
            self.load()
        try:
            self._ensure_dir()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"Configuração guardada em {self.config_file}")
        except OSError as e:
            logger.error(f"Erro ao guardar configuração: {e}")

    def get(self, key: str, default=None):
        """Retorna um valor de configuração específico."""
        config = self.load()
        return config.get(key, default)

    def set(self, key: str, value):
        """Define um valor de configuração e guarda."""
        config = self.load()
        config[key] = value
        self.save(config)

    def is_configured(self) -> bool:
        """Verifica se a configuração inicial mínima foi feita."""
        return bool(self.get("interface")) and self.get("dependencies_ok", False)

    def reload(self):
        """Força a recarga do ficheiro de configuração (descarta cache)."""
        self._config = None
        return self.load()