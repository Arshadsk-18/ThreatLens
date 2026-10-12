# Person 3 Delivery: Verified Real Negatives (Hard Negatives)

**Source:** Live catalog captures and verified public entities from Apple App Store and Bluesky discovery spikes.  
**Delivered by:** Person 3 (Discovery & Connectors)  
**Delivered to:** Person 4 (Detection & Evaluation)  
**Target Brand:** Kaveri Bank (Finance)  
**Total Records:** 72 verified `BENIGN_NAMESAKE` records

---

## 1. Specification & Domain Coverage

All 72 records contain the brand's distinctive token `"kaveri"`, but operate in non-financial, unrelated commercial and cultural domains:

1. **Agriculture (24 records):**
   - Hybrid seeds, agricultural tools, irrigation solutions, bio-fertilizers, organic farming cooperatives, cattle feed, dairy technology, farmer advisories.
   - Categories: `Agriculture`, `Business`, `Utilities`.
2. **Lifestyle (24 records):**
   - Handloom silk textiles, home decor, wellness retreats, herbal personal care, bridal jewelry, traditional culinary arts, interior styling.
   - Categories: `Lifestyle`, `Shopping`, `Health & Fitness`.
3. **Regional Media & Publishing (24 records):**
   - Regional language journalism, literary journals, folk music streaming, broadcasting, community gazettes, entertainment news.
   - Categories: `News`, `Entertainment`, `Books`.

---

## 2. Ingestion & Quality Standards

- **Platform Distribution:** 36 Apple App Store (`apple_itunes` / `IOS_APP`) and 36 Bluesky Social accounts (`bluesky_public` / `SOCIAL_ACCOUNT`).
- **Deduplication Rules:** Every record is strictly unique on `(platform, stable_identifier)`. Secondary identifiers (`bundle_id` and `handle`) are unique and conflict-free.
- **Dual Independent Sign-Off:** Every candidate record has undergone manual inspection and dual independent approval by `analyst_alpha` and `analyst_beta` per Section 14 to verify zero relationship or impersonation intent against Kaveri Bank.
- **Evidence Integrity:** Clean external URLs and non-conflicting icon hashes (`icon_hash != official`).
