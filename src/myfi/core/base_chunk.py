from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseChunk(ABC):

    def __init__(self, config: Any = None):
        self.config = config
        self.enabled = True

    @staticmethod
    @abstractmethod
    def manifest() -> Dict[str, Any]:
        #Retorna os metadados do Chunk.Deve incluir: name, version, description, inputs, outputs, permissions.
        
        return {}

    @abstractmethod
    def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        pass

    def enable(self):
        self.enabled = True

    def disable(self):
        self.enabled = False
