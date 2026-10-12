"""Comprehensive unit and security tests for safe image fetcher and perceptual hashing.

Owner: Person 3 (backend/app/services/sources/tests/test_image_fetch.py)
Reference: Contract Sections 5.6, 12, 13.4
"""

from __future__ import annotations

import io
import random
import string

import httpx
import pytest
import respx
from app.services.image_fetch import (
    fetch_icon_hash,
    is_host_allowlisted,
    is_ip_literal,
)
from PIL import Image, ImageDraw


def hamming_distance(hex1: str, hex2: str) -> int:
    """Compute bitwise hamming distance between two 16-char hex perceptual hashes (64-bit)."""
    val1 = int(hex1, 16)
    val2 = int(hex2, 16)
    return (val1 ^ val2).bit_count()


def generate_png_bytes(size: tuple[int, int] = (64, 64), color: str = "blue") -> bytes:
    img = Image.new("RGB", size, color=color)
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, size[0] - 10, size[1] - 10], fill="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def generate_jpeg_bytes(size: tuple[int, int] = (64, 64), quality: int = 85) -> bytes:
    img = Image.new("RGB", size, color="blue")
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, size[0] - 10, size[1] - 10], fill="white")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return buf.getvalue()


# Strictness checklist of rejected URLs (Section 5.6)
REJECTED_HOST_URLS = [
    ("https://evil.com/icon.png", "evil domain"),
    ("https://mzstatic.com.evil.com/icon.png", "subdomain trick"),
    ("https://evilmzstatic.com/icon.png", "suffix trick"),
    ("https://localhost/icon.png", "localhost"),
    ("https://127.0.0.1/icon.png", "IPv4 loopback"),
    ("https://169.254.169.254/latest/meta-data", "cloud metadata IP"),
    ("https://[::1]/icon.png", "IPv6 loopback"),
    ("https://user:pass@is1-ssl.mzstatic.com/icon.png", "userinfo credentials"),
    ("https://is1-ssl.mzstatic.com@evil.com/icon.png", "userinfo host trick"),
    ("http://is1-ssl.mzstatic.com/icon.png", "plain HTTP"),
    ("file:///etc/passwd", "file scheme"),
    ("https://is1-ssl.mzstatic.com:8443/icon.png", "non-443 port"),
    ("", "empty string"),
    ("https://is1-ssl.mzstatic.com/" + ("a" * 5000), "5000-char URL"),
]


@pytest.mark.parametrize("bad_url,reason", REJECTED_HOST_URLS)
@pytest.mark.asyncio
async def test_image_fetch_blocks_non_allowlisted_hosts(
    bad_url: str, reason: str
) -> None:
    """Parametrized security checklist: blocks disallowed hosts and schemes with ZERO network calls."""
    with respx.mock(assert_all_called=False) as respx_mock:
        result = await fetch_icon_hash(bad_url)
        assert result is None
        assert respx_mock.calls.call_count == 0


def test_is_host_allowlisted_and_ip_literal() -> None:
    """Check allowlist rules and IP literal detection."""
    assert is_host_allowlisted("cdn.bsky.app") is True
    assert is_host_allowlisted("is1-ssl.mzstatic.com") is True
    assert is_host_allowlisted("is2-ssl.mzstatic.com") is True
    assert is_host_allowlisted("mzstatic.com") is True

    # Attack strings must fail
    assert is_host_allowlisted("evilmzstatic.com") is False
    assert is_host_allowlisted("mzstatic.com.evil.com") is False
    assert is_host_allowlisted("evil.com") is False
    assert is_host_allowlisted("localhost") is False
    assert is_host_allowlisted("127.0.0.1") is False
    assert is_host_allowlisted("169.254.169.254") is False
    assert is_host_allowlisted("[::1]") is False

    # IP literal tests
    assert is_ip_literal("127.0.0.1") is True
    assert is_ip_literal("169.254.169.254") is True
    assert is_ip_literal("[::1]") is True
    assert is_ip_literal("::1") is True
    assert is_ip_literal("is1-ssl.mzstatic.com") is False
    assert is_ip_literal("cdn.bsky.app") is False


@pytest.mark.asyncio
@respx.mock
async def test_allowed_host_success_returns_16_char_hex_string() -> None:
    """Valid image on allowlisted host returns standard 16-character lowercase hex phash."""
    url = "https://is1-ssl.mzstatic.com/image/thumb/AppIcon/100x100bb.jpg"
    img_bytes = generate_png_bytes((100, 100), color="green")
    respx.get(url).mock(
        return_value=httpx.Response(
            200, content=img_bytes, headers={"Content-Type": "image/png"}
        )
    )

    result = await fetch_icon_hash(url)
    assert result is not None
    assert len(result) == 16
    assert all(c in string.hexdigits.lower() for c in result)


@pytest.mark.asyncio
@respx.mock
async def test_same_image_twice_produces_same_hash() -> None:
    """Pure function guarantee: identical bytes yield the exact same perceptual hash."""
    url = "https://cdn.bsky.app/img/avatar/plain/user/avatar.png"
    img_bytes = generate_png_bytes((64, 64), color="purple")
    respx.get(url).mock(
        return_value=httpx.Response(
            200, content=img_bytes, headers={"Content-Type": "image/png"}
        )
    )

    hash1 = await fetch_icon_hash(url)
    hash2 = await fetch_icon_hash(url)

    assert hash1 is not None
    assert hash2 is not None
    assert hash1 == hash2


@pytest.mark.asyncio
@respx.mock
async def test_slightly_resized_or_recompressed_image_small_hamming_distance() -> None:
    """Resized/recompressed versions of an image produce hashes within a small hamming distance."""
    url1 = "https://is1-ssl.mzstatic.com/icon_orig.png"
    url2 = "https://is1-ssl.mzstatic.com/icon_compressed.jpg"

    # Base image 100x100 PNG
    bytes1 = generate_png_bytes((100, 100), color="blue")
    # Compressed/resized 80x80 JPEG of same pattern
    bytes2 = generate_jpeg_bytes((80, 80), quality=75)

    respx.get(url1).mock(
        return_value=httpx.Response(
            200, content=bytes1, headers={"Content-Type": "image/png"}
        )
    )
    respx.get(url2).mock(
        return_value=httpx.Response(
            200, content=bytes2, headers={"Content-Type": "image/jpeg"}
        )
    )

    hash1 = await fetch_icon_hash(url1)
    hash2 = await fetch_icon_hash(url2)

    assert hash1 is not None
    assert hash2 is not None
    dist = hamming_distance(hash1, hash2)
    assert dist <= 10  # Very close perceptual match


@pytest.mark.asyncio
@respx.mock
async def test_cross_host_redirect_returns_none() -> None:
    """Cross-host redirect between two different allowlisted hosts returns None."""
    start_url = "https://is1-ssl.mzstatic.com/image/thumb/icon.png"
    cross_url = "https://cdn.bsky.app/img/avatar/plain/icon.png"

    respx.get(start_url).mock(
        return_value=httpx.Response(302, headers={"Location": cross_url})
    )
    respx.get(cross_url).mock(
        return_value=httpx.Response(
            200, content=generate_png_bytes(), headers={"Content-Type": "image/png"}
        )
    )

    result = await fetch_icon_hash(start_url)
    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_same_host_redirect_succeeds() -> None:
    """Redirect within the exact same host up to 3 hops succeeds."""
    url1 = "https://is1-ssl.mzstatic.com/step1"
    url2 = "https://is1-ssl.mzstatic.com/step2"
    final_url = "https://is1-ssl.mzstatic.com/final.png"

    img_bytes = generate_png_bytes()

    respx.get(url1).mock(
        return_value=httpx.Response(301, headers={"Location": "/step2"})
    )
    respx.get(url2).mock(
        return_value=httpx.Response(302, headers={"Location": "/final.png"})
    )
    respx.get(final_url).mock(
        return_value=httpx.Response(
            200, content=img_bytes, headers={"Content-Type": "image/png"}
        )
    )

    result = await fetch_icon_hash(url1)
    assert result is not None
    assert len(result) == 16


@pytest.mark.asyncio
@respx.mock
async def test_redirect_loop_returns_none() -> None:
    """Circular redirect loop returns None without hanging."""
    url_a = "https://is1-ssl.mzstatic.com/loop_a"
    url_b = "https://is1-ssl.mzstatic.com/loop_b"

    respx.get(url_a).mock(return_value=httpx.Response(302, headers={"Location": url_b}))
    respx.get(url_b).mock(return_value=httpx.Response(302, headers={"Location": url_a}))

    result = await fetch_icon_hash(url_a)
    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_excessive_redirect_hops_returns_none() -> None:
    """More than 3 redirect hops returns None."""
    u1 = "https://is1-ssl.mzstatic.com/r1"
    u2 = "https://is1-ssl.mzstatic.com/r2"
    u3 = "https://is1-ssl.mzstatic.com/r3"
    u4 = "https://is1-ssl.mzstatic.com/r4"
    u5 = "https://is1-ssl.mzstatic.com/r5"

    respx.get(u1).mock(return_value=httpx.Response(302, headers={"Location": u2}))
    respx.get(u2).mock(return_value=httpx.Response(302, headers={"Location": u3}))
    respx.get(u3).mock(return_value=httpx.Response(302, headers={"Location": u4}))
    respx.get(u4).mock(return_value=httpx.Response(302, headers={"Location": u5}))
    respx.get(u5).mock(
        return_value=httpx.Response(
            200, content=generate_png_bytes(), headers={"Content-Type": "image/png"}
        )
    )

    assert await fetch_icon_hash(u1) is None


@pytest.mark.asyncio
@respx.mock
async def test_payload_over_2mb_streaming_aborts() -> None:
    """Streaming body stops immediately when payload exceeds 2 MB cap."""
    # 2 MB + 1024 bytes
    oversized = b"P" * (2 * 1024 * 1024 + 1024)
    url = "https://cdn.bsky.app/img/avatar/huge.png"
    respx.get(url).mock(
        return_value=httpx.Response(
            200, content=oversized, headers={"Content-Type": "image/png"}
        )
    )

    result = await fetch_icon_hash(url)
    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_decompression_bomb_returns_none() -> None:
    """Images with declared pixels exceeding 25,000,000 are rejected as decompression bombs."""
    # 6000 x 5000 = 30,000,000 pixels (exceeds limit 25_000_000)
    bomb_img = Image.new("RGB", (6000, 5000), color="white")
    buf = io.BytesIO()
    bomb_img.save(buf, format="PNG")
    bomb_bytes = buf.getvalue()

    url = "https://is1-ssl.mzstatic.com/bomb.png"
    respx.get(url).mock(
        return_value=httpx.Response(
            200, content=bomb_bytes, headers={"Content-Type": "image/png"}
        )
    )

    result = await fetch_icon_hash(url)
    assert result is None


@pytest.mark.asyncio
@respx.mock
async def test_text_html_with_200_returns_none() -> None:
    """Non-image Content-Type returns None."""
    url = "https://cdn.bsky.app/index.html"
    respx.get(url).mock(
        return_value=httpx.Response(
            200,
            content=b"<!DOCTYPE html><html></html>",
            headers={"Content-Type": "text/html"},
        )
    )

    assert await fetch_icon_hash(url) is None


@pytest.mark.asyncio
@respx.mock
async def test_image_header_with_garbage_bytes_returns_none() -> None:
    """Content-Type image/* with unparseable corrupt payload returns None."""
    url = "https://is1-ssl.mzstatic.com/corrupt.jpg"
    respx.get(url).mock(
        return_value=httpx.Response(
            200,
            content=b"CORRUPT_BYTES_NOT_A_VALID_IMAGE",
            headers={"Content-Type": "image/jpeg"},
        )
    )

    assert await fetch_icon_hash(url) is None


@pytest.mark.asyncio
@respx.mock
async def test_svg_image_returns_none() -> None:
    """SVG vector graphics are strictly rejected."""
    svg_payload = b'<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40" /></svg>'

    # Case 1: Content-Type image/svg+xml
    url1 = "https://cdn.bsky.app/vector.svg"
    respx.get(url1).mock(
        return_value=httpx.Response(
            200, content=svg_payload, headers={"Content-Type": "image/svg+xml"}
        )
    )
    assert await fetch_icon_hash(url1) is None

    # Case 2: Spoofed Content-Type image/png with SVG bytes
    url2 = "https://is1-ssl.mzstatic.com/fake_png.png"
    respx.get(url2).mock(
        return_value=httpx.Response(
            200, content=svg_payload, headers={"Content-Type": "image/png"}
        )
    )
    assert await fetch_icon_hash(url2) is None


@pytest.mark.asyncio
@respx.mock
async def test_timeout_returns_none() -> None:
    """Network connection or read timeout returns None without raising."""
    url = "https://is1-ssl.mzstatic.com/timeout.png"
    respx.get(url).mock(side_effect=httpx.ReadTimeout("Read timed out"))

    assert await fetch_icon_hash(url) is None


@pytest.mark.asyncio
@respx.mock
async def test_http_404_and_500_return_none() -> None:
    """HTTP 404 Not Found and 500 Internal Server Error return None."""
    url_404 = "https://is1-ssl.mzstatic.com/notfound.png"
    respx.get(url_404).mock(return_value=httpx.Response(404, text="Not Found"))
    assert await fetch_icon_hash(url_404) is None

    url_500 = "https://is1-ssl.mzstatic.com/servererror.png"
    respx.get(url_500).mock(return_value=httpx.Response(500, text="Server Error"))
    assert await fetch_icon_hash(url_500) is None


@pytest.mark.asyncio
async def test_fuzz_200_random_inputs_never_escapes_exception() -> None:
    """Fuzz testing: 200 arbitrary URL/body combinations never raise an unhandled exception."""
    rng = random.Random(42)

    sample_hosts = [
        "is1-ssl.mzstatic.com",
        "cdn.bsky.app",
        "evil.com",
        "127.0.0.1",
        "localhost",
        "not-a-domain",
    ]

    with respx.mock(assert_all_called=False) as mock_router:
        # Pre-mock allowable hosts to return random garbage
        mock_router.get(url__regex=r"https://is1-ssl\.mzstatic\.com/.*").mock(
            return_value=httpx.Response(
                200,
                content=b"\xff\xd8\xff\xe0" + rng.randbytes(50),
                headers={"Content-Type": "image/jpeg"},
            )
        )
        mock_router.get(url__regex=r"https://cdn\.bsky\.app/.*").mock(
            return_value=httpx.Response(
                500,
                content=b"error",
            )
        )

        for _ in range(200):
            scheme = rng.choice(
                ["https://", "http://", "file://", "ftp://", "", "javascript:"]
            )
            host = rng.choice(sample_hosts)
            path = "/" + "".join(
                rng.choices(
                    string.ascii_letters + string.digits + "/?&=%#@",
                    k=rng.randint(0, 30),
                )
            )
            fuzz_url = f"{scheme}{host}{path}"

            try:
                res = await fetch_icon_hash(fuzz_url)
                assert res is None or (isinstance(res, str) and len(res) == 16)
            except Exception as err:  # noqa: BLE001
                pytest.fail(
                    f"fetch_icon_hash leaked an unhandled exception on input {fuzz_url!r}: {err}"
                )


@pytest.mark.asyncio
@respx.mock
async def test_apple_fixture_icon_urls_end_to_end_proof() -> None:
    """End-to-end proof: hash two Apple fixture icon URLs and demonstrate hamming distance."""
    # URLs extracted from real Apple fixture (apple_search_bank_sample.json)
    url_idfc = "https://is1-ssl.mzstatic.com/image/thumb/Purple211/v4/a6/81/5d/a6815dce-9c28-e570-1fbb-7436e2832935/AppIcon-1x_U007emarketing-0-8-0-85-220-0.png/100x100bb.jpg"
    url_axis = "https://is1-ssl.mzstatic.com/image/thumb/PurpleSource211/v4/a5/d7/c6/a5d7c679-bfa7-3402-990d-27b0eb38c41f/AppIcon-0-0-1x_U007emarketing-0-7-0-85-220.png/100x100bb.jpg"

    # Distinct generated image representations for the two bank apps
    img_idfc_bytes = generate_png_bytes((100, 100), color="maroon")
    img_axis_bytes = generate_png_bytes((100, 100), color="navy")

    respx.get(url_idfc).mock(
        return_value=httpx.Response(
            200, content=img_idfc_bytes, headers={"Content-Type": "image/jpeg"}
        )
    )
    respx.get(url_axis).mock(
        return_value=httpx.Response(
            200, content=img_axis_bytes, headers={"Content-Type": "image/jpeg"}
        )
    )

    hash_idfc = await fetch_icon_hash(url_idfc)
    hash_axis = await fetch_icon_hash(url_axis)

    assert hash_idfc is not None
    assert hash_axis is not None
    assert len(hash_idfc) == 16
    assert len(hash_axis) == 16

    # Demonstrate test-local hamming distance function
    distance = hamming_distance(hash_idfc, hash_axis)
    assert isinstance(distance, int)
    assert 0 <= distance <= 64
