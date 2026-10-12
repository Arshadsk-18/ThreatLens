"""Image fetch and perceptual hash interface specification.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Sections 5.6, 12
Owner: Person 3 (Discovery and Connectors)
Branch: feat/discovery

NOTE: This file defines the signature agreed between Person 2 and Person 3.
Person 3 owns safe downloading (allowlisted hosts, size cap, timeout) and phash computation.
Do not pretend this stub implements safe image downloading.
"""


async def fetch_icon_hash(url: str) -> str | None:
    """Safely fetch an icon/avatar and compute perceptual hash (phash hex string).

    Returns None if fetching fails, image is invalid, or host is not allowlisted.
    Implementation owned by Person 3.
    """
    raise NotImplementedError(
        "Person 3 owns safe image downloading and phash calculation."
    )
