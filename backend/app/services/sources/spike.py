"""ThreatLens Hour-1 API Spike Script.

Owner: Person 3 (Discovery & Connectors, branch: feat/discovery)
Reference: Contract Section 5.5, 5.6, 13.1, 13.2, 13.4, Appendix A

Runnable with `python -m app.services.sources.spike` from `backend/`.
Uses httpx only, User-Agent 'ThreatLens/3.0 hackathon prototype', 8s timeout,
and enforces >= 3.0s between Apple API calls. Must NOT be imported by any other module.
"""

from __future__ import annotations

import asyncio
import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import httpx

REPO_ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = REPO_ROOT / "backend" / "tests" / "fixtures"

USER_AGENT = "ThreatLens/3.0 hackathon prototype"
TIMEOUT_SECONDS = 8.0
APPLE_MIN_INTERVAL_S = 3.1


class SpikeRunner:
    def __init__(self) -> None:
        self.fixtures_dir = FIXTURES_DIR
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)
        self.last_apple_call_time = 0.0
        self.records: list[dict[str, Any]] = []

    async def _throttle_apple(self) -> None:
        elapsed = time.monotonic() - self.last_apple_call_time
        if elapsed < APPLE_MIN_INTERVAL_S:
            await asyncio.sleep(APPLE_MIN_INTERVAL_S - elapsed)
        self.last_apple_call_time = time.monotonic()

    async def run(self) -> dict[str, Any]:
        headers = {"User-Agent": USER_AGENT}
        transport = httpx.AsyncHTTPTransport(retries=0)
        limits = httpx.Limits(max_keepalive_connections=5, max_connections=10)

        async with httpx.AsyncClient(
            headers=headers,
            timeout=httpx.Timeout(TIMEOUT_SECONDS),
            transport=transport,
            limits=limits,
        ) as client:
            print("=" * 70)
            print("ThreatLens Hour-1 API Spike (Section 13.4)")
            print("=" * 70)

            # -------------------------------------------------------------
            # Call 1: Apple Search for "kaveri bank"
            # -------------------------------------------------------------
            await self._throttle_apple()
            url_apple_search = "https://itunes.apple.com/search?term=kaveri+bank&entity=software&country=in&limit=10"
            print(f"\n[1] Calling: {url_apple_search}")
            t0 = time.perf_counter()
            resp1 = await client.get(url_apple_search)
            lat1_ms = int((time.perf_counter() - t0) * 1000)
            data1 = resp1.json() if resp1.status_code == 200 else {}
            (self.fixtures_dir / "apple_search_kaveri_bank.json").write_text(
                json.dumps(data1, indent=2), encoding="utf-8"
            )
            rec1 = self._record_call(
                name="apple_search_kaveri_bank",
                url=url_apple_search,
                resp=resp1,
                lat_ms=lat1_ms,
                data=data1,
                items_key="results",
            )
            self.records.append(rec1)
            print(
                f"    Status: {resp1.status_code} | Latency: {lat1_ms}ms | Items: {data1.get('resultCount', 0)}"
            )

            # Also perform positive Apple search if call 1 returned 0 items
            sample_bundle_id = "com.google.chrome.ios"
            apple_positive_item: dict[str, Any] | None = None
            if data1.get("resultCount", 0) > 0:
                apple_positive_item = data1["results"][0]
                sample_bundle_id = (
                    apple_positive_item.get("bundleId") or sample_bundle_id
                )
            else:
                await self._throttle_apple()
                url_apple_sample = "https://itunes.apple.com/search?term=bank&entity=software&country=in&limit=5"
                print(
                    f"    [Helper] Searching term 'bank' to inspect real positive Apple fields: {url_apple_sample}"
                )
                t0 = time.perf_counter()
                resp1_sample = await client.get(url_apple_sample)
                lat_s_ms = int((time.perf_counter() - t0) * 1000)
                if resp1_sample.status_code == 200:
                    sample_data = resp1_sample.json()
                    (self.fixtures_dir / "apple_search_bank_sample.json").write_text(
                        json.dumps(sample_data, indent=2), encoding="utf-8"
                    )
                    if sample_data.get("results"):
                        apple_positive_item = sample_data["results"][0]
                        sample_bundle_id = (
                            apple_positive_item.get("bundleId") or sample_bundle_id
                        )
                    rec1_sample = self._record_call(
                        name="apple_search_bank_sample",
                        url=url_apple_sample,
                        resp=resp1_sample,
                        lat_ms=lat_s_ms,
                        data=sample_data,
                        items_key="results",
                    )
                    self.records.append(rec1_sample)

            # -------------------------------------------------------------
            # Call 2: Apple Lookup by bundleId
            # -------------------------------------------------------------
            await self._throttle_apple()
            url_apple_lookup = f"https://itunes.apple.com/lookup?bundleId={sample_bundle_id}&country=in"
            print(f"\n[2] Calling: {url_apple_lookup}")
            t0 = time.perf_counter()
            resp2 = await client.get(url_apple_lookup)
            lat2_ms = int((time.perf_counter() - t0) * 1000)
            data2 = resp2.json() if resp2.status_code == 200 else {}
            (self.fixtures_dir / "apple_lookup_bundle.json").write_text(
                json.dumps(data2, indent=2), encoding="utf-8"
            )
            rec2 = self._record_call(
                name="apple_lookup_bundle",
                url=url_apple_lookup,
                resp=resp2,
                lat_ms=lat2_ms,
                data=data2,
                items_key="results",
            )
            self.records.append(rec2)
            print(
                f"    Status: {resp2.status_code} | Latency: {lat2_ms}ms | Items: {data2.get('resultCount', 0)}"
            )

            # -------------------------------------------------------------
            # Call 2b & 2c: Legitimate empty search & lookup
            # -------------------------------------------------------------
            await self._throttle_apple()
            url_empty_search = "https://itunes.apple.com/search?term=xyznonexistentterm99999&entity=software&country=in&limit=5"
            print(f"\n[2b] Calling empty search: {url_empty_search}")
            t0 = time.perf_counter()
            resp_empty_search = await client.get(url_empty_search)
            lat_es_ms = int((time.perf_counter() - t0) * 1000)
            data_es = (
                resp_empty_search.json() if resp_empty_search.status_code == 200 else {}
            )
            (self.fixtures_dir / "apple_search_empty.json").write_text(
                json.dumps(data_es, indent=2), encoding="utf-8"
            )
            rec_es = self._record_call(
                name="apple_search_empty",
                url=url_empty_search,
                resp=resp_empty_search,
                lat_ms=lat_es_ms,
                data=data_es,
                items_key="results",
            )
            self.records.append(rec_es)

            await self._throttle_apple()
            url_empty_lookup = (
                "https://itunes.apple.com/lookup?id=999999999999999&country=in"
            )
            print(f"[2c] Calling empty lookup: {url_empty_lookup}")
            t0 = time.perf_counter()
            resp_empty_lookup = await client.get(url_empty_lookup)
            lat_el_ms = int((time.perf_counter() - t0) * 1000)
            data_el = (
                resp_empty_lookup.json() if resp_empty_lookup.status_code == 200 else {}
            )
            (self.fixtures_dir / "apple_lookup_empty.json").write_text(
                json.dumps(data_el, indent=2), encoding="utf-8"
            )
            rec_el = self._record_call(
                name="apple_lookup_empty",
                url=url_empty_lookup,
                resp=resp_empty_lookup,
                lat_ms=lat_el_ms,
                data=data_el,
                items_key="results",
            )
            self.records.append(rec_el)

            # -------------------------------------------------------------
            # Call 3: Bluesky searchActors
            # -------------------------------------------------------------
            url_bsky_search = "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors?q=bank&limit=5"
            print(f"\n[3] Calling: {url_bsky_search}")
            t0 = time.perf_counter()
            resp3 = await client.get(url_bsky_search)
            lat3_ms = int((time.perf_counter() - t0) * 1000)
            data3 = resp3.json() if resp3.status_code == 200 else {}
            (self.fixtures_dir / "bsky_search_actors_bank.json").write_text(
                json.dumps(data3, indent=2), encoding="utf-8"
            )
            rec3 = self._record_call(
                name="bsky_search_actors_bank",
                url=url_bsky_search,
                resp=resp3,
                lat_ms=lat3_ms,
                data=data3,
                items_key="actors",
            )
            self.records.append(rec3)
            print(
                f"    Status: {resp3.status_code} | Latency: {lat3_ms}ms | Actors: {len(data3.get('actors', []))}"
            )

            # Collect DIDs for getProfiles
            collected_dids: list[str] = [
                a["did"]
                for a in data3.get("actors", [])
                if isinstance(a, dict) and "did" in a
            ]

            # Test max limit accepted by searchActors (e.g. limit=100)
            url_bsky_max = "https://public.api.bsky.app/xrpc/app.bsky.actor.searchActors?q=bank&limit=100"
            resp3_max = await client.get(url_bsky_max)
            bsky_max_limit_accepted = resp3_max.status_code == 200

            # -------------------------------------------------------------
            # Call 3b: Bluesky getProfiles batch
            # -------------------------------------------------------------
            batch_dids = collected_dids or ["did:plc:5klap434eteydsxvdydtqkf2"]
            query_params = [("actors", did) for did in batch_dids]
            url_bsky_profiles = (
                "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles?"
                + "&".join(f"actors={did}" for did in batch_dids)
            )
            print(
                f"\n[3b] Calling getProfiles with repeated actors: {url_bsky_profiles}"
            )
            t0 = time.perf_counter()
            resp_prof = await client.get(
                "https://public.api.bsky.app/xrpc/app.bsky.actor.getProfiles",
                params=query_params,
            )
            lat_p_ms = int((time.perf_counter() - t0) * 1000)
            data_prof = resp_prof.json() if resp_prof.status_code == 200 else {}
            (self.fixtures_dir / "bsky_get_profiles.json").write_text(
                json.dumps(data_prof, indent=2), encoding="utf-8"
            )
            rec_prof = self._record_call(
                name="bsky_get_profiles",
                url=url_bsky_profiles,
                resp=resp_prof,
                lat_ms=lat_p_ms,
                data=data_prof,
                items_key="profiles",
            )
            self.records.append(rec_prof)
            print(
                f"    Status: {resp_prof.status_code} | Latency: {lat_p_ms}ms | Profiles: {len(data_prof.get('profiles', []))}"
            )

            # -------------------------------------------------------------
            # Call 4: searchPosts on public.api.bsky.app and api.bsky.app
            # -------------------------------------------------------------
            url_posts_public = "https://public.api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=bank&limit=5"
            print(f"\n[4a] Calling public searchPosts: {url_posts_public}")
            t0 = time.perf_counter()
            resp4_pub = await client.get(url_posts_public)
            lat4_pub_ms = int((time.perf_counter() - t0) * 1000)
            try:
                body4_pub: Any = resp4_pub.json()
            except (json.JSONDecodeError, ValueError):
                body4_pub = resp4_pub.text

            # Save in small envelope
            envelope4 = {
                "target": "public.api.bsky.app",
                "status_code": resp4_pub.status_code,
                "headers": dict(resp4_pub.headers),
                "body": body4_pub,
            }
            (self.fixtures_dir / "bsky_search_posts_403.json").write_text(
                json.dumps(envelope4, indent=2), encoding="utf-8"
            )
            rec4_pub = self._record_call(
                name="bsky_search_posts_public",
                url=url_posts_public,
                resp=resp4_pub,
                lat_ms=lat4_pub_ms,
                data=body4_pub if isinstance(body4_pub, dict) else {},
                items_key="",
            )
            self.records.append(rec4_pub)
            print(f"    Status: {resp4_pub.status_code} | Latency: {lat4_pub_ms}ms")

            url_posts_api = (
                "https://api.bsky.app/xrpc/app.bsky.feed.searchPosts?q=bank&limit=5"
            )
            print(f"[4b] Calling api.bsky.app searchPosts: {url_posts_api}")
            t0 = time.perf_counter()
            try:
                resp4_api = await client.get(url_posts_api)
                lat4_api_ms = int((time.perf_counter() - t0) * 1000)
                status_api = resp4_api.status_code
                try:
                    body4_api: Any = resp4_api.json()
                except (json.JSONDecodeError, ValueError):
                    body4_api = resp4_api.text
            except httpx.HTTPError as e:
                lat4_api_ms = int((time.perf_counter() - t0) * 1000)
                status_api = 0
                body4_api = f"Error: {e}"

            rec4_api = {
                "name": "bsky_search_posts_direct",
                "url": url_posts_api,
                "status": status_api,
                "latency_ms": lat4_api_ms,
                "content_type": "n/a",
                "size_bytes": len(str(body4_api)),
                "top_level_keys": [],
                "item_fields": [],
                "rate_limit_headers": {},
            }
            self.records.append(rec4_api)
            print(f"    Status: {status_api} | Latency: {lat4_api_ms}ms")

            # -------------------------------------------------------------
            # Call 5: Collect and verify icon/avatar hostnames
            # -------------------------------------------------------------
            print("\n[5] Collecting and inspecting artwork/avatar URLs...")
            observed_artwork_urls: list[str] = []
            observed_avatar_urls: list[str] = []

            if apple_positive_item:
                for key in ("artworkUrl512", "artworkUrl100", "artworkUrl60"):
                    val = apple_positive_item.get(key)
                    if val and isinstance(val, str):
                        observed_artwork_urls.append(val)

            for act in data3.get("actors", []):
                av = act.get("avatar")
                if av and isinstance(av, str):
                    observed_avatar_urls.append(av)

            image_checks: list[dict[str, Any]] = []
            for img_url in observed_artwork_urls[:2] + observed_avatar_urls[:2]:
                parsed = urlparse(img_url)
                t0 = time.perf_counter()
                try:
                    img_resp = await client.get(img_url)
                    img_lat_ms = int((time.perf_counter() - t0) * 1000)
                    image_checks.append(
                        {
                            "url": img_url,
                            "host": parsed.netloc,
                            "status": img_resp.status_code,
                            "content_type": img_resp.headers.get("content-type", ""),
                            "content_length": len(img_resp.content),
                            "latency_ms": img_lat_ms,
                        }
                    )
                    print(
                        f"    Image: {parsed.netloc} | Status: {img_resp.status_code} "
                        f"| Type: {img_resp.headers.get('content-type')} | Size: {len(img_resp.content)} bytes"
                    )
                except httpx.HTTPError as e:
                    image_checks.append(
                        {
                            "url": img_url,
                            "host": parsed.netloc,
                            "status": 0,
                            "error": str(e),
                        }
                    )

            # Check self-labels in Bluesky actors
            self_labels_observed: list[dict[str, Any]] = []
            for act in data3.get("actors", []):
                lbls = act.get("labels", [])
                if lbls:
                    self_labels_observed.append(
                        {"handle": act.get("handle"), "labels": lbls}
                    )

            summary = {
                "records": self.records,
                "apple_positive_item": apple_positive_item,
                "sample_bundle_id": sample_bundle_id,
                "bsky_max_limit_accepted": bsky_max_limit_accepted,
                "image_checks": image_checks,
                "self_labels_observed": self_labels_observed,
            }

            self._print_summary_table()
            return summary

    def _record_call(
        self,
        name: str,
        url: str,
        resp: httpx.Response,
        lat_ms: int,
        data: dict[str, Any],
        items_key: str,
    ) -> dict[str, Any]:
        top_keys = list(data.keys()) if isinstance(data, dict) else []
        item_fields: list[str] = []
        if (
            items_key
            and isinstance(data, dict)
            and isinstance(data.get(items_key), list)
        ):
            items_list = data[items_key]
            if items_list and isinstance(items_list[0], dict):
                item_fields = sorted(items_list[0].keys())

        rl_headers: dict[str, str] = {}
        for h, v in resp.headers.items():
            hl = h.lower()
            if "ratelimit" in hl or "retry-after" in hl or "quota" in hl:
                rl_headers[h] = v

        return {
            "name": name,
            "url": url,
            "status": resp.status_code,
            "latency_ms": lat_ms,
            "content_type": resp.headers.get("content-type", ""),
            "size_bytes": len(resp.content),
            "top_level_keys": top_keys,
            "item_fields": item_fields,
            "rate_limit_headers": rl_headers,
        }

    def _print_summary_table(self) -> None:
        print("\n" + "=" * 90)
        print(
            f"{'Target Name':<28} | {'Status':<6} | {'Latency':<8} | {'Size':<8} | {'RateLimit Headers'}"
        )
        print("-" * 90)
        for r in self.records:
            rl_str = (
                ", ".join(f"{k}: {v}" for k, v in r["rate_limit_headers"].items())
                or "None observed"
            )
            print(
                f"{r['name']:<28} | {r['status']:<6} | {str(r['latency_ms']) + 'ms':<8} | "
                f"{str(r['size_bytes']) + 'B':<8} | {rl_str}"
            )
        print("=" * 90)


async def main() -> int:
    runner = SpikeRunner()
    await runner.run()
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
