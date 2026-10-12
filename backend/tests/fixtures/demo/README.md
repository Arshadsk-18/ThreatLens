# ThreatLens DEMO Fixture Specification

**Owner:** Person 5 (SIMULATED dataset composition for Appendix B)  
**Consumer:** Person 3 (`DemoFixtureAdapter` in `app.services.sources.fixtures_demo`)  
**Reference:** Contract Section 5.3, 11.1, 12, Appendix B

---

## 1. Schema & File Format

Demo fixture files are stored under `backend/tests/fixtures/demo/*.json`. Every file must adhere to the following top-level structure:

```json
{
  "fixture_version": 1,
  "records": [
    {
      "candidate": {
        "source_id": "demo_fixtures",
        "platform": "apple_app_store",
        "asset_type": "IOS_APP",
        "stable_identifier": "demo-ios-001",
        "secondary_identifiers": {
          "bundle_id": "com.kaveribank.mobile"
        },
        "display_name": "Kaveri Bank Mobile",
        "handle": null,
        "publisher_name": "Kaveri Bank Ltd",
        "url": "https://apps.apple.com/in/app/kaveri-bank-mobile/id9990001",
        "icon_url": null,
        "icon_phash": null,
        "source_mode": "SIMULATED",
        "retrieved_at": "2026-10-12T12:00:00Z",
        "matched_queries": ["kaveri bank"]
      },
      "note": "Official cleared asset for Kaveri Bank"
    }
  ]
}
```

### Strict Rules:
1. **Source Mode:** Every record's `candidate.source_mode` MUST be `"SIMULATED"`. Any record claiming `"LIVE"` or `"CACHED"` will be rejected at load time with an error detailing the file and record index.
2. **NormalizedCandidate Fields:** Each candidate must satisfy the contract schema:
   - `source_id`: `"demo_fixtures"`
   - `platform`: e.g. `"apple_app_store"`, `"google_play"`, `"bluesky"`, `"instagram"`, `"x"`, `"facebook"`
   - `asset_type`: `"IOS_APP"`, `"ANDROID_APP"`, or `"SOCIAL_ACCOUNT"`
   - `stable_identifier`: unique identifier across the fixture
   - `display_name`: human-visible title or name
   - `source_mode`: `"SIMULATED"`
   - `retrieved_at`: ISO UTC timestamp string
3. **Safety & Privacy:** Fictional IDs, URLs, and phone numbers only. Do NOT use real personal data, actual customer phone numbers, or real active third-party brands.
4. **Labelling:** The `note` field must clearly describe the threat category or technique (e.g. `cleared`, `impersonation: typo-squatting`, `impersonation: customer-care scam`, `not-relevant: Kaveri River conservation`).

---

## 2. 3-Record Example

```json
{
  "fixture_version": 1,
  "records": [
    {
      "candidate": {
        "source_id": "demo_fixtures",
        "platform": "apple_app_store",
        "asset_type": "IOS_APP",
        "stable_identifier": "demo-ios-001",
        "secondary_identifiers": {"bundle_id": "com.kaveri.mobilebanking"},
        "display_name": "Kaveri Mobile Plus",
        "handle": null,
        "publisher_name": "Kaveri Bank Official",
        "url": "https://apps.apple.com/in/app/kaveri-mobile-plus/id9991001",
        "icon_url": null,
        "icon_phash": "817a7a7a7e027e81",
        "source_mode": "SIMULATED",
        "retrieved_at": "2026-10-12T12:00:00Z",
        "matched_queries": ["kaveri bank", "kaveri mobile"]
      },
      "note": "CLEARED: Official legitimate iOS mobile banking app"
    },
    {
      "candidate": {
        "source_id": "demo_fixtures",
        "platform": "bluesky",
        "asset_type": "SOCIAL_ACCOUNT",
        "stable_identifier": "did:plc:demoimpersonator12345678",
        "secondary_identifiers": {},
        "display_name": "Kaveri Bank Support 24x7",
        "handle": "kaveribank-support.bsky.social",
        "publisher_name": null,
        "url": "https://bsky.app/profile/kaveribank-support.bsky.social",
        "icon_url": null,
        "icon_phash": "817a7a7a7a037e81",
        "source_mode": "SIMULATED",
        "retrieved_at": "2026-10-12T12:00:00Z",
        "matched_queries": ["kaveri bank support"]
      },
      "note": "IMPERSONATION: Fake customer care support account soliciting credentials"
    },
    {
      "candidate": {
        "source_id": "demo_fixtures",
        "platform": "bluesky",
        "asset_type": "SOCIAL_ACCOUNT",
        "stable_identifier": "did:plc:demobenignkaveri77889900",
        "secondary_identifiers": {},
        "display_name": "Kaveri River Conservation Trust",
        "handle": "kaveririver.bsky.social",
        "publisher_name": null,
        "url": "https://bsky.app/profile/kaveririver.bsky.social",
        "icon_url": null,
        "icon_phash": null,
        "source_mode": "SIMULATED",
        "retrieved_at": "2026-10-12T12:00:00Z",
        "matched_queries": ["kaveri"]
      },
      "note": "NOT-RELEVANT: Legitimate environmental NGO sharing the namesake"
    }
  ]
}
```
