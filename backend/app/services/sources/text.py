"""Text sanitization and link extraction helpers for source adapters.

Owner: Person 3 (backend/app/services/sources/text.py)
Reference: Contract Sections 8.1, 13.1, 13.2
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit, urlunsplit

URL_REGEX = re.compile(r"https?://[^\s<>\"']+", re.IGNORECASE)
TRAILING_PUNCTUATION = ".,;:!?'\")>]"


def sanitize_text(text: str | None, *, preserve_newlines: bool = True) -> str | None:
    """Sanitize strings by removing NUL and ASCII control characters.

    CRITICAL CONTRACT RULE:
    DO NOT Unicode-normalize (NFKC) or case-fold names here.
    Homoglyphs (such as Cyrillic 'і' U+0456) and character variants must reach
    Person 4's detection engine byte-for-byte to permit accurate HOMOGLYPH
    and LOOKALIKE technique classification.
    """
    if text is None:
        return None

    cleaned_chars: list[str] = []
    for ch in text:
        code = ord(ch)
        if code == 0:  # NUL
            continue
        if code < 32:
            if preserve_newlines and ch in ("\n", "\r", "\t"):
                cleaned_chars.append(ch)
            continue
        if code == 127:  # DEL
            continue
        cleaned_chars.append(ch)

    return "".join(cleaned_chars).strip()


def extract_links(text: str | None) -> list[str]:
    """Extract, normalize, and deduplicate HTTP/HTTPS links from free text.

    Rules:
    - HTTP and HTTPS URLs only.
    - Trailing punctuation trimmed (e.g. commas, periods, brackets).
    - Hostname converted to lowercase; path/query preserved.
    - Deduplicated in order of appearance.
    - Capped at maximum 10 links.
    - Each link capped at <= 300 characters.
    """
    if not text:
        return []

    links: list[str] = []
    seen: set[str] = set()

    for match in URL_REGEX.finditer(text):
        raw = match.group(0)
        # Trim trailing punctuation
        cleaned = raw.rstrip(TRAILING_PUNCTUATION)
        if not cleaned:
            continue

        try:
            parsed = urlsplit(cleaned)
            scheme = parsed.scheme.lower()
            if scheme not in ("http", "https"):
                continue

            # Drop links with credentials (e.g. user:pass@host)
            if parsed.username or parsed.password or "@" in parsed.netloc:
                continue

            host = parsed.netloc.lower()
            if not host:
                continue

            normalized_url = urlunsplit(
                (
                    scheme,
                    host,
                    parsed.path,
                    parsed.query,
                    parsed.fragment,
                )
            )

            if len(normalized_url) > 300:
                continue

            if normalized_url not in seen:
                seen.add(normalized_url)
                links.append(normalized_url)
                if len(links) >= 10:
                    break
        except (ValueError, TypeError):
            continue

    return links
