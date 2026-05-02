import logging
from typing import Dict, Any, List
from myfi.core.base_chunk import BaseChunk

logger = logging.getLogger(__name__)

class ChunkEngine:

    def __init__(self, config: Any = None):
        self.config = config
        # Dicionário de Chunks registados: nome -> instância
        self._registry: Dict[str, BaseChunk] = {}
        # Workflows: nome -> lista de nomes de Chunks
        self._workflows: Dict[str, List[str]] = {}

    def register(self, chunk: BaseChunk):
        """Regista um Chunk no motor."""
        manifest = chunk.manifest()
        name = manifest.get("name")
        if not name:
            raise ValueError("O Chunk não tem um nome definido no manifesto.")
        self._registry[name] = chunk
        logger.info(f"Chunk registado: {name} v{manifest.get('version', '0.0.0')}")

    def is_registered(self, chunk_name: str) -> bool:
        """Verifica se um Chunk está registado."""
        return chunk_name in self._registry

    def enable(self, chunk_name: str):
        """Ativa um Chunk registado."""
        if chunk_name in self._registry:
            self._registry[chunk_name].enable()

    def disable(self, chunk_name: str):
        """Desativa um Chunk registado."""
        if chunk_name in self._registry:
            self._registry[chunk_name].disable()

    def define_workflow(self, name: str, steps: List[str]):
        """Define um workflow como uma sequência de nomes de Chunks."""
        for step in steps:
            if step not in self._registry:
                raise ValueError(f"Chunk '{step}' não está registado.")
        self._workflows[name] = steps
        logger.info(f"Workflow definido: {name} -> {' -> '.join(steps)}")

    def run_workflow(self, name: str, initial_input: Dict[str, Any] = None) -> Dict[str, Any]:

        if name not in self._workflows:
            raise ValueError(f"Workflow '{name}' não encontrado.")
        steps = self._workflows[name]
        data = initial_input or {}
        for step_name in steps:
            chunk = self._registry.get(step_name)
            if chunk is None:
                raise RuntimeError(f"Chunk '{step_name}' não está registado.")
            if not chunk.enabled:
                logger.warning(f"Chunk '{step_name}' está desativado. A saltar.")
                continue
            logger.debug(f"Executando Chunk: {step_name}")
            data = chunk.run(data)
        return data
