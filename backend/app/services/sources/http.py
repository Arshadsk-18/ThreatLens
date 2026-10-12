"""Standard HTTP JSON request helper for source adapters.

Owner: Person 3 (backend/app/services/sources/http.py)
Reference: Contract Sections 5.5, 10, 12
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from app.schemas import ProviderErrorCode

from .errors import ProviderError
from .ratelimit import AsyncRateLimiter

DEFAULT_USER_AGENT = "ThreatLens/3.0 (hackathon prototype)"
DEFAULT_TIMEOUT_S = 8.0
MAX_RESPONSE_BYTES = 5 * 1024 * 1024  # 5 MB cap


async def request_json(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    params: Any = None,
    *,
    timeout: float = DEFAULT_TIMEOUT_S,
    retries: int = 1,
    limiter: AsyncRateLimiter | None = None,
) -> Any:
    """Execute an HTTP request and parse JSON with contract-mandated retry and error policies.

    Rules:
    - Default timeout 8 s.
    - Limiter acquired before EVERY attempt (including retries).
    - 1 retry on 5xx or timeout; NO retry on 429; no retry on 401/403.
    - Stream body with 5 MB cap, validate UTF-8 and JSON structure (dict or list).
    - Map status and network failures to ProviderError.
    - Never leak response body, tokens, or query strings in error messages.
    - Sets User-Agent and Accept: application/json headers.
    """
    headers = {
        "User-Agent": DEFAULT_USER_AGENT,
        "Accept": "application/json",
    }
    timeout_cfg = httpx.Timeout(timeout)
    max_attempts = 1 + max(0, retries)
    attempts = 0

    while attempts < max_attempts:
        attempts += 1
        if limiter is not None:
            await limiter.acquire()

        try:
            async with client.stream(
                method=method,
                url=url,
                params=params,
                headers=headers,
                timeout=timeout_cfg,
            ) as resp:
                status = resp.status_code

                # Status 429: never retry
                if status == 429:
                    raise ProviderError(
                        ProviderErrorCode.RATE_LIMITED,
                        "Provider rate limit exceeded (HTTP 429).",
                    )

                # Status 401/403: auth required, never retry
                if status in (401, 403):
                    raise ProviderError(
                        ProviderErrorCode.AUTH_REQUIRED,
                        f"Provider authentication failed (HTTP {status}).",
                    )

                # 5xx: retry once
                if 500 <= status < 600:
                    if attempts < max_attempts:
                        continue
                    raise ProviderError(
                        ProviderErrorCode.PROVIDER_UNAVAILABLE,
                        f"Provider service temporarily unavailable (HTTP {status}).",
                    )

                # Other non-200 statuses
                if status != 200:
                    raise ProviderError(
                        ProviderErrorCode.INVALID_RESPONSE,
                        f"Provider returned unexpected status HTTP {status}.",
                    )

                # Check Content-Length header against cap
                content_len = resp.headers.get("content-length")
                if content_len:
                    try:
                        if int(content_len) > MAX_RESPONSE_BYTES:
                            raise ProviderError(
                                ProviderErrorCode.INVALID_RESPONSE,
                                "Response payload exceeded 5 MB size limit.",
                            )
                    except ValueError:
                        pass

                # Stream and accumulate body bytes
                buf = bytearray()
                async for chunk in resp.aiter_bytes():
                    buf.extend(chunk)
                    if len(buf) > MAX_RESPONSE_BYTES:
                        raise ProviderError(
                            ProviderErrorCode.INVALID_RESPONSE,
                            "Response payload exceeded 5 MB size limit.",
                        )

                # Decode UTF-8
                try:
                    text = bytes(buf).decode("utf-8")
                except UnicodeDecodeError:
                    raise ProviderError(
                        ProviderErrorCode.INVALID_RESPONSE,
                        "Response payload contains invalid UTF-8 encoding.",
                    ) from None

                # Parse JSON
                try:
                    data = json.loads(text)
                except json.JSONDecodeError:
                    raise ProviderError(
                        ProviderErrorCode.INVALID_RESPONSE,
                        "Response payload is not valid JSON.",
                    ) from None

                if not isinstance(data, (dict, list)):
                    raise ProviderError(
                        ProviderErrorCode.INVALID_RESPONSE,
                        "Response payload root must be a JSON object or array.",
                    )

                return data

        except ProviderError:
            # Re-raise already mapped ProviderErrors (e.g. 429, 403, 5xx after retries)
            raise
        except (httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout):
            if attempts < max_attempts:
                continue
            raise ProviderError(
                ProviderErrorCode.TIMEOUT,
                f"Provider request timed out after {timeout} seconds.",
            ) from None
        except (httpx.NetworkError, httpx.ConnectError, httpx.RequestError):
            if attempts < max_attempts:
                continue
            raise ProviderError(
                ProviderErrorCode.PROVIDER_UNAVAILABLE,
                "Provider network connection failed.",
            ) from None
