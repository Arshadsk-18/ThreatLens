"""Image validation and fetching service wrapper."""
from __future__ import annotations

import asyncio
from urllib.parse import urlsplit

from app.services.image_fetch import fetch_icon_hash, is_host_allowlisted


def fetch_and_hash_image(url: str) -> str | None:
    """Validate image host against allowlist and fetch perceptual hash.

    Raises ValueError if host or scheme violates security allowlist.
    """
    if not url or not isinstance(url, str):
        raise ValueError("URL must be a non-empty string.")

    url_clean = url.strip()
    if not url_clean.startswith("https://"):
        raise ValueError(f"Scheme must be https, got {url_clean!r}")

    parsed = urlsplit(url_clean)
    if not is_host_allowlisted(parsed.hostname or ""):
        raise ValueError(f"Host {parsed.hostname!r} is not in image allowlist")

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                return executor.submit(asyncio.run, fetch_icon_hash(url_clean)).result()
        return loop.run_until_complete(fetch_icon_hash(url_clean))
    except RuntimeError:
        return asyncio.run(fetch_icon_hash(url_clean))
