"""Prefill URL parser and validator for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 5.6, 11.3
"""

import re
from urllib.parse import urlparse

from app.core.errors import ValidationException
from app.schemas.error import ErrorDetail

APPLE_URL_PATTERN = re.compile(r"^/([a-zA-Z]{2})/app/([^/]+)/id(\d+)$")
BLUESKY_URL_PATTERN = re.compile(r"^/profile/([^/?#]+)$")


class ParsedPrefillTarget:
    """Parsed prefill target containing target platform and identifier."""

    def __init__(self, platform: str, identifier: str) -> None:
        self.platform = platform
        self.identifier = identifier


def parse_and_validate_prefill(
    url: str | None = None,
    platform: str | None = None,
    identifier: str | None = None,
) -> ParsedPrefillTarget:
    """Parse and allowlist prefill input. Never fetches user-supplied URLs.

    Allowed URL patterns:
    - apps.apple.com/<cc>/app/<slug>/id<digits>
    - bsky.app/profile/<handle-or-did>

    Returns ParsedPrefillTarget with extracted platform and identifier.
    Raises ValidationException with BLOCKED_URL issue on unlisted/disallowed URLs.
    """
    if url:
        parsed = urlparse(url)
        netloc = parsed.netloc.lower()
        # Remove default ports if present
        if ":" in netloc:
            netloc = netloc.split(":")[0]

        # 1. Apple App Store
        if netloc == "apps.apple.com" or netloc.endswith(".apps.apple.com"):
            match = APPLE_URL_PATTERN.match(parsed.path)
            if match:
                # Group 3 is digits (id<digits>)
                track_id = match.group(3)
                return ParsedPrefillTarget(
                    platform="apple_app_store", identifier=track_id
                )

        # 2. Bluesky
        elif netloc == "bsky.app" or netloc.endswith(".bsky.app"):
            match = BLUESKY_URL_PATTERN.match(parsed.path)
            if match:
                handle_or_did = match.group(1)
                return ParsedPrefillTarget(platform="bluesky", identifier=handle_or_did)

        # All other URLs are blocked
        raise ValidationException(
            message="Invalid prefill URL.",
            details=[
                ErrorDetail(
                    field="url",
                    issue="BLOCKED_URL: Allowed patterns are apps.apple.com/<cc>/app/<slug>/id<digits> and bsky.app/profile/<handle-or-did>",
                )
            ],
        )

    if platform and identifier:
        plat = platform.strip().lower()
        ident = identifier.strip()
        if plat not in {
            "apple_app_store",
            "bluesky",
            "google_play",
            "instagram",
            "x",
            "facebook",
        }:
            raise ValidationException(
                message="Unsupported platform.",
                details=[
                    ErrorDetail(
                        field="platform", issue=f"Platform '{plat}' is not supported."
                    )
                ],
            )
        if not ident:
            raise ValidationException(
                message="Identifier cannot be empty.",
                details=[
                    ErrorDetail(
                        field="identifier", issue="Identifier must not be empty."
                    )
                ],
            )
        return ParsedPrefillTarget(platform=plat, identifier=ident)

    raise ValidationException(
        message="Invalid prefill request.",
        details=[
            ErrorDetail(
                field="request",
                issue="Must provide either 'url' or both 'platform' and 'identifier'.",
            )
        ],
    )


def validate_stable_identifier(platform: str, identifier: str) -> None:
    """Validate stable identifier syntax per platform rules in Section 11.3."""
    if platform == "apple_app_store":
        if not identifier.isdigit():
            raise ValidationException(
                message="Invalid stable identifier.",
                details=[
                    ErrorDetail(
                        field="stable_identifier",
                        issue="Must be numeric for apple_app_store",
                    )
                ],
            )
    elif platform == "google_play":
        package_regex = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*(\.[a-zA-Z][a-zA-Z0-9_]*)+$")
        if not package_regex.match(identifier):
            raise ValidationException(
                message="Invalid stable identifier.",
                details=[
                    ErrorDetail(
                        field="stable_identifier",
                        issue="Must be a valid package name for google_play (e.g. com.example.app)",
                    )
                ],
            )
    elif platform == "bluesky" and not identifier.startswith("did:"):
        raise ValidationException(
            message="Invalid stable identifier.",
            details=[
                ErrorDetail(
                    field="stable_identifier",
                    issue="Must be a did: string for bluesky (e.g. did:plc:...)",
                )
            ],
        )
