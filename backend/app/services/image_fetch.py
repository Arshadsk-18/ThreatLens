"""Safe icon and avatar image fetcher and perceptual hash computation.

Owner: Person 3 (backend/app/services/image_fetch.py)
Reference: Contract Sections 5.6, 12, 13.4

Hard rules (Section 5.6):
- Return None on ANY violation or failure. Never raise to the caller.
- https only. Reject userinfo, explicit ports other than 443, IP-literal hosts, empty hosts.
- Host allowlist by exact match or exact suffix match on a dot boundary: *.mzstatic.com
  and cdn.bsky.app. Single constant ALLOWLISTED_HOST_RULES.
- Redirects: manual following up to 3 hops; every hop must be https, allowlisted, and on
  the SAME host as the original request. Cross-host redirects return None.
- Total timeout 5 s. Stream body and stop at 2 MB.
- Content-Type must start with image/. Reject SVG. Allowed raster formats: PNG, JPEG, WEBP, GIF.
- Pillow pixel limit 25_000_000; DecompressionBombError/Warning treated as failure.
  Open, verify(), reopen, convert to RGB before hashing.
- Hash: imagehash.phash 8x8 (64-bit) -> 16-character lowercase hex string.
- Never write to disk, never serve, never execute, never log URLs with query strings or bytes.
"""

from __future__ import annotations

import io
import ipaddress
import os
import time
import warnings
from urllib.parse import urljoin, urlsplit

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")

import httpx
import imagehash
from PIL import Image

# Security constants (Section 5.6)
MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB size cap
TOTAL_TIMEOUT_SECONDS = 5.0
MAX_REDIRECT_HOPS = 3
MAX_URL_LENGTH = 2048

# Single host allowlist constant (Contract 5.6 & SPIKE_RESULTS.md)
# Exact hostnames or suffix patterns (prefixed with '.')
ALLOWLISTED_HOST_RULES: tuple[str, ...] = (
    "cdn.bsky.app",
    "mzstatic.com",
    ".mzstatic.com",
)

# Pillow DecompressionBomb protection
Image.MAX_IMAGE_PIXELS = 25_000_000

# Allowed raster image formats
_ALLOWED_IMAGE_FORMATS = frozenset({"PNG", "JPEG", "WEBP", "GIF"})


def is_ip_literal(host: str) -> bool:
    """Return True if host is an IPv4 or IPv6 address literal."""
    if not host:
        return False
    clean = host.strip("[]").strip()
    try:
        ipaddress.ip_address(clean)
        return True
    except ValueError:
        return False


def is_host_allowlisted(host: str) -> bool:
    """Validate host against allowlist using exact match or dot-boundary suffix match."""
    if not host:
        return False
    h = host.lower().strip()
    if is_ip_literal(h):
        return False
    for rule in ALLOWLISTED_HOST_RULES:
        if rule.startswith("."):
            if h.endswith(rule):
                return True
        elif h == rule:
            return True
    return False


async def fetch_icon_hash(
    url: str,
    client: httpx.AsyncClient | None = None,
) -> str | None:
    """Safely fetch an icon/avatar image and compute its 64-bit perceptual hash.

    Returns a 16-character lowercase hex string on success, or None on ANY
    violation, security failure, network error, or decoding failure. Never raises.
    """
    if not url or not isinstance(url, str):
        return None

    url_clean = url.strip()
    if not url_clean or len(url_clean) > MAX_URL_LENGTH:
        return None

    if not url_clean.startswith("https://"):
        return None

    try:
        parsed = urlsplit(url_clean)
    except Exception:  # noqa: BLE001
        return None

    if parsed.scheme.lower() != "https":
        return None

    # Reject userinfo
    if parsed.username or parsed.password or "@" in (parsed.netloc or ""):
        return None

    # Reject explicit ports other than 443
    if parsed.port is not None and parsed.port != 443:
        return None

    # Validate hostname
    if not parsed.hostname or not parsed.hostname.strip():
        return None

    host_clean = parsed.hostname.lower().strip()
    if is_ip_literal(host_clean) or not is_host_allowlisted(host_clean):
        return None

    # Execute fetch with manual redirect checking and streaming cap
    async def _execute_fetch(http_client: httpx.AsyncClient) -> bytes | None:
        current_url = url_clean
        original_host = host_clean
        visited_urls = {current_url}
        hop_count = 0
        t0 = time.monotonic()

        while True:
            remaining_time = TOTAL_TIMEOUT_SECONDS - (time.monotonic() - t0)
            if remaining_time <= 0:
                return None

            request_timeout = httpx.Timeout(
                timeout=remaining_time,
                connect=min(5.0, remaining_time),
                read=min(5.0, remaining_time),
            )

            try:
                async with http_client.stream(
                    "GET",
                    current_url,
                    follow_redirects=False,
                    timeout=request_timeout,
                ) as resp:
                    # Handle redirect (manual following, max 3 hops, same host only)
                    if resp.status_code in (301, 302, 303, 307, 308):
                        hop_count += 1
                        if hop_count > MAX_REDIRECT_HOPS:
                            return None

                        location = resp.headers.get("location")
                        if not location:
                            return None

                        redirect_url = urljoin(current_url, location)
                        if not redirect_url.startswith("https://"):
                            return None

                        redir_parsed = urlsplit(redirect_url)
                        if redir_parsed.scheme.lower() != "https":
                            return None
                        if (
                            redir_parsed.username
                            or redir_parsed.password
                            or "@" in (redir_parsed.netloc or "")
                        ):
                            return None
                        if redir_parsed.port is not None and redir_parsed.port != 443:
                            return None

                        redir_host = (redir_parsed.hostname or "").lower().strip()
                        if not redir_host or is_ip_literal(redir_host):
                            return None

                        # Redirect must be on the SAME host as original request
                        if redir_host != original_host:
                            return None

                        if not is_host_allowlisted(redir_host):
                            return None

                        if redirect_url in visited_urls:
                            # Redirect loop detected
                            return None

                        visited_urls.add(redirect_url)
                        current_url = redirect_url
                        continue

                    if resp.status_code != 200:
                        return None

                    # Validate Content-Type
                    ct_header = resp.headers.get("content-type", "")
                    content_type = ct_header.lower().split(";")[0].strip()
                    if not content_type.startswith("image/"):
                        return None
                    if content_type in ("image/svg+xml", "image/svg"):
                        return None

                    # Check Content-Length if present
                    cl_header = resp.headers.get("content-length")
                    if cl_header:
                        try:
                            if int(cl_header) > MAX_SIZE_BYTES:
                                return None
                        except ValueError:
                            pass

                    # Stream body and enforce 2 MB cap
                    buf = bytearray()
                    async for chunk in resp.aiter_bytes():
                        buf.extend(chunk)
                        if len(buf) > MAX_SIZE_BYTES:
                            return None

                    return bytes(buf)

            except Exception:  # noqa: BLE001
                return None

    try:
        if client is not None:
            raw_bytes = await _execute_fetch(client)
        else:
            async with httpx.AsyncClient() as default_client:
                raw_bytes = await _execute_fetch(default_client)
    except Exception:  # noqa: BLE001
        return None

    if not raw_bytes:
        return None

    # Reject SVG or XML magic bytes
    start_bytes = raw_bytes[:100].lstrip().lower()
    if start_bytes.startswith((b"<svg", b"<?xml")) or b"<svg" in start_bytes:
        return None

    # Pillow decoding and perceptual hashing
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)

            # 1. Open and verify file integrity
            bio = io.BytesIO(raw_bytes)
            with Image.open(bio) as img:
                fmt = (img.format or "").upper()
                if fmt not in _ALLOWED_IMAGE_FORMATS:
                    return None
                img.verify()

            # 2. Reopen to load pixels safely and convert to RGB
            bio.seek(0)
            with Image.open(bio) as img:
                if fmt == "GIF":
                    img.seek(0)
                rgb_img = img.convert("RGB")
                phash_val = imagehash.phash(rgb_img)
                return str(phash_val).lower()
    except Exception:  # noqa: BLE001
        return None


__all__ = [
    "ALLOWLISTED_HOST_RULES",
    "MAX_SIZE_BYTES",
    "TOTAL_TIMEOUT_SECONDS",
    "fetch_icon_hash",
    "is_host_allowlisted",
    "is_ip_literal",
]
