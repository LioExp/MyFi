# src/myfi/core/base_chunk.py
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseChunk(ABC):
    """
    Contrato base para todos os Chunks do MyFi.

    Metodos obrigatorios:
        manifest() → metadados do chunk
        run()      → logica principal
    Metodos opcionais (override conforme necessario):
        requirements()  → dependencias pip
        setup()         → executado uma vez na instalacao
        teardown()      → executado na remocao
        health_check()  → verifica se o chunk esta operacional
    """

    def __init__(self, config: Any = None) -> None:
        self.config  = config
        self.enabled = True

    # OBRIGATORIOS
    @staticmethod
    @abstractmethod
    def manifest() -> dict[str, Any]:
        """
        Metadados do chunk.

        Campos obrigatorios:
            name        str   — identificador unico
            version     str   — semver (ex: "1.0.0")
            description str   — descricao curta

        Campos opcionais:
            inputs       dict  — schema dos inputs esperados em run()
            outputs      dict  — schema dos outputs produzidos por run()
            permissions  list  — permissoes necessarias (ex: ["network:outbound"])
            cli_commands list  — comandos CLI expostos
            tags         list  — categorias (ex: ["network", "osint"])
            author       str   — autor do chunk
            myfi_min     str   — versao minima do MyFi necessaria
        """
        return {}

    @abstractmethod
    def run(self, input_data: dict[str, Any]) -> dict[str, Any]:
        """
        Logica principal do chunk.
        Recebe output do chunk anterior no workflow (ou {} se for o primeiro).
        Deve sempre devolver um dict — nunca levantar excepcao para o engine.
        """
        pass

    # OPCIONAIS — override conforme necessario
    @staticmethod
    def requirements() -> list[str]:
        """
        Dependencias pip necessarias para este chunk.
        Instaladas automaticamente por 'myfi chunk install'.
        Exemplo:
            return ["geoip2>=4.0.0", "requests>=2.28.0"]
        """
        return []

    @classmethod
    def setup(cls) -> None:
        """
        Executado UMA vez apos instalacao.
        Usado para: download de bases de dados, criacao de directorias,
        configuracao inicial, etc.

        Exemplo (GeoLocate):
            download GeoLite2-City.mmdb e GeoLite2-ASN.mmdb
        """
        pass

    @classmethod
    def teardown(cls) -> None:
        """
        Executado na remocao do chunk.
        Usado para: limpar ficheiros, bases de dados, configuracoes.
        Por defeito nao faz nada — chunks podem optar por manter os dados.
        """
        pass

    @classmethod
    def health_check(cls) -> tuple[bool, str]:
        """
        Verifica se o chunk esta operacional.
        Chamado por 'myfi chunk list' e antes de run() em workflows.

        Devolve:
            (True,  "ok")                    — tudo bem
            (False, "GeoLite2 not found")    — problema especifico

        Exemplo (GeoLocate):
            if not Path("~/.myfi/data/GeoLite2-City.mmdb").exists():
                return False, "GeoLite2 database not found. Run: myfi chunk setup GeoLocate"
            return True, "ok"
        """
        return True, "ok"


    # ESTADO
    def enable(self) -> None:
        self.enabled = True

    def disable(self) -> None:
        self.enabled = False

    def __repr__(self) -> str:
        m = self.manifest()
        return (
            f"<{self.__class__.__name__} "
            f"name={m.get('name', '?')} "
            f"version={m.get('version', '?')} "
            f"enabled={self.enabled}>"
        )
