"""Hardening tests: Data-quality edge cases (Section D).

Owner: Person 3
Reference: Contract Sections 8.1, 13.1, 13.2, Phase 9 Hardening
"""

from __future__ import annotations

from uuid import uuid4

import httpx
import pytest
import respx
from app.schemas import PlannedQuery, QueryPlan
from app.services.sources.apple import (
    map_apple_item,
)
from app.services.sources.bluesky import (
    BlueskyPublicAdapter,
    is_self_labelled_no_unauth,
    map_bluesky_profile,
)
from app.services.sources.ratelimit import AsyncRateLimiter
from app.services.sources.text import extract_links, sanitize_text


class TestDataQualityEdgeCases:
    """Edge cases for text sanitization, link extraction, and data mapping."""

    def test_unicode_emoji_rtl_and_homoglyphs_preserved_byte_for_byte(self) -> None:
        # Cyrillic small 'і' (U+0456), Greek question mark, RTL Arabic, emoji, zero-width chars
        cyrillic_name = "Kaverі Bank"  # contains Cyrillic small 'і' U+0456
        assert ord(cyrillic_name[5]) == 0x0456
        sanitized = sanitize_text(cyrillic_name)
        assert sanitized == cyrillic_name
        assert ord(sanitized[5]) == 0x0456  # Byte-for-byte preserved

        # Emoji
        emoji_name = "Kaveri Bank 📱💰"
        assert sanitize_text(emoji_name) == emoji_name

        # RTL Arabic
        rtl_name = "بنك كافيري"
        assert sanitize_text(rtl_name) == rtl_name

        # Zero-width characters (\u200b ZWSP, \u200c ZWNJ, \u200d ZWJ, \ufeff BOM)
        zw_name = "Kav\u200beri\u200c Bank\u200d\ufeff"
        sanitized_zw = sanitize_text(zw_name)
        assert sanitized_zw == zw_name
        assert "\u200b" in sanitized_zw
        assert "\u200c" in sanitized_zw
        assert "\u200d" in sanitized_zw
        assert "\ufeff" in sanitized_zw

    def test_nul_and_ascii_control_chars_stripped(self) -> None:
        raw = "Kaveri\x00 Bank\x07\x1b\x7f"
        sanitized = sanitize_text(raw)
        assert sanitized == "Kaveri Bank"
        assert "\x00" not in sanitized
        assert "\x07" not in sanitized
        assert "\x1b" not in sanitized
        assert "\x7f" not in sanitized

    def test_links_with_credentials_and_javascript_schemes_dropped(self) -> None:
        # Credentials must be dropped
        text_with_creds = (
            "Check https://user:pass@evil.com/login and http://admin:secret@bank.com"
        )
        links = extract_links(text_with_creds)
        assert links == [], (
            f"Expected links with credentials to be dropped, got: {links}"
        )

        # JavaScript and other non-http/https schemes must be dropped
        text_with_js = (
            "Click javascript:alert(1) or data:text/html,evil or file:///etc/passwd"
        )
        assert extract_links(text_with_js) == []

        # Normal links preserved
        text_normal = (
            "Visit https://kaveribank.com and http://blog.kaveribank.com/news."
        )
        assert extract_links(text_normal) == [
            "https://kaveribank.com",
            "http://blog.kaveribank.com/news",
        ]

    def test_bio_with_50_links_capped_at_10(self) -> None:
        many_links_text = " ".join(f"https://site{i}.com/page" for i in range(50))
        extracted = extract_links(many_links_text)
        assert len(extracted) == 10
        assert extracted[0] == "https://site0.com/page"
        assert extracted[9] == "https://site9.com/page"

    def test_bluesky_links_cap_10_even_with_website_field(self) -> None:
        # Profile bio with 10 links + website field
        many_links = " ".join(f"https://bio{i}.com" for i in range(10))
        profile_data = {
            "did": "did:plc:test12345",
            "handle": "kaveri.bsky.social",
            "displayName": "Kaveri",
            "description": many_links,
            "website": "https://extra-website.com",
        }
        cand = map_bluesky_profile(profile_data)
        assert len(cand.external_links) <= 10
        assert len(cand.external_links) == 10

    def test_apple_item_missing_seller_null_artist_and_rating_count_as_string(
        self,
    ) -> None:
        item = {
            "trackId": 998877,
            "trackName": "Kaveri Mobile 📱",
            "bundleId": "com.kaveri.mobile",
            "sellerName": None,  # missing / null
            "artistId": None,  # null artistId
            "description": "Very long description " * 500,  # long description
            "primaryGenreName": "Finance",
            "userRatingCount": "4500",  # rating count as string!
            "releaseDate": "unexpected-date-format-not-iso",  # unexpected releaseDate
            "trackViewUrl": "https://apps.apple.com/in/app/kaveri/id998877",
            "artworkUrl512": "https://is1-ssl.mzstatic.com/image/thumb/icon512.png",
        }
        cand = map_apple_item(item)
        assert cand.stable_identifier == "998877"
        assert cand.display_name == "Kaveri Mobile 📱"
        assert cand.publisher_name is None
        assert cand.developer_id is None
        assert cand.created_at_source is None  # Handled unexpected format safely
        assert cand.rating_count == 4500  # Parsed from string cleanly!
        assert len(cand.description or "") > 5000

    def test_bluesky_no_display_name_and_invalid_handle_falls_back_to_did(self) -> None:
        profile_data = {
            "did": "did:plc:fallback123456",
            "handle": "handle.invalid",
            "displayName": "",  # empty
            "description": "",  # empty bio
        }
        cand = map_bluesky_profile(profile_data)
        assert cand.stable_identifier == "did:plc:fallback123456"
        assert cand.handle is None
        assert cand.display_name == "did:plc:fallback123456"  # falls back to DID
        assert cand.description is None
        assert cand.external_links == []

    def test_bluesky_bio_with_only_links(self) -> None:
        profile_data = {
            "did": "did:plc:links999",
            "handle": "links.bsky.social",
            "description": "https://link1.org https://link2.org",
        }
        cand = map_bluesky_profile(profile_data)
        assert cand.description == "https://link1.org https://link2.org"
        assert cand.external_links == ["https://link1.org", "https://link2.org"]

    def test_bluesky_unknown_label_shape_does_not_crash(self) -> None:
        # labels not a list, or containing malformed items
        item1 = {"did": "did:plc:1", "labels": "invalid_string_not_list"}
        assert is_self_labelled_no_unauth(item1) is False

        item2 = {"did": "did:plc:1", "labels": [{"unexpected_key": 42}, None, 123]}
        assert is_self_labelled_no_unauth(item2) is False

        item3 = {
            "did": "did:plc:1",
            "labels": [{"val": "!no-unauthenticated", "src": "did:plc:1"}],
        }
        assert is_self_labelled_no_unauth(item3) is True

    @pytest.mark.asyncio
    @respx.mock
    async def test_bluesky_did_disappears_between_discovery_and_enrichment(
        self,
    ) -> None:
        # Search returns 2 actors, but getProfiles only returns 1
        respx.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
        ).respond(
            200,
            json={
                "actors": [
                    {
                        "did": "did:plc:actor1",
                        "handle": "actor1.bsky.social",
                        "displayName": "Actor One",
                    },
                    {
                        "did": "did:plc:actor2",
                        "handle": "actor2.bsky.social",
                        "displayName": "Actor Two",
                    },
                ]
            },
        )
        respx.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles"
        ).respond(
            200,
            json={
                "profiles": [
                    {
                        "did": "did:plc:actor1",
                        "handle": "actor1.bsky.social",
                        "displayName": "Actor One Enriched",
                        "followersCount": 100,
                    }
                ]
            },
        )

        adapter = BlueskyPublicAdapter(rate_limiter=AsyncRateLimiter(0.0))
        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[PlannedQuery(term="actor", kind="EXACT", priority=1)],
        )
        res = await adapter.search(plan, limit=10)

        assert res.queries_executed == 1
        assert len(res.candidates) == 2
        cand_map = {c.stable_identifier: c for c in res.candidates}
        assert cand_map["did:plc:actor1"].display_name == "Actor One Enriched"
        assert cand_map["did:plc:actor1"].followers == 100
        # actor2 disappeared from getProfiles, so kept basic discovery candidate
        assert cand_map["did:plc:actor2"].display_name == "Actor Two"
        assert cand_map["did:plc:actor2"].followers is None

    @pytest.mark.asyncio
    @respx.mock
    async def test_bluesky_duplicate_dids_across_queries_tracked_in_order(self) -> None:
        # Query 1 returns actor1 and actor2. Query 2 returns actor2 and actor3.
        route = respx.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors"
        )
        route.side_effect = [
            httpx.Response(
                200,
                json={
                    "actors": [
                        {"did": "did:plc:a1", "handle": "a1.bsky.social"},
                        {"did": "did:plc:a2", "handle": "a2.bsky.social"},
                    ]
                },
            ),
            httpx.Response(
                200,
                json={
                    "actors": [
                        {"did": "did:plc:a2", "handle": "a2.bsky.social"},
                        {"did": "did:plc:a3", "handle": "a3.bsky.social"},
                    ]
                },
            ),
        ]
        respx.get(
            "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles"
        ).respond(
            200,
            json={
                "profiles": [
                    {"did": "did:plc:a1"},
                    {"did": "did:plc:a2"},
                    {"did": "did:plc:a3"},
                ]
            },
        )

        adapter = BlueskyPublicAdapter(rate_limiter=AsyncRateLimiter(0.0))
        plan = QueryPlan(
            brand_id=uuid4(),
            queries=[
                PlannedQuery(term="term_one", kind="EXACT", priority=1),
                PlannedQuery(term="term_two", kind="LOOKALIKE", priority=2),
            ],
        )
        res = await adapter.search(plan, limit=10)

        assert len(res.candidates) == 3
        cand_map = {c.stable_identifier: c for c in res.candidates}
        assert cand_map["did:plc:a1"].matched_queries == ["term_one"]
        assert cand_map["did:plc:a2"].matched_queries == ["term_one", "term_two"]
        assert cand_map["did:plc:a3"].matched_queries == ["term_two"]
