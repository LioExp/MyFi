# src/myfi/chunks/extras/phone/phone_intel_plugin.py
from __future__ import annotations

import logging
import subprocess
import sys
from typing import Any

import phonenumbers
import requests
from phonenumbers import carrier, geocoder, timezone

logger = logging.getLogger(__name__)

_REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
_REQUEST_TIMEOUT = 10


class PhoneIntelPlugin:
    """Plugin that analyzes phone numbers."""

    def __init__(self, config: Any = None):
        # config injected — no ConfigManager() within methods
        self._config = config

    # ════════════════════════════════════════════════════════════
    # MAIN LOOKUP
    # ════════════════════════════════════════════════════════════

    def lookup(self, phone: str, default_region: str = "AO") -> dict | None:
        """
        Analyzes a phone number.
        Returns a dict with data or None if the number is invalid.
        """
        try:
            parsed = phonenumbers.parse(phone, default_region)
        except phonenumbers.NumberParseException as e:
            logger.warning(f"Invalid number '{phone}': {e}")
            return None

        if not phonenumbers.is_valid_number(parsed):
            logger.warning(f"Invalid number: {phone}")
            return None

        return {
            "phone":                    phone,
            "formatted_international":  phonenumbers.format_number(
                                            parsed,
                                            phonenumbers.PhoneNumberFormat.INTERNATIONAL,
                                        ),
            "country_code":             parsed.country_code,
            "national_number":          parsed.national_number,
            "region":                   phonenumbers.region_code_for_number(parsed),
            "carrier":                  carrier.name_for_number(parsed, "en") or "unknown",
            "location":                 (
                                            geocoder.description_for_number(parsed, "pt")
                                            or geocoder.description_for_number(parsed, "en")
                                            or "unknown"
                                        ),
            "timezone":                 ", ".join(timezone.time_zones_for_number(parsed))
                                        or "unknown",
            "valid":                    True,
            "possible":                 phonenumbers.is_possible_number(parsed),
            "number_type":              self._get_number_type(parsed),
        }

    def _get_number_type(self, parsed) -> str:
        from phonenumbers import PhoneNumberType
        return {
            PhoneNumberType.MOBILE:              "mobile",
            PhoneNumberType.FIXED_LINE:          "fixed line",
            PhoneNumberType.FIXED_LINE_OR_MOBILE:"fixed or mobile",
            PhoneNumberType.TOLL_FREE:           "toll free",
            PhoneNumberType.PREMIUM_RATE:        "premium rate",
            PhoneNumberType.VOIP:                "voip",
        }.get(phonenumbers.number_type(parsed), "other")

    # ════════════════════════════════════════════════════════════
    # DEEP SEARCH
    # ════════════════════════════════════════════════════════════

    def deep_search(self, phone: str) -> dict:
        """
        Aggressive search in public sources.
        Each source is isolated — a failure does not cancel the others.
        Returns a dict with partial results and errors found.
        """
        results: dict = {}
        errors:  dict = {}

        sources = {
            "numverify":           lambda: self._check_numverify(phone),
            "social_registration": lambda: self._check_social_registration(phone),
            "spam_check":          lambda: self._check_spam_lists(phone),
            "google_dorks":        lambda: self._generate_google_dorks(phone),
        }

        for key, fn in sources.items():
            try:
                results[key] = fn()
                logger.debug(f"deep_search: '{key}' completed.")
            except Exception as e:
                logger.error(f"deep_search: '{key}' failed: {e}")
                errors[key] = str(e)

        results["_errors"] = errors
        results["_warning"] = (
            "These data are public. "
            "Anyone could do this search manually."
        )
        return results

    # ════════════════════════════════════════════════════════════
    # SOURCES — DEEP SEARCH
    # ════════════════════════════════════════════════════════════

    def _check_numverify(self, phone: str) -> dict:
        """Validates the number via Numverify API (100 free requests/month)."""
        api_key = self._config.get("numverify_api_key") if self._config else None

        if not api_key:
            return {
                "error": (
                    "Numverify API key not configured. "
                    "Register at numverify.com (free)."
                )
            }

        url = (
            f"http://apilayer.net/api/validate"
            f"?access_key={api_key}&number={phone}&format=1"
        )

        try:
            response = requests.get(url, timeout=_REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
        except requests.Timeout:
            raise TimeoutError("Numverify: timeout.")
        except requests.ConnectionError as e:
            raise ConnectionError(f"Numverify: no connection: {e}")
        except requests.HTTPError as e:
            raise RuntimeError(f"Numverify: HTTP {e.response.status_code}")

        if data.get("valid"):
            return {
                "valid":     True,
                "number":    data.get("international_format", phone),
                "country":   data.get("country_name", "unknown"),
                "location":  data.get("location",     "unknown"),
                "carrier":   data.get("carrier",      "unknown"),
                "line_type": data.get("line_type",    "unknown"),
            }
        return {"valid": False, "error": "Number invalid according to Numverify."}

    def _check_social_registration(self, phone: str) -> list[dict]:
        """
        Checks registration on platforms via 'ignorant'.
        Each platform is isolated — a failure does not cancel the others.
        """
        platforms = ["whatsapp", "instagram", "amazon", "snapchat"]
        results   = []

        for platform in platforms:
            try:
                proc = subprocess.run(
                    [sys.executable, "-m", "ignorant", platform, phone],
                    capture_output=True,
                    text=True,
                    timeout=15,
                )
                registered = proc.returncode == 0
                results.append({
                    "platform":   platform.capitalize(),
                    "registered": registered,
                    "status":     "found" if registered else "not found",
                })
            except subprocess.TimeoutExpired:
                logger.warning(f"ignorant: timeout on '{platform}'.")
                results.append({
                    "platform":   platform.capitalize(),
                    "registered": False,
                    "status":     "timeout",
                })
            except FileNotFoundError:
                logger.error("ignorant: module not found. Install with: pip install ignorant")
                results.append({
                    "platform":   platform.capitalize(),
                    "registered": False,
                    "status":     "ignorant not installed",
                })
            except Exception as e:
                logger.error(f"ignorant: error on '{platform}': {e}")
                results.append({
                    "platform":   platform.capitalize(),
                    "registered": False,
                    "status":     f"error: {str(e)[:60]}",
                })

        return results

    def _check_spam_lists(self, phone: str) -> list[dict]:
        """Checks if the number was reported in spam lists."""
        sources = [
            {
                "name":  "ScamCallFighters",
                "url":   f"https://scamcallfighters.com/search?phone={phone}",
                "check": lambda html: "reportado" in html.lower() or "scam" in html.lower(),
            },
            {
                "name":  "WhoCallMe",
                "url":   f"https://whocallsme.com/PhoneNumber.aspx/{phone}",
                "check": lambda html: "report" in html.lower() or "spam" in html.lower(),
            },
        ]

        results = []
        for source in sources:
            try:
                response = requests.get(
                    source["url"],
                    headers=_REQUEST_HEADERS,
                    timeout=_REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                flagged = source["check"](response.text)
                results.append({
                    "source":  source["name"],
                    "flagged": flagged,
                    "status":  "flagged" if flagged else "clean",
                })
            except requests.Timeout:
                logger.warning(f"spam_check: timeout on '{source['name']}'.")
                results.append({"source": source["name"], "flagged": False, "status": "timeout"})
            except requests.ConnectionError:
                logger.warning(f"spam_check: no connection to '{source['name']}'.")
                results.append({"source": source["name"], "flagged": False, "status": "unreachable"})
            except requests.HTTPError as e:
                logger.warning(f"spam_check: HTTP {e.response.status_code} on '{source['name']}'.")
                results.append({"source": source["name"], "flagged": False, "status": f"http {e.response.status_code}"})

        return results

    def _generate_google_dorks(self, phone: str) -> list[dict]:
        """Generates Google Dorks for manual search. Does not do scraping."""
        dorks = [
            ("exact search",       f'"{phone}"'),
            ("linkedin",           f'"{phone}" site:linkedin.com'),
            ("mentions in pdfs",   f'"{phone}" filetype:pdf'),
            ("mentions in forums", f'"{phone}" site:reddit.com OR site:quora.com'),
        ]
        return [
            {
                "name": name,
                "url":  f"https://www.google.com/search?q={query}",
            }
            for name, query in dorks
        ]
