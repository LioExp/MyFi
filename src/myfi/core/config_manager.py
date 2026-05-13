# src/myfi/core/config_manager.py
from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ConfigManager:
    """Gestor centralizado de configuracao do MyFi."""

    DEFAULT_CONFIG: dict = {
        "interface":        None,
        "device_type":      None,
        "dependencies_ok":  False,
        "telegram_token":   None,
        "telegram_chat_id": None,
        "default_limit_mb": 200,
        "retention_days":   30,
    }

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir  = config_dir or Path.home() / ".myfi"
        self.config_file = self.config_dir / "config.json"
        self._config: dict | None = None
        self._ensure_dir()

    # ════════════════════════════════════════════════════════════
    # INTERNOS
    # ════════════════════════════════════════════════════════════

    def _ensure_dir(self) -> None:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Nao foi possivel criar {self.config_dir}: {e}")
            raise

    def _load_file(self) -> dict:
        """Le o ficheiro e devolve o dict raw. Nunca levanta excepção."""
        if not self.config_file.exists():
            logger.info(f"Config nao encontrada em {self.config_file}. Usando defaults.")
            return {}
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"Erro ao ler config: {e}. Usando defaults.")
            return {}

    # ════════════════════════════════════════════════════════════
    # API PÚBLICA
    # ════════════════════════════════════════════════════════════

    def load(self) -> dict:
        """
        Carrega a configuracao (com cache).
        Valores do ficheiro têm prioridade sobre DEFAULT_CONFIG.
        """
        if self._config is None:
            data         = self._load_file()
            self._config = {**self.DEFAULT_CONFIG, **data}
            logger.debug(f"Config carregada de {self.config_file}")
        return self._config

    def save(self) -> None:
        """
        Persiste o estado actual no disco.
        Chamada explicitamente — nao automaticamente a cada set().
        """
        if self._config is None:
            self.load()
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self._config, f, indent=2, ensure_ascii=False)
            logger.info(f"Config guardada em {self.config_file}")
        except OSError as e:
            logger.error(f"Erro ao guardar config: {e}")
            raise

    def get(self, key: str, default=None):
        """Devolve um valor da configuracao."""
        return self.load().get(key, default)

    def set(self, key: str, value) -> None:
        """
        Define um valor em memoria.
        Nao escreve no disco — chama save() explicitamente quando terminares.
        """
        self.load()[key] = value

    def reload(self) -> dict:
        """Forca recarga do ficheiro, descartando o cache."""
        self._config = None
        return self.load()

    def reset(self) -> None:
        """
        Limpa a configuracao em memoria.
        Nao apaga o ficheiro — o proximo save() ira sobreescrever.
        """
        self._config = {**self.DEFAULT_CONFIG}
        logger.debug("Config resetada para defaults.")

    def is_configured(self) -> bool:
        """
        Verifica se a configuracao minima esta feita.

        - Todos os modos precisam de interface definida.
        - local_pc precisa adicionalmente de dependencies_ok=True.
        - hotspot e router precisam apenas de device_type definido.
        """
        device_type = self.get("device_type")
        has_iface   = bool(self.get("interface"))

        if not has_iface or not device_type:
            return False

        if device_type == "local_pc":
            return self.get("dependencies_ok", False)

        # hotspot e router — interface + device_type e suficiente
        return True
