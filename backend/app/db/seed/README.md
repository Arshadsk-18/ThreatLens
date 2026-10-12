# ThreatLens Demo Fixtures & Visual Hash Specification (Appendix B)

**Owner:** Person 5 (Data & Seed) in collaboration with Person 3 (Connectors/Adapter).  
**Target:** Fictional brand **Kaveri Bank** (~60 candidates).

---

## 1. Perceptual Hash (pHash) Design & Math

Section 8.2 of the contract defines visual resemblance via perceptual hash similarity:
$$\text{sim} = 1 - \frac{\text{hamming}(h_1, h_2)}{64}$$

All hashes are 64-bit hexadecimal strings (16 hex characters).

### Baseline (Official Assets)
- **Official Kaveri Bank icon & avatar pHash:** `0000000000000000` (64 zero bits).

### Walkthrough & Story Hashes
1. **Scenario A / Copied Icon (0.93 similarity)**
   - **pHash:** `000000000000000f`
   - **Hamming distance:** 4 bits (`0xf` = binary `1111`).
   - **Similarity:** $1 - 4/64 = 60/64 = 0.9375 \approx 0.93$ (94%).
   - **Effect:** Fired `VISUAL` group ($v = 1.0$), 20.0 points.

2. **Scenario D & E / Copied Avatar (0.95 similarity)**
   - **pHash:** `0000000000000007`
   - **Hamming distance:** 3 bits (`0x7` = binary `0111`).
   - **Similarity:** $1 - 3/64 = 61/64 = 0.9531 \approx 0.95$ (95%).
   - **Effect:** Fired `VISUAL` group ($v = 1.0$), 20.0 points.

3. **Benign Namesakes & Unrelated Icons (0.55 similarity)**
   - **pHash:** `000000001f7f7fff`
   - **Hamming distance:** 29 bits.
   - **Similarity:** $1 - 29/64 = 35/64 = 0.5469 \approx 0.55$ (55%).
   - **Effect:** Below 0.70 threshold $\implies v = 0.0$, 0 points, does NOT fire `VISUAL`.

---

## 2. Fixture Composition Breakdown (60 Candidates)

| Group | Count | Intended Story Label | Notes |
|---|---|---|---|
| **Identity Cleared** | 5 | `cleared_r1`, `cleared_r2`, `cleared_r3` | Exact iOS app, exact Bluesky DID, second app by dev 9000000001, partner app, Android official. |
| **Benign Lookalikes** | 14 | `benign_g4`, `benign_g5` | 1 declared fan page (G5), 1 fan page with brand text (G5), 6 unrelated category apps (G4), 6 unrelated social pages (G4). |
| **Impersonation** | 12 | `impersonation_<technique>` | Scenarios A, D, E, exact-name cap (Medium), and all 9 lookalike techniques across iOS, Android, Bluesky, Instagram, X, Facebook. |
| **Not Relevant** | 29 | `not_relevant` | Name similarity $< 0.60$; realistic scan funnel noise. |
| **Total** | **60** | | `deduplicated == 5 + 29 + 14 + 0 + 12 = 60` |

---

## 3. Privacy & Safety
- **No real brands or people:** Only fictional Kaveri Bank assets.
- **Fictional phone numbers:** `+91-9876543210` format.
- **Fictional UPI IDs:** `kaveri.bank@exampleupi`.
- **Fictional DIDs:** `did:plc:kaveriofficial123` format.
