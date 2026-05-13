# src/myfi/core/engine.py  — actualizar discover para carregar chunks externos
from __future__ import annotations

import importlib
import importlib.util
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List

from myfi.core.base_chunk import BaseChunk

logger = logging.getLogger(__name__)


class ChunkEngine:
    def __init__(self, config: Any = None) -> None:
        self.config       = config
        self._registry:   Dict[str, BaseChunk] = {}
        self._workflows:  Dict[str, List[str]] = {}
        self._cli_handlers: Dict[str, Any]     = {}

    def register_cli_handler(self, command: str, callback: Any) -> None:
        self._cli_handlers[command] = callback

    def get_cli_handler(self, command: str) -> Any:
        return self._cli_handlers.get(command)

    def register(self, chunk: BaseChunk) -> None:
        manifest = chunk.manifest()
        name     = manifest.get("name")
        if not name:
            raise ValueError("Chunk sem nome no manifesto.")
        self._registry[name] = chunk
        logger.info(f"Chunk registado: {name} v{manifest.get('version', '0.0.0')}")

    def is_registered(self, name: str) -> bool:
        return name in self._registry

    def enable(self, name: str) -> None:
        if name in self._registry:
            self._registry[name].enable()

    def disable(self, name: str) -> None:
        if name in self._registry:
            self._registry[name].disable()

    def define_workflow(self, name: str, steps: List[str]) -> None:
        for step in steps:
            if step not in self._registry:
                raise ValueError(f"Chunk '{step}' nao registado.")
        self._workflows[name] = steps
        logger.info(f"Workflow definido: {name} → {' → '.join(steps)}")

    def run_workflow(self, name: str, initial_input: Dict[str, Any] = None) -> Dict[str, Any]:
        if name not in self._workflows:
            raise ValueError(f"Workflow '{name}' nao encontrado.")
        data = initial_input or {}
        for step_name in self._workflows[name]:
            chunk = self._registry.get(step_name)
            if chunk is None:
                raise RuntimeError(f"Chunk '{step_name}' nao registado.")
            if not chunk.enabled:
                logger.warning(f"Chunk '{step_name}' desactivado — a saltar.")
                continue
            logger.debug(f"Executando: {step_name}")
            data = chunk.run(data)
        return data

    def load_external_chunk(
        self,
        path: Path,
        subparsers: Any = None,
    ) -> bool:
        """
        Carrega um chunk externo de um path em disco.
        Usado pelo ChunkManager apos instalacao.
        Devolve True se carregado com sucesso.
        """
        init_file = path / "__init__.py"
        if not init_file.exists():
            logger.error(f"load_external_chunk: __init__.py nao encontrado em {path}")
            return False

        module_name = f"myfi_ext_{path.name.lower()}"
        try:
            spec = importlib.util.spec_from_file_location(
                module_name, init_file,
                submodule_search_locations=[str(path)],
            )
            mod = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = mod
            spec.loader.exec_module(mod)

            if hasattr(mod, "register_chunk"):
                mod.register_chunk(self, subparsers)
                logger.info(f"Chunk externo carregado: {path.name}")
                return True
            else:
                logger.warning(f"load_external_chunk: register_chunk nao encontrado em {path.name}")
                return False
        except Exception as e:
            logger.error(f"load_external_chunk: falhou para '{path.name}': {e}")
            return False
