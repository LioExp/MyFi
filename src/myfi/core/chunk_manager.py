# src/myfi/core/chunk_manager.py
from __future__ import annotations

import importlib
import importlib.util
import json
import logging
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

import requests

logger = logging.getLogger(__name__)

# CONSTANTES
_REGISTRY_URL  = (
    "https://raw.githubusercontent.com/myfi/registry/main/registry.json"
)
_CHUNKS_DIR    = Path.home() / ".myfi" / "chunks"
_CHUNKS_DB     = Path.home() / ".myfi" / "chunks.json"
_DATA_DIR      = Path.home() / ".myfi" / "data"
_REGISTRY_CACHE= Path.home() / ".myfi" / "registry_cache.json"


# CHUNK MANAGER
class ChunkManager:
    """
    Gere o ciclo de vida de chunks externos:
    instalacao, remocao, actualizacao e discovery.

    Chunks built-in (src/myfi/chunks/extras/) sao geridos pelo engine.
    Chunks externos ficam em ~/.myfi/chunks/ e sao geridos aqui.
    """

    def __init__(self) -> None:
        _CHUNKS_DIR.mkdir(parents=True, exist_ok=True)
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        self._db = self._load_db()

    # BASE DE DADOS LOCAL
    def _load_db(self) -> dict[str, Any]:
        """Carrega o registo local de chunks instalados."""
        if not _CHUNKS_DB.exists():
            return {"chunks": {}}
        try:
            return json.loads(_CHUNKS_DB.read_text())
        except (json.JSONDecodeError, OSError) as e:
            logger.error(f"ChunkManager: erro ao ler chunks.json: {e}")
            return {"chunks": {}}

    def _save_db(self) -> None:
        try:
            _CHUNKS_DB.write_text(
                json.dumps(self._db, indent=2, ensure_ascii=False)
            )
        except OSError as e:
            logger.error(f"ChunkManager: erro ao guardar chunks.json: {e}")

    # REGISTRY
    def fetch_registry(self, force: bool = False) -> dict[str, Any]:
        """
        Obtem o registry oficial.
        Usa cache local se disponivel e force=False.
        """
        if not force and _REGISTRY_CACHE.exists():
            try:
                cached = json.loads(_REGISTRY_CACHE.read_text())
                logger.debug("ChunkManager: registry carregado de cache.")
                return cached
            except Exception:
                pass

        try:
            resp = requests.get(_REGISTRY_URL, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            _REGISTRY_CACHE.write_text(json.dumps(data, indent=2))
            return data
        except requests.Timeout:
            raise TimeoutError("Registry: timeout ao obter registry.")
        except requests.ConnectionError:
            # tenta usar cache mesmo expirada
            if _REGISTRY_CACHE.exists():
                logger.warning("ChunkManager: sem ligacao — a usar cache.")
                return json.loads(_REGISTRY_CACHE.read_text())
            raise ConnectionError("Registry: sem ligacao e sem cache local.")
        except Exception as e:
            raise RuntimeError(f"Registry: erro ao obter registry: {e}")

    def search(self, query: str = "") -> list[dict[str, Any]]:
        """
        Pesquisa chunks no registry.
        Se query vazio, devolve todos.
        """
        registry = self.fetch_registry()
        chunks   = registry.get("chunks", {})
        results  = []

        query_lower = query.lower()
        for name, info in chunks.items():
            if not query_lower or (
                query_lower in name.lower()
                or query_lower in info.get("description", "").lower()
                or any(query_lower in t for t in info.get("tags", []))
            ):
                results.append({
                    "name":        name,
                    "version":     info.get("version", "?"),
                    "description": info.get("description", ""),
                    "author":      info.get("author", "?"),
                    "tags":        info.get("tags", []),
                    "verified":    info.get("verified", False),
                    "repo":        info.get("repo", ""),
                    "installed":   name in self._db["chunks"],
                })

        return sorted(results, key=lambda r: (not r["verified"], r["name"]))

    # INSTALAÇÃO
    def install(
        self,
        name_or_url: str,
        progress_cb: Any = None,
    ) -> dict[str, Any]:
        """
        Instala um chunk.

        name_or_url pode ser:
            "GeoLocate"                           → nome no registry oficial
            "github:lio/myfi-chunk-geolocate"     → shorthand GitHub
            "https://github.com/lio/chunk.git"    → URL Git completo
            "/path/local/chunk"                   → path local (dev)

        progress_cb(step: str) — callback opcional para feedback visual.
        """
        def _progress(msg: str) -> None:
            if progress_cb:
                progress_cb(msg)
            logger.info(f"install: {msg}")

        #resolver URL
        chunk_name, repo_url = self._resolve(name_or_url)

        if chunk_name in self._db["chunks"]:
            raise ValueError(f"'{chunk_name}' ja esta instalado. Usa 'chunk update' para actualizar.")

        target_dir = _CHUNKS_DIR / chunk_name.lower()

        try:
            #clone
            _progress(f"Cloning {repo_url}...")
            self._git_clone(repo_url, target_dir)

            #ler manifesto do repo
            _progress("Reading chunk manifest...")
            chunk_json = self._read_chunk_json(target_dir)

            #instalar dependencias
            requires = chunk_json.get("requires", [])
            if requires:
                _progress(f"Installing dependencies: {', '.join(requires)}")
                self._pip_install(requires)

            #correr setup
            if chunk_json.get("setup", False):
                _progress("Running setup...")
                self._run_setup(target_dir, chunk_name)

            #registar
            self._db["chunks"][chunk_name] = {
                "name":      chunk_name,
                "version":   chunk_json.get("version", "?"),
                "repo":      repo_url,
                "path":      str(target_dir),
                "requires":  requires,
                "installed": _now(),
            }
            self._save_db()

            _progress(f"{chunk_name} installed successfully.")
            return self._db["chunks"][chunk_name]

        except Exception as e:
            # limpar em caso de falha
            if target_dir.exists():
                shutil.rmtree(target_dir, ignore_errors=True)
            raise RuntimeError(f"Install failed: {e}") from e

    # REMOÇÃO
    def remove(self, name: str, keep_data: bool = False) -> None:
        """
        Remove um chunk instalado.
        keep_data=True mantém ficheiros de dados (ex: bases GeoLite2).
        """
        if name not in self._db["chunks"]:
            raise ValueError(f"'{name}' nao esta instalado.")

        info       = self._db["chunks"][name]
        target_dir = Path(info["path"])

        # correr teardown se existir
        try:
            self._run_teardown(target_dir, name, keep_data)
        except Exception as e:
            logger.warning(f"teardown falhou para '{name}': {e}")

        # remover ficheiros
        if target_dir.exists():
            shutil.rmtree(target_dir, ignore_errors=True)

        del self._db["chunks"][name]
        self._save_db()

    # ACTUALIZAÇÃO
    def update(self, name: str, progress_cb: Any = None) -> dict[str, Any]:
        """Actualiza um chunk instalado via git pull."""
        def _progress(msg: str) -> None:
            if progress_cb:
                progress_cb(msg)
            logger.info(f"update: {msg}")

        if name not in self._db["chunks"]:
            raise ValueError(f"'{name}' nao esta instalado.")

        info       = self._db["chunks"][name]
        target_dir = Path(info["path"])

        _progress(f"Updating {name}...")
        self._git_pull(target_dir)

        # re-ler manifesto — versao pode ter mudado
        chunk_json   = self._read_chunk_json(target_dir)
        new_version  = chunk_json.get("version", "?")
        old_version  = info.get("version", "?")

        # re-instalar dependencias se mudaram
        new_requires = chunk_json.get("requires", [])
        if new_requires != info.get("requires", []):
            _progress(f"Updating dependencies: {', '.join(new_requires)}")
            self._pip_install(new_requires)

        self._db["chunks"][name]["version"]  = new_version
        self._db["chunks"][name]["requires"] = new_requires
        self._db["chunks"][name]["updated"]  = _now()
        self._save_db()

        _progress(f"{name} updated: {old_version} → {new_version}")
        return self._db["chunks"][name]

    def update_all(self, progress_cb: Any = None) -> list[str]:
        """Actualiza todos os chunks instalados. Devolve lista de actualizados."""
        updated = []
        for name in list(self._db["chunks"].keys()):
            try:
                self.update(name, progress_cb)
                updated.append(name)
            except Exception as e:
                logger.error(f"update_all: '{name}' falhou: {e}")
        return updated

    # DISCOVERY — usado pelo engine
    def installed_paths(self) -> list[Path]:
        """
        Devolve paths de todos os chunks externos instalados.
        Usado pelo engine para carregar os chunks.
        """
        paths = []
        for info in self._db["chunks"].values():
            p = Path(info["path"])
            if p.exists() and (p / "__init__.py").exists():
                paths.append(p)
            else:
                logger.warning(
                    f"ChunkManager: chunk path nao encontrado: {p}"
                )
        return paths

    def list_installed(self) -> list[dict[str, Any]]:
        """Lista chunks instalados com health check."""
        result = []
        for name, info in self._db["chunks"].items():
            health_ok, health_msg = self._health_check(Path(info["path"]), name)
            result.append({
                **info,
                "health":     health_ok,
                "health_msg": health_msg,
            })
        return result

    # HELPERS PRIVADOS
    def _resolve(self, name_or_url: str) -> tuple[str, str]:
        """
        Resolve name_or_url para (chunk_name, repo_url).
        """
        # path local — para desenvolvimento
        if name_or_url.startswith("/") or name_or_url.startswith("."):
            p    = Path(name_or_url).resolve()
            name = p.name
            return name, str(p)

        # URL Git completo
        if name_or_url.startswith("https://") or name_or_url.startswith("git@"):
            name = name_or_url.rstrip("/").split("/")[-1].removesuffix(".git")
            name = _normalise_name(name)
            return name, name_or_url

        # shorthand github:autor/repo
        if name_or_url.startswith("github:"):
            slug = name_or_url[7:]
            name = slug.split("/")[-1]
            name = _normalise_name(name)
            return name, f"https://github.com/{slug}.git"

        # nome no registry oficial
        registry = self.fetch_registry()
        chunks   = registry.get("chunks", {})
        if name_or_url in chunks:
            info = chunks[name_or_url]
            repo = info["repo"]
            # resolver shorthand do registry
            if repo.startswith("github:"):
                slug = repo[7:]
                repo = f"https://github.com/{slug}.git"
            return name_or_url, repo

        raise ValueError(
            f"'{name_or_url}' nao encontrado no registry. "
            f"Usa um URL Git completo ou 'github:autor/repo'."
        )

    @staticmethod
    def _git_clone(url: str, target: Path) -> None:
        if target.exists():
            shutil.rmtree(target)
        result = subprocess.run(
            ["git", "clone", "--depth", "1", url, str(target)],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git clone falhou: {result.stderr.strip()}")

    @staticmethod
    def _git_pull(target: Path) -> None:
        result = subprocess.run(
            ["git", "-C", str(target), "pull", "--ff-only"],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"git pull falhou: {result.stderr.strip()}")

    @staticmethod
    def _read_chunk_json(target: Path) -> dict[str, Any]:
        chunk_json = target / "chunk.json"
        if not chunk_json.exists():
            logger.warning(f"chunk.json nao encontrado em {target} — usando defaults.")
            return {}
        try:
            return json.loads(chunk_json.read_text())
        except json.JSONDecodeError as e:
            raise RuntimeError(f"chunk.json invalido: {e}")

    @staticmethod
    def _pip_install(packages: list[str]) -> None:
        if not packages:
            return
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "--quiet", *packages],
            capture_output=True, text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"pip install falhou: {result.stderr.strip()[:200]}")

    @staticmethod
    def _run_setup(target: Path, name: str) -> None:
        """Importa o chunk e corre setup() se existir."""
        try:
            spec   = importlib.util.spec_from_file_location(
                f"myfi_ext_{name.lower()}", target / "__init__.py"
            )
            mod    = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr in dir(mod):
                cls = getattr(mod, attr)
                if (
                    isinstance(cls, type)
                    and hasattr(cls, "setup")
                    and cls.__name__ != "BaseChunk"
                ):
                    cls.setup()
                    break
        except Exception as e:
            raise RuntimeError(f"setup() falhou: {e}")

    @staticmethod
    def _run_teardown(target: Path, name: str, keep_data: bool) -> None:
        try:
            spec = importlib.util.spec_from_file_location(
                f"myfi_ext_{name.lower()}", target / "__init__.py"
            )
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr in dir(mod):
                cls = getattr(mod, attr)
                if (
                    isinstance(cls, type)
                    and hasattr(cls, "teardown")
                    and cls.__name__ != "BaseChunk"
                ):
                    if not keep_data:
                        cls.teardown()
                    break
        except Exception as e:
            logger.warning(f"teardown falhou: {e}")

    @staticmethod
    def _health_check(target: Path, name: str) -> tuple[bool, str]:
        try:
            spec = importlib.util.spec_from_file_location(
                f"myfi_ext_{name.lower()}", target / "__init__.py"
            )
            mod  = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            for attr in dir(mod):
                cls = getattr(mod, attr)
                if (
                    isinstance(cls, type)
                    and hasattr(cls, "health_check")
                    and cls.__name__ != "BaseChunk"
                ):
                    return cls.health_check()
            return True, "ok"
        except Exception as e:
            return False, str(e)[:80]


# HELPERS
def _normalise_name(raw: str) -> str:
    """myfi-chunk-geolocate → GeoLocate (best effort)."""
    name = raw.lower()
    for prefix in ("myfi-chunk-", "myfi_chunk_", "chunk-", "chunk_"):
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    return name.replace("-", "_").title().replace("_", "")


def _now() -> str:
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
