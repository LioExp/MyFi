from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

_BASE_URL      = "https://ipwho.is"
_TIMEOUT       = 5
_MAPS_TEMPLATE = "https://www.google.com/maps/@{lat},{lon},8z"


class GeoIPPlugin:
    """Queries the ipwho.is API to geolocate an IP."""

    def lookup(self, ip: str) -> dict | None:
        """
        Geolocates an IP.
        Returns a dict with relevant fields or None in case of error.

        Raises:
            TimeoutError:     if the API does not respond in time.
            ConnectionError:  if there is no network connection.
            RuntimeError:     if the API returns HTTP != 2xx.
        """
        try:
            response = requests.get(f"{_BASE_URL}/{ip}", timeout=_TIMEOUT)
            response.raise_for_status()
        except requests.Timeout:
            raise TimeoutError(f"GeoIP: timeout querying {ip}.")
        except requests.ConnectionError as e:
            raise ConnectionError(f"GeoIP: no connection for {ip}: {e}")
        except requests.HTTPError as e:
            raise RuntimeError(
                f"GeoIP: HTTP {e.response.status_code} for {ip}."
            )

        try:
            data = response.json()
        except ValueError as e:
            logger.error(f"GeoIP: invalid response (not JSON) for {ip}: {e}")
            return None

        if not data.get("success", False):
            logger.warning(
                f"GeoIP: no success for {ip}: "
                f"{data.get('message', 'unknown error')}"
            )
            return None

        lat = data.get("latitude")
        lon = data.get("longitude")
        conn = data.get("connection") or {}

        return {
            "ip":        ip,
            "country":   data.get("country")  or "unknown",
            "city":      data.get("city")      or "unknown",
            "latitude":  lat,
            "longitude": lon,
            "isp":       conn.get("isp")       or "unknown",
            "org":       conn.get("org")       or "unknown",
            "maps_url":  (
                _MAPS_TEMPLATE.format(lat=lat, lon=lon)
                if lat is not None and lon is not None
                else "#"
            ),
        }
