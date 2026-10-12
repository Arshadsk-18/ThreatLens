"""Sources and connectors package for ThreatLens.

Owner: Person 3 (backend/app/services/sources/**)
"""

from __future__ import annotations

try:
    import app.schemas  # type: ignore # noqa: F401
except ImportError:
    try:
        import importlib.util
        from pathlib import Path

        conftest_file = Path(__file__).resolve().parent / "tests" / "conftest.py"
        if conftest_file.exists():
            spec = importlib.util.spec_from_file_location(
                "_sources_conftest_bootstrap", conftest_file
            )
            if spec and spec.loader:
                boot_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(boot_mod)
    except Exception:  # noqa: BLE001, S110
        pass


from .base import SourceAdapter
from .errors import ProviderError
from .http import request_json
from .outcome import build_result, should_abort_remaining_queries
from .ratelimit import APPLE_LIMITER, BLUESKY_LIMITER, AsyncRateLimiter
from .text import extract_links, sanitize_text

try:
    from .apple import AppleItunesAdapter, AppleSourceAdapter
    from .bluesky import BlueskyPublicAdapter, BlueskySourceAdapter
    from .cache import (
        CachedResponse,
        CacheRepo,
        InMemoryCacheFake,
        InMemoryCacheRepo,
        make_cache_key,
    )
    from .demo import DemoFixtureAdapter, RecordedFixtureAdapter
    from .errors import BlockedUrlError
    from .fixtures_demo import DemoFixtureAdapter as DemoAdapter
    from .fixtures_recorded import RecordedFixtureAdapter as RecordedAdapter
    from .not_connected import NotConnectedAdapter
    from .prefill import (
        PrefillRef,
        PrefillResult,
        lookup_for_prefill,
        parse_prefill_input,
    )
    from .registry import (
        DEMO_ONLY_SOURCES,
        FIXED_SOURCE_IDS,
        assert_not_demo_only,
        get_adapter,
        is_demo_only,
        list_adapters,
        refresh_status,
        source_catalog,
    )

    __all__ = [
        "APPLE_LIMITER",
        "BLUESKY_LIMITER",
        "DEMO_ONLY_SOURCES",
        "FIXED_SOURCE_IDS",
        "AppleItunesAdapter",
        "AppleSourceAdapter",
        "AsyncRateLimiter",
        "BlockedUrlError",
        "BlueskyPublicAdapter",
        "BlueskySourceAdapter",
        "CacheRepo",
        "CachedResponse",
        "DemoAdapter",
        "DemoFixtureAdapter",
        "InMemoryCacheFake",
        "InMemoryCacheRepo",
        "NotConnectedAdapter",
        "PrefillRef",
        "PrefillResult",
        "ProviderError",
        "RecordedAdapter",
        "RecordedFixtureAdapter",
        "SourceAdapter",
        "assert_not_demo_only",
        "build_result",
        "extract_links",
        "get_adapter",
        "is_demo_only",
        "list_adapters",
        "lookup_for_prefill",
        "make_cache_key",
        "parse_prefill_input",
        "refresh_status",
        "request_json",
        "sanitize_text",
        "should_abort_remaining_queries",
        "source_catalog",
    ]
except ImportError:
    # Allows spike script and submodules to be executed directly before Person 2 lands app.schemas
    __all__ = [
        "APPLE_LIMITER",
        "BLUESKY_LIMITER",
        "AsyncRateLimiter",
        "ProviderError",
        "SourceAdapter",
        "build_result",
        "extract_links",
        "request_json",
        "sanitize_text",
        "should_abort_remaining_queries",
    ]
