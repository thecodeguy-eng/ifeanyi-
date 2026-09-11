# platform_app/geoip.py
"""Best-effort IP -> country lookup, used to show where a user registered from."""

import ipaddress
import logging

import requests
from django.core.cache import cache

logger = logging.getLogger(__name__)


def _is_public_ip(ip_address):
    try:
        addr = ipaddress.ip_address(ip_address)
    except ValueError:
        return False
    return not (addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved)


def get_country_from_ip(ip_address):
    """
    Resolve a public IP address to a country name.
    Returns None on any failure (private IP, network error, rate limit, etc.)
    so callers never need to worry about this raising.
    """
    if not ip_address or not _is_public_ip(ip_address):
        return None

    cache_key = f"geoip_country_{ip_address}"
    cached = cache.get(cache_key, '__missing__')
    if cached != '__missing__':
        return cached

    country = None
    try:
        response = requests.get(
            f"http://ip-api.com/json/{ip_address}",
            params={'fields': 'status,country'},
            timeout=2,
        )
        data = response.json()
        if data.get('status') == 'success':
            country = data.get('country')
    except Exception as e:
        logger.warning(f"GeoIP lookup failed for {ip_address}: {e}")

    cache.set(cache_key, country, 60 * 60 * 24)
    return country


def get_client_ip(request):
    """Same precedence used by UserActivityMiddleware, kept here to avoid duplication."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '')
