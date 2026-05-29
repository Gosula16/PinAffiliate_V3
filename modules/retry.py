"""Retry utility — exponential backoff for any API call."""

import time, logging, functools, random

logger = logging.getLogger("publisher.retry")


def with_retry(max_attempts: int = 3, base_delay: float = 2.0, exceptions=(Exception,)):
    """
    Decorator: retries a function up to max_attempts times.
    Delay doubles each attempt + random jitter.
    Usage:
        @with_retry(max_attempts=3)
        def call_api(): ...
    """
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return fn(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt == max_attempts:
                        break
                    delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
                    logger.warning(f"{fn.__name__} attempt {attempt}/{max_attempts} failed: {e} — retrying in {delay:.1f}s")
                    time.sleep(delay)
            logger.error(f"{fn.__name__} failed after {max_attempts} attempts: {last_exc}")
            raise last_exc
        return wrapper
    return decorator


def retry_call(fn, *args, max_attempts=3, base_delay=2.0, **kwargs):
    """
    Inline retry without decorator.
    Usage: result = retry_call(requests.get, url, max_attempts=3)
    """
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            last_exc = e
            if attempt == max_attempts:
                break
            delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 1)
            logger.warning(f"Attempt {attempt}/{max_attempts} failed: {e} — retry in {delay:.1f}s")
            time.sleep(delay)
    raise last_exc
