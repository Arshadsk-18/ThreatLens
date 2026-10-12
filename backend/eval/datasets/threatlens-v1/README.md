# ThreatLens Evaluation Dataset v1 (`threatlens-v1`)

**Target Brand:** Kaveri Bank (Finance)  
**Registered Assets:**
1. Official iOS App: `1234567890`, bundle `com.kaveribank.mobile`, publisher `Kaveri Bank Ltd`, developer `9000000001`
2. Official Bluesky Profile: DID `did:plc:kaveribankofficial`, handle `kaveribank.bsky.social`
3. Authorized Partner App: `5555555555`, bundle `com.partner.kaveripay`, developer `9000000088`

## Composition Summary

- **Total Cases:** 192 (120 baseline cases + 72 Person 3 verified hard negatives)
- **Splits:**
  - `DEV`: 115 cases (59.9%)
  - `HELDOUT`: 77 cases (40.1%)
- **By Label:**
  - `IMPERSONATION`: 40 cases (Synthetic positives covering all look-alike techniques, plus 4 adversarial disclaimer abuse cases)
  - `BENIGN_NAMESAKE`: 132 cases (Real captured namesakes in unrelated categories verified by the team and analysts)
  - `OFFICIAL`: 20 cases (Exact ID matches, registered publisher ID secondary apps, and authorized partner matches)
- **By Provenance:**
  - `REAL_CAPTURED`: 142 cases
  - `SYNTHETIC`: 50 cases

## Provenances and Labeling Methodology

1. **IMPERSONATION (Positives):**
   - Synthetically constructed across all 10 `LookalikeTechnique` categories: `EXACT_NAME_REUSE`, `HOMOGLYPH`, `CHARACTER_SWAP`, `OMISSION`, `REPETITION`, `KEYBOARD_ADJACENT`, `ADDED_WORD`, `SPACING`, `SEPARATOR`.
   - Includes 4 adversarial G5 cases with "unofficial" disclaimers accompanied by copied avatars, lure terms, or exact name reuse.
2. **BENIGN_NAMESAKE (Hard Negatives):**
   - 60 baseline captured namesakes across independent commerce categories (Silk Sarees, Water Purifiers, Cineplex, Medical, Sweet Meat Stall, etc.).
   - 72 verified live records delivered by Person 3 spanning Agriculture (seeds, agro-machinery, bio-fertilizers), Lifestyle (handlooms, home decor, wellness spas), and Regional Media (Kannada news, FM radio, literary journals), with dual independent sign-off from `analyst_alpha` and `analyst_beta` per Section 14.
3. **OFFICIAL (Identity Clearings):**
   - Verified official assets, partner integrations, and publisher portfolio items designed to ensure zero false accusations (`official_flagged_count == 0`).

## Honest Limitations

- Positive impersonation cases are synthetic; live production attacks will feature novel lures and obfuscations.
- Negatives are real-world namesakes captured in sample scans and team/analyst labeled.
- Sample size is bounded (192 cases); Wilson 95% confidence intervals are reported for all metrics.
