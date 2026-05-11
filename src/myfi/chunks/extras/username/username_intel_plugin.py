from __future__ import annotations

import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)

# CONSTANTES

_WMN_URL = (
    "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
)

_CACHE_DIR  = Path.home() / ".cache" / "myfi"
_CACHE_FILE = _CACHE_DIR / "wmn-data.json"
_CACHE_TTL  = timedelta(days=7)

_TIMEOUT     = 12
_MAX_WORKERS = 20

# Protecções que tornam verificação impossível sem browser headless
_SKIP_PROTECTIONS = {"cloudflare", "captcha", "userauth"}

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_.\-]{1,64}$")

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# SESSION HTTP

def _build_session() -> requests.Session:
    session = requests.Session()
    retry = Retry(
        total=2,
        backoff_factor=0.5,
        status_forcelist={429, 500, 502, 503, 504},
        allowed_methods={"GET", "POST", "HEAD"},
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update(_DEFAULT_HEADERS)
    return session

# DATASET WMN — DOWNLOAD + CACHE

def _load_wmn_dataset(session: requests.Session) -> list[dict]:
    """
    aqui ele Carrega o dataset WMN com cache local (TTL 7 dias).
    Se o download falhar mas o cache existir, usa o cache mesmo expirado.
    """
    _CACHE_DIR.mkdir(parents=True, exist_ok=True)

    cache_valid = (
        _CACHE_FILE.exists()
        and datetime.fromtimestamp(_CACHE_FILE.stat().st_mtime)
        > datetime.now() - _CACHE_TTL
    )

    if not cache_valid:
        logger.info("WMN: a descarregar dataset actualizado...")
        try:
            resp = session.get(_WMN_URL, timeout=30)
            resp.raise_for_status()
            _CACHE_FILE.write_bytes(resp.content)
            logger.info(f"WMN: dataset guardado em {_CACHE_FILE}")
        except Exception as e:
            if _CACHE_FILE.exists():
                logger.warning(f"WMN: download falhou ({e}), usando cache existente.")
            else:
                raise RuntimeError(
                    f"Não foi possível descarregar o dataset WMN e não existe cache local.\n"
                    f"Verifica a ligação à rede. Erro: {e}"
                )

    try:
        data = json.loads(_CACHE_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        _CACHE_FILE.unlink(missing_ok=True)
        raise RuntimeError(
            f"Dataset WMN corrompido. Cache apagado — tenta de novo. Erro: {e}"
        )

    sites = data.get("sites", [])
    logger.info(f"WMN: {len(sites)} sites no dataset.")
    return sites


def _filter_sites(sites: list[dict]) -> list[dict]:
    """
    Filtra sites inutilizáveis:
      - valid == False  → marcado pelo maintainer como quebrado
      - protection ∩ _SKIP_PROTECTIONS ≠ ∅ → impossível sem browser headless
    """
    active = []
    n_invalid = n_protected = 0

    for site in sites:
        if site.get("valid") is False:
            n_invalid += 1
            continue
        protections = set(site.get("protection", []))
        if protections & _SKIP_PROTECTIONS:
            n_protected += 1
            continue
        active.append(site)

    logger.info(
        f"WMN: {len(active)} sites activos "
        f"(skipped: {n_invalid} invalid, {n_protected} protected)"
    )
    return active


# PLUGIN

class UsernameIntelPlugin:

    def __init__(self) -> None:
        self._session: requests.Session = _build_session()
        self._sites: list[dict] | None  = None  # lazy load

    # DATASET — LAZY LOAD

    def _ensure_dataset(self) -> None:
        if self._sites is None:
            raw          = _load_wmn_dataset(self._session)
            self._sites  = _filter_sites(raw)

    # INPUT VALIDATION

    @staticmethod
    def _validate(username: str) -> str:
        username = username.strip()
        if not username:
            raise ValueError("Username vazio.")
        if not _USERNAME_RE.match(username):
            raise ValueError(
                f"Username inválido: '{username}'. "
                "Charset: a-z A-Z 0-9 _ . - (máx 64 chars)."
            )
        return username

    # VERIFICAÇÃO DE UM SITE

    def _check_site(self, site: dict, username: str) -> dict[str, Any]:
        """
        Implementa as regras de detecção WMN para um site:

          FOUND         → code == e_code  AND  (e_string in body  OR  e_string == "")
          NOT FOUND     → code == m_code  AND  (m_string in body  OR  m_string == "")
          INCONCLUSIVE  → nenhuma das regras acima se aplica

        INCONCLUSIVE nunca é reportado como found — sem falsos positivos.
        """
        name      = site["name"]
        e_code    = site.get("e_code",   200)
        e_string  = site.get("e_string", "")
        m_string  = site.get("m_string", "")
        m_code    = site.get("m_code",   404)
        cat       = site.get("cat",      "other")
        post_body = site.get("post_body", "")

        # strip_bad_char — normaliza username para este site
        uname = username
        for ch in site.get("strip_bad_char", ""):
            uname = uname.replace(ch, "")

        url    = site["uri_check"].replace("{account}", uname)
        pretty = (site.get("uri_pretty", "") or url).replace("{account}", uname)

        headers = {**_DEFAULT_HEADERS, **site.get("headers", {})}

        try:
            if post_body:
                body_str = post_body.replace("{account}", uname)
                try:
                    json.loads(body_str)
                    headers.setdefault("Content-Type", "application/json")
                except json.JSONDecodeError:
                    headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
                resp = self._session.post(
                    url, data=body_str, headers=headers,
                    timeout=_TIMEOUT, allow_redirects=True,
                )
            else:
                resp = self._session.get(
                    url, headers=headers,
                    timeout=_TIMEOUT, allow_redirects=True,
                )

        except requests.Timeout:
            return _r(name, pretty, cat, "timeout", False)
        except requests.ConnectionError:
            return _r(name, pretty, cat, "unreachable", False)
        except requests.TooManyRedirects:
            return _r(name, pretty, cat, "redirect_loop", False)
        except requests.RequestException as exc:
            return _r(name, pretty, cat, str(exc)[:60], False)

        code = resp.status_code
        text = resp.text

        found_by_code    = (code == e_code)
        found_by_estring = (not e_string) or (e_string in text)
        miss_by_mstring  = (not m_string) or (m_string in text)
        miss_by_code     = (code == m_code)

        if found_by_code and found_by_estring:
            # edge case: m_string também presente → site ambíguo
            if m_string and m_string in text:
                return _r(name, pretty, cat, f"ambiguous_http_{code}", False)
            return _r(name, pretty, cat, "found", True)

        if miss_by_code and miss_by_mstring:
            return _r(name, pretty, cat, "not_found", False)

        return _r(name, pretty, cat, f"inconclusive_http_{code}", False)


    # ENTRY POIN

    def search(self, username: str) -> dict[str, Any]:
        """
        Pesquisa o username em todos os sites WMN activos.

        Raises:
            ValueError:   username inválido
            RuntimeError: dataset não disponível (rede + sem cache)
        """
        username = self._validate(username)
        self._ensure_dataset()

        results: list[dict[str, Any]] = []
        t0 = time.monotonic()

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            futures = {
                pool.submit(self._check_site, site, username): site
                for site in self._sites
            }
            for future in as_completed(futures):
                site = futures[future]
                try:
                    results.append(future.result())
                except Exception as exc:
                    name = site.get("name", "?")
                    logger.error(f"check_site '{name}': {exc}")
                    results.append(
                        _r(name, site.get("uri_check", ""), site.get("cat", "other"),
                           f"error: {exc}", False)
                    )

        elapsed = time.monotonic() - t0
        results.sort(key=lambda r: (not r["found"], r["platform"].lower()))
        intel = _enrich(results, username, elapsed)

        return {"results": results, "intel": intel, "engine": "wmn"}


# HELPERS

def _r(name: str, url: str, cat: str, status: str, found: bool) -> dict[str, Any]:
    return {"platform": name, "url": url, "cat": cat, "found": found, "status": status}


def _enrich(results: list[dict], username: str, elapsed: float) -> dict[str, Any]:
    found        = [r for r in results if r["found"]]
    inconclusive = [r for r in results if "inconclusive" in r["status"]]
    errors       = [r for r in results
                    if r["status"] in ("timeout", "unreachable", "redirect_loop")
                    or r["status"].startswith("error")]
    categories   = _categorise(found)

    return {
        "username":           username,
        "engine":             "wmn",
        "total_checked":      len(results),
        "total_found":        len(found),
        "total_inconclusive": len(inconclusive),
        "total_errors":       len(errors),
        "elapsed_s":          round(elapsed, 1),
        "exposure_score":     _exposure_score(found, categories),
        "categories":         categories,
        "google_dorks":       _google_dorks(username),
    }


def _categorise(found: list[dict]) -> dict[str, list[str]]:
    cats: dict[str, list[str]] = {}
    for r in found:
        cats.setdefault(r.get("cat", "other"), []).append(r["platform"])
    return cats


_CATEGORY_WEIGHTS: dict[str, int] = {
    "social":       3,
    "professional": 3,
    "content":      2,
    "tech":         2,
    "gaming":       1,
    "finance":      3,
    "dating":       4,
    "forums":       4,
    "leaked":       5,
    "other":        1,
}


def _exposure_score(found: list[dict], categories: dict[str, list[str]]) -> str:
    if not found:
        return "none"
    score = sum(
        _CATEGORY_WEIGHTS.get(cat, 1) * len(platforms)
        for cat, platforms in categories.items()
    )
    if score <= 4:  return "low"
    if score <= 12: return "medium"
    if score <= 24: return "high"
    return "critical"


def _google_dorks(username: str) -> list[dict[str, str]]:
    base  = "https://www.google.com/search?q="
    dorks = [
        ("exact match",     f'"{username}"'),
        ("email pattern",   f'"{username}" "@"'),
        ("documents",       f'"{username}" filetype:pdf OR filetype:doc OR filetype:xlsx'),
        ("forums",          f'"{username}" site:reddit.com OR site:quora.com OR site:stackoverflow.com'),
        ("paste sites",     f'"{username}" site:pastebin.com OR site:ghostbin.co OR site:rentry.co'),
        ("github",          f'"{username}" site:github.com'),
        ("linkedin",        f'"{username}" site:linkedin.com'),
        ("breach mentions", f'"{username}" "leaked" OR "breach" OR "dump" OR "combolist"'),
        ("credentials",     f'"{username}" "password" OR "passwd" OR "pwd"'),
    ]
    return [{"name": n, "url": base + quote_plus(q)} for n, q in dorks]
