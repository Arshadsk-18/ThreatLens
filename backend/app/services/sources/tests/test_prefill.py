"""Tests for prefill URL parser, validation security checklist, and safe lookup dispatcher.

Owner: Person 3 (backend/app/services/sources/tests/test_prefill.py)
Reference: Contract Sections 5.6, 11.3, 12
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx
import pytest
import respx
from app.schemas import ProviderErrorCode, SourceMode
from app.services.sources.apple import AppleItunesAdapter
from app.services.sources.bluesky import BlueskyPublicAdapter
from app.services.sources.errors import BlockedUrlError
from app.services.sources.prefill import (
    PrefillRef,
    PrefillResult,
    lookup_for_prefill,
    parse_prefill_input,
)

FIXTURES_DIR = Path(__file__).resolve().parents[4] / "tests" / "fixtures"


def load_fixture(name: str) -> dict[str, Any]:
    with open(FIXTURES_DIR / name, "r", encoding="utf-8") as f:
        return json.load(f)


# Strictness checklist items (Contract 5.6 & Phase 5)
REJECTED_URLS = [
    # 1. http scheme
    ("http://apps.apple.com/in/app/kaveri-mobile-plus/id1456230489", "http scheme"),
    # 2. missing scheme
    ("apps.apple.com/in/app/kaveri-mobile-plus/id1456230489", "missing scheme"),
    # 3. uppercase scheme
    (
        "HTTPS://apps.apple.com/in/app/kaveri-mobile-plus/id1456230489",
        "uppercase scheme",
    ),
    # 4. uppercase host tricks
    ("https://APPS.APPLE.COM/in/app/kaveri-mobile-plus/id1456230489", "uppercase host"),
    # 5. userinfo spoofing
    (
        "https://apps.apple.com@evil.com/in/app/kaveri-mobile-plus/id1456230489",
        "userinfo evil.com",
    ),
    (
        "https://user:pass@apps.apple.com/in/app/kaveri-mobile-plus/id1456230489",
        "userinfo credentials",
    ),
    # 6. explicit port
    (
        "https://apps.apple.com:443/in/app/kaveri-mobile-plus/id1456230489",
        "explicit port 443",
    ),
    ("https://bsky.app:8080/profile/alice.bsky.social", "explicit port 8080"),
    # 7. domain suffix spoofing
    (
        "https://apps.apple.com.evil.com/in/app/kaveri-mobile-plus/id1456230489",
        "subdomain spoofing",
    ),
    # 8. path prefix spoofing
    (
        "https://evil.com/apps.apple.com/in/app/kaveri-mobile-plus/id1456230489",
        "path spoofing",
    ),
    # 9. itunes.apple.com (API host not in prefill allowlist for user URLs)
    ("https://itunes.apple.com/in/app/kaveri-mobile-plus/id1456230489", "itunes host"),
    # 10. trailing path junk
    (
        "https://apps.apple.com/in/app/kaveri-mobile-plus/id1456230489/extra",
        "trailing path",
    ),
    # 11. trailing query junk
    (
        "https://apps.apple.com/in/app/kaveri-mobile-plus/id1456230489?utm_source=track",
        "query parameters",
    ),
    # 12. fragments carrying URLs
    (
        "https://apps.apple.com/in/app/kaveri-mobile-plus/id1456230489#https://evil.com",
        "fragment carrying URL",
    ),
    # 13. backslashes
    (
        "https://apps.apple.com\\in\\app\\kaveri-mobile-plus\\id1456230489",
        "backslashes",
    ),
    # 14. encoded slashes (%2f)
    (
        "https://apps.apple.com/in%2fapp/kaveri-mobile-plus/id1456230489",
        "encoded slash %2f",
    ),
    (
        "https://apps.apple.com/in%2Fapp/kaveri-mobile-plus/id1456230489",
        "encoded slash %2F",
    ),
    # 15. unicode lookalike hosts (Cyrillic а: U+0430)
    (
        "https://\u0430pps.apple.com/in/app/kaveri-mobile-plus/id1456230489",
        "Cyrillic a homoglyph",
    ),
    # 16. IP literals
    ("https://192.168.1.1/profile/alice.bsky.social", "private IP literal"),
    # 17. localhost
    ("https://localhost/profile/alice.bsky.social", "localhost"),
    # 18. cloud metadata IP
    ("https://169.254.169.254/latest/meta-data", "metadata IP"),
    # 19. file:// and gopher:// schemes
    ("file:///etc/passwd", "file scheme"),
    ("gopher://gopher.floodgap.com", "gopher scheme"),
    # 20. newline and carriage return injection
    (
        "https://apps.apple.com/in/app/kaveri-mobile-plus/id1456230489\n",
        "newline injection",
    ),
    (
        "https://apps.apple.com/in/app/kaveri-mobile-plus/id1456230489\r\nevil",
        "CRLF injection",
    ),
    # 21. empty string and whitespace
    ("", "empty string"),
    ("   ", "whitespace string"),
    # 22. >2000 chars
    (
        "https://apps.apple.com/in/app/" + ("a" * 2000) + "/id1456230489",
        "excessive length >2000",
    ),
    # 23. id with letters
    (
        "https://apps.apple.com/in/app/kaveri-mobile-plus/id1456230489abc",
        "id with letters",
    ),
    # 24. did with illegal characters
    ("https://bsky.app/profile/did:plc:invalid!character", "did with exclamation mark"),
    ("https://bsky.app/profile/did:plc:invalid 123", "did with space"),
    # 25. handle with spaces or slashes
    ("https://bsky.app/profile/bad handle.bsky.social", "handle with space"),
    ("https://bsky.app/profile/bad/handle.bsky.social", "handle with slash"),
]


@pytest.mark.parametrize("bad_url,reason", REJECTED_URLS)
def test_prefill_rejects_unlisted_urls(bad_url: str, reason: str) -> None:
    """Parametrized security checklist: rejects malformed or unlisted URLs without network calls."""
    with respx.mock(assert_all_called=False) as respx_mock:
        with pytest.raises(BlockedUrlError) as exc_info:
            parse_prefill_input(url=bad_url, platform=None, identifier=None)

        assert exc_info.value.error_code == ProviderErrorCode.BLOCKED_URL
        assert isinstance(exc_info.value.message, str)
        assert len(exc_info.value.message) > 0
        # Assert zero network calls were made
        assert respx_mock.calls.call_count == 0


def test_prefill_rejects_invalid_platform_identifier_pairs() -> None:
    """Invalid (platform, identifier) pairs raise BlockedUrlError."""
    # Unsupported platform
    with pytest.raises(BlockedUrlError):
        parse_prefill_input(url=None, platform="twitter", identifier="jack")

    # Apple with letters (not bundle id, no dots)
    with pytest.raises(BlockedUrlError):
        parse_prefill_input(url=None, platform="apple_app_store", identifier="notanid")

    # Bluesky with spaces or slashes
    with pytest.raises(BlockedUrlError):
        parse_prefill_input(
            url=None, platform="bluesky", identifier="bad handle.bsky.social"
        )
    with pytest.raises(BlockedUrlError):
        parse_prefill_input(url=None, platform="bluesky", identifier="bad/handle")

    # Both url and platform/identifier missing
    with pytest.raises(BlockedUrlError):
        parse_prefill_input(url=None, platform=None, identifier=None)

    # Empty identifier
    with pytest.raises(BlockedUrlError):
        parse_prefill_input(url=None, platform="apple_app_store", identifier="")


def test_prefill_accepts_allowlisted_urls() -> None:
    """Accepts valid Apple App Store and Bluesky profile URLs and (platform, id) pairs."""
    # 1. Apple App Store standard URL
    ref1 = parse_prefill_input(
        url="https://apps.apple.com/in/app/kaveri-mobile-plus/id1456230489",
        platform=None,
        identifier=None,
    )
    assert ref1.platform == "apple_app_store"
    assert ref1.identifier == "1456230489"
    assert ref1.source_id == "apple_itunes"

    # 2. Apple App Store with special characters in slug
    ref2 = parse_prefill_input(
        url="https://apps.apple.com/us/app/google-chrome_app%20.web/id535886823",
        platform=None,
        identifier=None,
    )
    assert ref2.platform == "apple_app_store"
    assert ref2.identifier == "535886823"
    assert ref2.source_id == "apple_itunes"

    # 3. Bluesky handle URL
    ref3 = parse_prefill_input(
        url="https://bsky.app/profile/kaveribank.bsky.social",
        platform=None,
        identifier=None,
    )
    assert ref3.platform == "bluesky"
    assert ref3.identifier == "kaveribank.bsky.social"
    assert ref3.source_id == "bluesky_public"

    # 4. Bluesky DID URL
    ref4 = parse_prefill_input(
        url="https://bsky.app/profile/did:plc:z72i7hdynmk6r22z27h6tvur",
        platform=None,
        identifier=None,
    )
    assert ref4.platform == "bluesky"
    assert ref4.identifier == "did:plc:z72i7hdynmk6r22z27h6tvur"
    assert ref4.source_id == "bluesky_public"

    # 5. (platform, identifier) pair: Bluesky handle
    ref5 = parse_prefill_input(
        url=None,
        platform="bluesky",
        identifier="kaveribank.bsky.social",
    )
    assert ref5 == PrefillRef(
        platform="bluesky",
        identifier="kaveribank.bsky.social",
        source_id="bluesky_public",
    )

    # 6. (platform, identifier) pair: Bluesky DID
    ref6 = parse_prefill_input(
        url=None,
        platform="bluesky",
        identifier="did:plc:z72i7hdynmk6r22z27h6tvur",
    )
    assert ref6 == PrefillRef(
        platform="bluesky",
        identifier="did:plc:z72i7hdynmk6r22z27h6tvur",
        source_id="bluesky_public",
    )

    # 7. (platform, identifier) pair: Apple trackId
    ref7 = parse_prefill_input(
        url=None,
        platform="apple_app_store",
        identifier="1456230489",
    )
    assert ref7 == PrefillRef(
        platform="apple_app_store", identifier="1456230489", source_id="apple_itunes"
    )

    # 8. (platform, identifier) pair: Apple bundle ID
    ref8 = parse_prefill_input(
        url=None,
        platform="apple_app_store",
        identifier="com.kaveri.mobile",
    )
    assert ref8 == PrefillRef(
        platform="apple_app_store",
        identifier="com.kaveri.mobile",
        source_id="apple_itunes",
    )


@pytest.mark.asyncio
@respx.mock
async def test_prefill_apple_lookup_success() -> None:
    """Prefill lookup for Apple App Store fetches solely from itunes.apple.com."""
    fixture_data = load_fixture("apple_lookup_bundle.json")

    route = respx.get("https://itunes.apple.com/lookup").mock(
        return_value=httpx.Response(200, json=fixture_data)
    )

    ref = parse_prefill_input(
        url="https://apps.apple.com/in/app/idfc-first-bank/id1521443352",
        platform=None,
        identifier=None,
    )

    result = await lookup_for_prefill(ref)

    assert isinstance(result, PrefillResult)
    assert result.error_code is None
    assert result.error_message is None
    assert result.source_id == "apple_itunes"
    assert result.source_mode == SourceMode.LIVE
    assert result.candidate is not None
    assert result.candidate.display_name == "IDFC FIRST Bank: MobileBanking"
    assert result.candidate.stable_identifier == "1521443352"
    assert route.called
    assert route.calls.last.request.url.params["id"] == "1521443352"


@pytest.mark.asyncio
@respx.mock
async def test_prefill_bluesky_by_handle_and_did() -> None:
    """Prefill lookup for Bluesky by handle and DID queries public.api.bsky.app."""
    fixture_data = load_fixture("bsky_get_profiles.json")

    route = respx.get(
        "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles"
    ).mock(return_value=httpx.Response(200, json=fixture_data))

    # 1. Lookup by handle
    ref_handle = parse_prefill_input(
        url="https://bsky.app/profile/jillwine-banks.bsky.social",
        platform=None,
        identifier=None,
    )
    res_handle = await lookup_for_prefill(ref_handle)

    assert res_handle.error_code is None
    assert res_handle.candidate is not None
    assert res_handle.source_id == "bluesky_public"
    assert res_handle.candidate.stable_identifier == "did:plc:5klap434eteydsxvdydtqkf2"
    assert res_handle.candidate.display_name == "Jill Wine-Banks"

    # 2. Lookup by DID
    ref_did = parse_prefill_input(
        url=None,
        platform="bluesky",
        identifier="did:plc:5klap434eteydsxvdydtqkf2",
    )
    res_did = await lookup_for_prefill(ref_did)

    assert res_did.error_code is None
    assert res_did.candidate is not None
    assert res_did.candidate.stable_identifier == "did:plc:5klap434eteydsxvdydtqkf2"
    assert route.call_count >= 2


@pytest.mark.asyncio
@respx.mock
async def test_prefill_provider_failure_returns_error_not_exception_leak() -> None:
    """Provider failure returns a structured PrefillResult with error_code without leaking exceptions."""
    # Apple 500 server error
    respx.get("https://itunes.apple.com/lookup").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    ref_apple = parse_prefill_input(
        url="https://apps.apple.com/in/app/kaveri-mobile-plus/id1456230489",
        platform=None,
        identifier=None,
    )

    # Must NOT raise ProviderError or httpx.HTTPError
    result_apple = await lookup_for_prefill(ref_apple)

    assert result_apple.candidate is None
    assert result_apple.source_id == "apple_itunes"
    assert result_apple.error_code == ProviderErrorCode.PROVIDER_UNAVAILABLE
    assert result_apple.error_message is not None
    # Ensure sensitive URL parameters are never in the message
    assert "https://" not in result_apple.error_message

    # Bluesky 429 rate limit
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(429, text="Rate limit exceeded")
    )

    ref_bsky = parse_prefill_input(
        url="https://bsky.app/profile/alice.bsky.social",
        platform=None,
        identifier=None,
    )

    result_bsky = await lookup_for_prefill(ref_bsky)

    assert result_bsky.candidate is None
    assert result_bsky.source_id == "bluesky_public"
    assert result_bsky.error_code == ProviderErrorCode.RATE_LIMITED
    assert result_bsky.error_message is not None


@pytest.mark.asyncio
@respx.mock
async def test_prefill_not_found_is_none() -> None:
    """Clean 'not found' returns candidate=None and error_code=None."""
    # Apple empty results
    respx.get("https://itunes.apple.com/lookup").mock(
        return_value=httpx.Response(200, json={"resultCount": 0, "results": []})
    )

    ref_apple = parse_prefill_input(
        url="https://apps.apple.com/in/app/unknown-app/id999999999",
        platform=None,
        identifier=None,
    )

    result_apple = await lookup_for_prefill(ref_apple)

    assert result_apple.candidate is None
    assert result_apple.error_code is None
    assert result_apple.error_message is None
    assert result_apple.source_id == "apple_itunes"

    # Bluesky empty profiles
    respx.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
        return_value=httpx.Response(200, json={"profiles": []})
    )

    ref_bsky = parse_prefill_input(
        url="https://bsky.app/profile/unknown.bsky.social",
        platform=None,
        identifier=None,
    )

    result_bsky = await lookup_for_prefill(ref_bsky)

    assert result_bsky.candidate is None
    assert result_bsky.error_code is None
    assert result_bsky.error_message is None
    assert result_bsky.source_id == "bluesky_public"


@pytest.mark.asyncio
async def test_prefill_only_calls_official_hosts_never_arbitrary_urls() -> None:
    """Security verification: respx router fails on any unmocked host, verifying zero unauthorized network egress."""
    with respx.mock(assert_all_called=False) as router:
        # Mock only the two official endpoints
        router.get("https://itunes.apple.com/lookup").mock(
            return_value=httpx.Response(200, json={"resultCount": 0, "results": []})
        )
        router.get("https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles").mock(
            return_value=httpx.Response(200, json={"profiles": []})
        )

        # Run prefill through both adapters
        ref_apple = parse_prefill_input(
            url="https://apps.apple.com/in/app/test-app/id123456789",
            platform=None,
            identifier=None,
        )
        ref_bsky = parse_prefill_input(
            url="https://bsky.app/profile/test.bsky.social",
            platform=None,
            identifier=None,
        )

        apple_adapter = AppleItunesAdapter()
        bsky_adapter = BlueskyPublicAdapter()

        await lookup_for_prefill(ref_apple, apple_adapter=apple_adapter)
        await lookup_for_prefill(ref_bsky, bluesky_adapter=bsky_adapter)

        # Verify only official hostnames were contacted
        called_hosts = {call.request.url.host for call in router.calls}
        assert called_hosts.issubset({"itunes.apple.com", "public.api.bsky.app"})
        assert "apps.apple.com" not in called_hosts
        assert "bsky.app" not in called_hosts
