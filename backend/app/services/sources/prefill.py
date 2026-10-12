"""Prefill URL parser and safe lookup dispatcher.

Owner: Person 3 (backend/app/services/sources/prefill.py)
Reference: Contract Sections 5.6, 11.3, 12

Security Principle (Section 5.6 & 11.3):
The backend NEVER fetches user-supplied URLs. It PARSES the input against a strict
allowlist, extracts a canonical identifier, and queries the official provider APIs
(itunes.apple.com or public.api.bsky.app) exclusively via the adapters' lookup() methods.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime
from urllib.parse import urlsplit

from app.schemas import NormalizedCandidate, ProviderErrorCode, SourceMode

from .apple import AppleItunesAdapter
from .bluesky import BlueskyPublicAdapter
from .errors import BlockedUrlError, ProviderError

# Allowlisted hostnames (exact string equality only)
_ALLOWED_HOSTS = {"apps.apple.com", "bsky.app"}

# Strict URL path formats
# Apple: https://apps.apple.com/<cc>/app/<slug>/id<digits>
_APPLE_PATH_REGEX = re.compile(r"^/([a-z]{2})/app/([a-z0-9\-%._]+)/id(\d+)$")
# Bluesky: https://bsky.app/profile/<handle-or-did>
_BSKY_PATH_REGEX = re.compile(r"^/profile/([^/]+)$")

# Identifier patterns
_DID_REGEX = re.compile(r"^did:[a-z0-9]+:[a-zA-Z0-9._-]+$")
_HANDLE_REGEX = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)+$"
)
_APPLE_DIGITS_REGEX = re.compile(r"^\d+$")
_APPLE_BUNDLE_ID_REGEX = re.compile(r"^[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$")


@dataclass(frozen=True)
class PrefillRef:
    """Parsed and validated prefill reference carrying platform and extracted ID."""

    platform: str  # "apple_app_store" | "bluesky"
    identifier: str  # Apple: digits (trackId) or bundle_id; Bluesky: handle or did
    source_id: str  # "apple_itunes" | "bluesky_public"


@dataclass
class PrefillResult:
    """Safe result from prefill lookup, isolating provider errors for route handlers."""

    candidate: NormalizedCandidate | None
    source_id: str
    source_mode: SourceMode
    retrieved_at: datetime
    error_code: ProviderErrorCode | None = None
    error_message: str | None = None


def parse_prefill_input(
    url: str | None,
    platform: str | None,
    identifier: str | None,
) -> PrefillRef:
    """Parse user-supplied input against strict allowlist and extract canonical ID.

    Accepts:
    1. URL:
       - https://apps.apple.com/<cc>/app/<slug>/id<digits>
       - https://bsky.app/profile/<handle-or-did>
    2. (platform, identifier) pair:
       - ("bluesky", handle or did)
       - ("apple_app_store", digits or bundle id)

    Raises BlockedUrlError on any unrecognized host, scheme, syntax, or parameter violation.
    """
    if url is not None:
        if not isinstance(url, str):
            raise BlockedUrlError("URL must be a string")
        if "\n" in url or "\r" in url:
            raise BlockedUrlError(
                "Newline or carriage return injection detected in URL"
            )
        url_clean = url.strip()
        if not url_clean:
            raise BlockedUrlError("URL must not be empty")
        if len(url_clean) > 2000:
            raise BlockedUrlError("URL exceeds maximum length of 2000 characters")
        if "\\" in url_clean:
            raise BlockedUrlError("Backslashes are not permitted in URL")
        if "%2f" in url_clean.lower():
            raise BlockedUrlError("Encoded slashes are not permitted in URL")
        if not url_clean.startswith("https://"):
            raise BlockedUrlError("Scheme must be lowercase 'https://'")
        if "?" in url_clean or "#" in url_clean:
            raise BlockedUrlError(
                "URL query parameters and fragments are not permitted"
            )

        parsed = urlsplit(url_clean)

        # Exact scheme match
        if parsed.scheme != "https":
            raise BlockedUrlError("Scheme must be 'https'")

        # Netloc must exactly equal lowercased hostname (no ports, credentials, casing tricks)
        if parsed.netloc != parsed.hostname:
            raise BlockedUrlError(
                "URL authority contains ports, credentials, or invalid casing"
            )

        # Exact hostname match against allowlist (no substring or startswith checks)
        if parsed.hostname not in _ALLOWED_HOSTS:
            raise BlockedUrlError(
                f"Host '{parsed.hostname}' is not in the prefill allowlist"
            )

        if parsed.hostname == "apps.apple.com":
            match = _APPLE_PATH_REGEX.match(parsed.path)
            if not match:
                raise BlockedUrlError(
                    f"Path does not match Apple App Store URL format: {parsed.path}"
                )
            track_id = match.group(3)
            ref = PrefillRef(
                platform="apple_app_store",
                identifier=track_id,
                source_id="apple_itunes",
            )
        elif parsed.hostname == "bsky.app":
            match = _BSKY_PATH_REGEX.match(parsed.path)
            if not match:
                raise BlockedUrlError(
                    f"Path does not match Bluesky profile URL format: {parsed.path}"
                )
            raw_target = match.group(1)
            if " " in raw_target or "/" in raw_target:
                raise BlockedUrlError(f"Invalid Bluesky profile target: {raw_target}")

            if raw_target.startswith("did:"):
                if not _DID_REGEX.match(raw_target):
                    raise BlockedUrlError(f"Invalid Bluesky DID: {raw_target}")
            else:
                if not _HANDLE_REGEX.match(raw_target):
                    raise BlockedUrlError(f"Invalid Bluesky handle: {raw_target}")

            ref = PrefillRef(
                platform="bluesky",
                identifier=raw_target,
                source_id="bluesky_public",
            )
        else:
            raise BlockedUrlError(f"Unsupported host: {parsed.hostname}")

        # Check optional matching constraints if provided alongside URL
        if platform is not None and platform != ref.platform:
            raise BlockedUrlError(
                f"Supplied platform '{platform}' does not match URL platform '{ref.platform}'"
            )
        if identifier is not None and identifier != ref.identifier:
            raise BlockedUrlError("Supplied identifier does not match URL identifier")

        return ref

    # URL is None: validate (platform, identifier) pair
    if platform is None or identifier is None:
        raise BlockedUrlError(
            "Either 'url' or both 'platform' and 'identifier' must be provided"
        )

    if not isinstance(identifier, str):
        raise BlockedUrlError("Identifier must be a string")

    id_clean = identifier.strip()
    if not id_clean:
        raise BlockedUrlError("Identifier must not be empty")
    if (
        len(id_clean) > 2000
        or "\n" in id_clean
        or "\r" in id_clean
        or "\\" in id_clean
        or "/" in id_clean
        or " " in id_clean
    ):
        raise BlockedUrlError(
            "Identifier contains invalid characters or exceeds 2000 characters"
        )

    if platform == "bluesky":
        if id_clean.startswith("did:"):
            if not _DID_REGEX.match(id_clean):
                raise BlockedUrlError(f"Invalid Bluesky DID: {id_clean}")
        else:
            if not _HANDLE_REGEX.match(id_clean):
                raise BlockedUrlError(f"Invalid Bluesky handle: {id_clean}")
        return PrefillRef(
            platform="bluesky",
            identifier=id_clean,
            source_id="bluesky_public",
        )

    if platform == "apple_app_store":
        if _APPLE_DIGITS_REGEX.match(id_clean) or _APPLE_BUNDLE_ID_REGEX.match(
            id_clean
        ):
            return PrefillRef(
                platform="apple_app_store",
                identifier=id_clean,
                source_id="apple_itunes",
            )
        raise BlockedUrlError(
            f"Invalid Apple App Store identifier (must be digits or bundle id): {id_clean}"
        )

    raise BlockedUrlError(f"Unsupported platform: {platform}")


async def lookup_for_prefill(
    ref: PrefillRef,
    *,
    apple_adapter: AppleItunesAdapter | None = None,
    bluesky_adapter: BlueskyPublicAdapter | None = None,
) -> PrefillResult:
    """Safe prefill lookup dispatcher executing against official APIs.

    Dispatches solely using the extracted identifier to official adapters:
    - Apple: queries https://itunes.apple.com/lookup
    - Bluesky: queries https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles

    Catches ProviderError to return a sanitized PrefillResult with error_code
    and error_message, allowing Person 2's route to return draft=null + error_code.
    """
    now = datetime.now(UTC)

    if ref.platform == "apple_app_store" or ref.source_id == "apple_itunes":
        adapter = apple_adapter or AppleItunesAdapter()
        try:
            candidate = await adapter.lookup(ref.identifier)
            mode = candidate.source_mode if candidate else SourceMode.LIVE
            retrieved = candidate.retrieved_at if candidate else now
            return PrefillResult(
                candidate=candidate,
                source_id="apple_itunes",
                source_mode=mode,
                retrieved_at=retrieved,
            )
        except ProviderError as err:
            return PrefillResult(
                candidate=None,
                source_id="apple_itunes",
                source_mode=SourceMode.LIVE,
                retrieved_at=now,
                error_code=err.error_code,
                error_message=err.message,
            )

    if ref.platform == "bluesky" or ref.source_id == "bluesky_public":
        adapter = bluesky_adapter or BlueskyPublicAdapter()
        try:
            candidate = await adapter.lookup(ref.identifier)
            mode = candidate.source_mode if candidate else SourceMode.LIVE
            retrieved = candidate.retrieved_at if candidate else now
            return PrefillResult(
                candidate=candidate,
                source_id="bluesky_public",
                source_mode=mode,
                retrieved_at=retrieved,
            )
        except ProviderError as err:
            return PrefillResult(
                candidate=None,
                source_id="bluesky_public",
                source_mode=SourceMode.LIVE,
                retrieved_at=now,
                error_code=err.error_code,
                error_message=err.message,
            )

    raise BlockedUrlError(f"Unsupported prefill platform: {ref.platform}")


__all__ = [
    "BlockedUrlError",
    "PrefillRef",
    "PrefillResult",
    "lookup_for_prefill",
    "parse_prefill_input",
]
