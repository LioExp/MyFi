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

# ── Constantes ────────────────────────────────────────────────────────────────

_WMN_URL    = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
_CACHE_DIR  = Path.home() / ".cache" / "myfi"
_CACHE_FILE = _CACHE_DIR / "wmn-data.json"
_CACHE_TTL  = timedelta(days=7)

_TIMEOUT     = 12
_MAX_WORKERS = 20

_SKIP_PROTECTIONS = {"cloudflare", "captcha", "userauth"}
_USERNAME_RE      = re.compile(r"^[a-zA-Z0-9_.\-]{1,64}$")

_DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

# ── Session ───────────────────────────────────────────────────────────────────

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

# ── WMN Dataset ───────────────────────────────────────────────────────────────

def _load_wmn_dataset(session: requests.Session) -> list[dict]:
    """Carrega o dataset WMN com cache local (TTL 7 dias)."""
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
        raise RuntimeError(f"Dataset WMN corrompido. Cache apagado — tenta de novo. Erro: {e}")

    sites = data.get("sites", [])
    logger.info(f"WMN: {len(sites)} sites no dataset.")
    return sites


def _filter_sites(sites: list[dict]) -> list[dict]:
    """Remove sites inválidos e protegidos por Cloudflare/captcha."""
    active, n_invalid, n_protected = [], 0, 0
    for site in sites:
        if site.get("valid") is False:
            n_invalid += 1
            continue
        if set(site.get("protection", [])) & _SKIP_PROTECTIONS:
            n_protected += 1
            continue
        active.append(site)
    logger.info(
        f"WMN: {len(active)} sites activos "
        f"(skipped: {n_invalid} invalid, {n_protected} protected)"
    )
    return active

# ═════════════════════════════════════════════════════════════════════════════
# CAMADA 3 — Free-tier APIs (sem auth obrigatória)
# Reddit, GitHub, HackerNews, Keybase
# ═════════════════════════════════════════════════════════════════════════════

def _ft_not_found(platform: str) -> dict[str, Any]:
    return {"platform": platform, "found": False, "status": "not_found", "data": {}}

def _ft_error(platform: str, reason: str) -> dict[str, Any]:
    return {"platform": platform, "found": False, "status": f"error: {reason}", "data": {}}


def _check_reddit(username: str, session: requests.Session) -> dict[str, Any]:
    url = f"https://www.reddit.com/user/{username}/about.json"
    try:
        resp = session.get(url, headers={**_DEFAULT_HEADERS, "Accept": "application/json"}, timeout=10)
    except requests.RequestException as e:
        return _ft_error("reddit", str(e))

    if resp.status_code == 404:
        return _ft_not_found("reddit")
    if resp.status_code == 403:
        # conta suspensa — existe mas está bloqueada
        return {
            "platform": "reddit", "found": True, "status": "suspended",
            "profile_url": f"https://www.reddit.com/user/{username}",
            "data": {"suspended": True},
        }
    if resp.status_code != 200:
        return _ft_error("reddit", f"HTTP {resp.status_code}")

    try:
        body = resp.json().get("data", {})
    except Exception:
        return _ft_error("reddit", "invalid JSON")

    return {
        "platform":    "reddit",
        "found":       True,
        "status":      "found",
        "profile_url": f"https://www.reddit.com/user/{username}",
        "data": {
            "id":            body.get("id"),
            "created_utc":   body.get("created_utc"),
            "total_karma":   body.get("total_karma"),
            "comment_karma": body.get("comment_karma"),
            "link_karma":    body.get("link_karma"),
            "is_gold":       body.get("is_gold"),
            "verified":      body.get("verified"),
            "subreddit": {
                "display_name": body.get("subreddit", {}).get("display_name_prefixed"),
                "subscribers":  body.get("subreddit", {}).get("subscribers"),
                "public_desc":  body.get("subreddit", {}).get("public_description"),
            } if body.get("subreddit") else None,
        },
    }


def _check_github(username: str, session: requests.Session, token: str | None = None) -> dict[str, Any]:
    url     = f"https://api.github.com/users/{username}"
    headers = {**_DEFAULT_HEADERS, "Accept": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        resp = session.get(url, headers=headers, timeout=10)
    except requests.RequestException as e:
        return _ft_error("github", str(e))

    if resp.status_code == 404:
        return _ft_not_found("github")
    if resp.status_code == 403:
        return _ft_error("github", "rate_limited — passa um GITHUB_TOKEN")
    if resp.status_code != 200:
        return _ft_error("github", f"HTTP {resp.status_code}")

    try:
        body = resp.json()
    except Exception:
        return _ft_error("github", "invalid JSON")

    return {
        "platform":    "github",
        "found":       True,
        "status":      "found",
        "profile_url": body.get("html_url"),
        "data": {
            "id":           body.get("id"),
            "login":        body.get("login"),
            "name":         body.get("name"),
            "bio":          body.get("bio"),
            "location":     body.get("location"),
            "company":      body.get("company"),
            "blog":         body.get("blog"),
            "email":        body.get("email"),
            "twitter":      body.get("twitter_username"),
            "created_at":   body.get("created_at"),
            "public_repos": body.get("public_repos"),
            "followers":    body.get("followers"),
            "following":    body.get("following"),
            "type":         body.get("type"),
        },
    }


def _check_hackernews(username: str, session: requests.Session) -> dict[str, Any]:
    url = f"https://hacker-news.firebaseio.com/v0/user/{username}.json"
    try:
        resp = session.get(url, headers={**_DEFAULT_HEADERS, "Accept": "application/json"}, timeout=10)
    except requests.RequestException as e:
        return _ft_error("hackernews", str(e))

    if resp.status_code != 200:
        return _ft_error("hackernews", f"HTTP {resp.status_code}")
    try:
        body = resp.json()
    except Exception:
        return _ft_error("hackernews", "invalid JSON")

    if body is None:
        return _ft_not_found("hackernews")

    return {
        "platform":    "hackernews",
        "found":       True,
        "status":      "found",
        "profile_url": f"https://news.ycombinator.com/user?id={username}",
        "data": {
            "id":        body.get("id"),
            "created":   body.get("created"),
            "karma":     body.get("karma"),
            "about":     body.get("about"),
            "submitted": len(body.get("submitted", [])),
        },
    }


def _check_keybase(username: str, session: requests.Session) -> dict[str, Any]:
    try:
        resp = session.get(
            "https://keybase.io/_/api/1.0/user/lookup.json",
            params={"username": username},
            headers={**_DEFAULT_HEADERS, "Accept": "application/json"},
            timeout=10,
        )
    except requests.RequestException as e:
        return _ft_error("keybase", str(e))

    if resp.status_code == 404:
        return _ft_not_found("keybase")
    if resp.status_code != 200:
        return _ft_error("keybase", f"HTTP {resp.status_code}")

    try:
        body = resp.json()
    except Exception:
        return _ft_error("keybase", "invalid JSON")

    if body.get("status", {}).get("code", -1) != 0:
        return _ft_not_found("keybase")

    them = body.get("them")
    if not them:
        return _ft_not_found("keybase")

    profile   = them[0] if isinstance(them, list) else them
    basics    = profile.get("basics", {})
    profile_d = profile.get("profile", {})
    proofs    = profile.get("proofs_summary", {}).get("all", [])
    proof_map: dict[str, list[str]] = {}
    for p in proofs:
        proof_map.setdefault(p.get("proof_type", "unknown"), []).append(p.get("nametag", ""))

    return {
        "platform":    "keybase",
        "found":       True,
        "status":      "found",
        "profile_url": f"https://keybase.io/{username}",
        "data": {
            "uid":         basics.get("uid"),
            "username":    basics.get("username"),
            "full_name":   profile_d.get("full_name"),
            "bio":         profile_d.get("bio"),
            "location":    profile_d.get("location"),
            "proofs":      proof_map,
            "public_keys": bool(profile.get("public_keys", {}).get("primary")),
        },
    }


def _run_free_tier(
    username: str,
    session:  requests.Session,
    tokens:   dict[str, str],
) -> list[dict[str, Any]]:
    return [
        _check_reddit(username, session),
        _check_github(username, session, token=tokens.get("github")),
        _check_hackernews(username, session),
        _check_keybase(username, session),
    ]

# ═════════════════════════════════════════════════════════════════════════════
# CAMADA 2 — Manual investigation package (plataformas bloqueadas)
# Twitter/X, Instagram, TikTok, LinkedIn, Facebook
# Não simula verificação — gera URLs directos e queries de investigação.
# ═════════════════════════════════════════════════════════════════════════════

def _manual_entry(
    platform: str,
    display:  str,
    reason:   str,
    direct_url: str,
    alt_urls: list[str],
    search_queries: list[dict[str, str]],
    notes: str = "",
) -> dict:
    return {
        "platform":       platform,
        "display":        display,
        "status":         "manual_required",
        "reason":         reason,
        "direct_url":     direct_url,
        "alt_urls":       alt_urls,
        "search_queries": search_queries,
        "notes":          notes,
    }


def _build_manual_package(username: str) -> list[dict]:
    q = quote_plus
    base = "https://www.google.com/search?q="
    return [
        _manual_entry(
            platform    = "twitter",
            display     = "Twitter / X",
            reason      = (
                "API Basic obrigatória ($100/mês) desde Fev 2023. "
                "Twint e equivalentes estão quebrados."
            ),
            direct_url  = f"https://x.com/{username}",
            alt_urls    = [
                f"https://nitter.net/{username}",
                f"https://xcancel.com/{username}",
            ],
            search_queries = [
                {"label": "perfil",       "url": base + q(f'site:x.com OR site:twitter.com {username}')},
                {"label": "menções",      "url": base + q(f'"@{username}" site:twitter.com OR site:x.com')},
                {"label": "wayback",      "url": f"https://web.archive.org/web/*/twitter.com/{username}"},
            ],
            notes = "Com tier Basic: GET /2/users/by/username/{username} + Bearer token.",
        ),
        _manual_entry(
            platform    = "instagram",
            display     = "Instagram",
            reason      = (
                "Graph API requer app aprovada pela Meta + OAuth. "
                "Endpoint /web_profile_info bloqueado desde 2023."
            ),
            direct_url  = f"https://www.instagram.com/{username}/",
            alt_urls    = [
                f"https://www.picuki.com/profile/{username}",
                f"https://imginn.com/{username}",
            ],
            search_queries = [
                {"label": "perfil",       "url": base + q(f'site:instagram.com/{username}')},
                {"label": "tagged",       "url": base + q(f'"@{username}" site:instagram.com')},
                {"label": "wayback",      "url": f"https://web.archive.org/web/*/instagram.com/{username}/"},
            ],
        ),
        _manual_entry(
            platform    = "tiktok",
            display     = "TikTok",
            reason      = (
                "Research API requer candidatura formal. "
                "Não existe endpoint público para user lookup."
            ),
            direct_url  = f"https://www.tiktok.com/@{username}",
            alt_urls    = [],
            search_queries = [
                {"label": "perfil",       "url": base + q(f'site:tiktok.com/@{username}')},
                {"label": "menções",      "url": base + q(f'"@{username}" tiktok')},
            ],
            notes = "Perfis são públicos no browser — verificação visual directa.",
        ),
        _manual_entry(
            platform    = "linkedin",
            display     = "LinkedIn",
            reason      = (
                "Partnership Program obrigatório. "
                "Scraping proibido por ToS e litigado (hiQ v. LinkedIn, SCOTUS 2022)."
            ),
            direct_url  = f"https://www.linkedin.com/in/{username}/",
            alt_urls    = [],
            search_queries = [
                {"label": "perfil",       "url": base + q(f'site:linkedin.com/in/ "{username}"')},
                {"label": "empresa",      "url": base + q(f'site:linkedin.com/company/ "{username}"')},
            ],
            notes = "Pesquisa Google com site:linkedin.com/in/ é frequentemente mais eficaz que acesso directo.",
        ),
        _manual_entry(
            platform    = "facebook",
            display     = "Facebook",
            reason      = (
                "Graph API requer app review da Meta. "
                "Lookup público removido desde Graph API v2.0 (2015)."
            ),
            direct_url  = f"https://www.facebook.com/{username}",
            alt_urls    = [
                f"https://www.facebook.com/search/people/?q={q(username)}",
            ],
            search_queries = [
                {"label": "perfil",       "url": base + q(f'site:facebook.com "{username}"')},
                {"label": "wayback",      "url": f"https://web.archive.org/web/*/facebook.com/{username}"},
            ],
        ),
    ]

# ═════════════════════════════════════════════════════════════════════════════
# PLUGIN PRINCIPAL
# ═════════════════════════════════════════════════════════════════════════════

class UsernameIntelPlugin:

    def __init__(self) -> None:
        self._session: requests.Session  = _build_session()
        self._sites:   list[dict] | None = None

    def _ensure_dataset(self) -> None:
        if self._sites is None:
            raw         = _load_wmn_dataset(self._session)
            self._sites = _filter_sites(raw)

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

    # ── Camada 1: verificação WMN ─────────────────────────────────────────────

    def _check_site(self, site: dict, username: str) -> dict[str, Any]:
        name      = site["name"]
        e_code    = site.get("e_code",    200)
        e_string  = site.get("e_string",  "")
        m_string  = site.get("m_string",  "")
        m_code    = site.get("m_code",    404)
        cat       = site.get("cat",       "other")
        post_body = site.get("post_body", "")

        uname = username
        for ch in site.get("strip_bad_char", ""):
            uname = uname.replace(ch, "")

        url     = site["uri_check"].replace("{account}", uname)
        pretty  = (site.get("uri_pretty", "") or url).replace("{account}", uname)
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
            if m_string and m_string in text:
                return _r(name, pretty, cat, f"ambiguous_http_{code}", False)
            return _r(name, pretty, cat, "found", True)
        if miss_by_code and miss_by_mstring:
            return _r(name, pretty, cat, "not_found", False)
        return _r(name, pretty, cat, f"inconclusive_http_{code}", False)

    # ── Entry point ───────────────────────────────────────────────────────────

    def search(
        self,
        username: str,
        tokens:   dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """
        Pesquisa o username em três camadas.

        Args:
            username: username a pesquisar
            tokens:   tokens opcionais, ex: {"github": "ghp_..."}

        Returns:
            {
                "results":   [...],   # Camada 1 — WMN (400+ plataformas)
                "free_tier": [...],   # Camada 3 — Reddit, GitHub, HN, Keybase
                "manual":    [...],   # Camada 2 — Twitter, IG, TikTok, LinkedIn, FB
                "intel":     {...},
                "engine":    "wmn+free_tier+manual",
            }

        Raises:
            ValueError:   username inválido
            RuntimeError: dataset WMN não disponível (rede + sem cache)
        """
        username = self._validate(username)
        tokens   = tokens or {}

        t0           = time.monotonic()
        wmn_results: list[dict[str, Any]] = []

        # ── Camada 1: WMN ─────────────────────────────────────────────────────
        self._ensure_dataset()
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as pool:
            futures = {
                pool.submit(self._check_site, site, username): site
                for site in self._sites
            }
            for future in as_completed(futures):
                site = futures[future]
                try:
                    wmn_results.append(future.result())
                except Exception as exc:
                    name = site.get("name", "?")
                    logger.error(f"check_site '{name}': {exc}")
                    wmn_results.append(
                        _r(name, site.get("uri_check", ""), site.get("cat", "other"),
                           f"error: {exc}", False)
                    )
        wmn_results.sort(key=lambda r: (not r["found"], r["platform"].lower()))

        # ── Camada 3: Free-tier APIs ──────────────────────────────────────────
        free_results = _run_free_tier(username, self._session, tokens)

        # ── Camada 2: Manual package ──────────────────────────────────────────
        manual = _build_manual_package(username)

        elapsed = time.monotonic() - t0
        intel   = _enrich(wmn_results, free_results, username, elapsed)

        return {
            "results":   wmn_results,
            "free_tier": free_results,
            "manual":    manual,
            "intel":     intel,
            "engine":    "wmn+free_tier+manual",
        }

# ── Helpers ───────────────────────────────────────────────────────────────────

def _r(name: str, url: str, cat: str, status: str, found: bool) -> dict[str, Any]:
    return {"platform": name, "url": url, "cat": cat, "found": found, "status": status}


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

_FREE_TIER_CATS: dict[str, str] = {
    "reddit":     "forums",
    "github":     "tech",
    "hackernews": "tech",
    "keybase":    "tech",
}


def _enrich(
    wmn_results:  list[dict],
    free_results: list[dict],
    username:     str,
    elapsed:      float,
) -> dict[str, Any]:
    found        = [r for r in wmn_results if r["found"]]
    inconclusive = [r for r in wmn_results if "inconclusive" in r.get("status", "")]
    errors       = [r for r in wmn_results
                    if r["status"] in ("timeout", "unreachable", "redirect_loop")
                    or r["status"].startswith("error")]
    free_found   = [r for r in free_results if r.get("found")]

    categories = _categorise(found)
    for r in free_found:
        cat = _FREE_TIER_CATS.get(r["platform"], "other")
        categories.setdefault(cat, []).append(r["platform"])

    return {
        "username":             username,
        "engine":               "wmn+free_tier+manual",
        "total_checked":        len(wmn_results),
        "total_found":          len(found),
        "total_free_tier":      len(free_found),
        "total_inconclusive":   len(inconclusive),
        "total_errors":         len(errors),
        "elapsed_s":            round(elapsed, 1),
        "exposure_score":       _exposure_score(found + free_found, categories),
        "categories":           categories,
        "google_dorks":         _google_dorks(username),
    }


def _categorise(found: list[dict]) -> dict[str, list[str]]:
    cats: dict[str, list[str]] = {}
    for r in found:
        cats.setdefault(r.get("cat", "other"), []).append(r["platform"])
    return cats


def _exposure_score(found: list[dict], categories: dict[str, list[str]]) -> str:
    if not found:
        return "none"
    score = sum(
        _CATEGORY_WEIGHTS.get(cat, 1) * len(platforms)
        for cat, platforms in categories.items()
    )
    if score <= 4:   return "low"
    if score <= 12:  return "medium"
    if score <= 24:  return "high"
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
