import logging

from django.core.cache import caches

logger = logging.getLogger(__name__)


def rate_limited(key, limit, window_seconds):
    """Record one hit for `key`; True once it exceeds `limit` hits within the window.

    Backed by the database cache (see CACHES['ratelimit']) because Vercel runs
    many short-lived instances - an in-memory counter would reset constantly.
    Fails open: if the cache table is unavailable we log and allow the request
    rather than locking every user out.
    """
    cache = caches['ratelimit']
    key = f'rl:{key}'
    try:
        if cache.add(key, 1, window_seconds):
            return False
        return cache.incr(key) > limit
    except Exception as e:
        logger.error(f"Rate limit check failed for {key}: {e}")
        return False


def reset_rate_limit(key):
    try:
        caches['ratelimit'].delete(f'rl:{key}')
    except Exception as e:
        logger.error(f"Rate limit reset failed for {key}: {e}")
