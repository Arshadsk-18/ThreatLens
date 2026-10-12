"""Seed script wrapper for ThreatLens."""

from app.db.seed import (
    DEMO_BRAND_ID,
    DEMO_BRAND_NAME,
    DEMO_SCAN_ID,
    seed_demo_story,
)

seed = seed_demo_story

__all__ = [
    "DEMO_BRAND_ID",
    "DEMO_BRAND_NAME",
    "DEMO_SCAN_ID",
    "seed",
    "seed_demo_story",
]

if __name__ == "__main__":
    seed_demo_story()
