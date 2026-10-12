"""Offline dataset evaluation runner adapter."""
from __future__ import annotations

from typing import Any

from app.services.evaluation import evaluate_dataset as _eval_ds


def evaluate_dataset(
    split_or_dataset: str = "threatlens-v1",
    split: str = "HELDOUT",
    **kwargs: Any,
) -> dict[str, Any]:
    """Run offline evaluation dataset harness."""
    if split_or_dataset.lower() in ("dev", "heldout"):
        target_split = split_or_dataset.upper()
        ds_id = "threatlens-v1"
    else:
        ds_id = split_or_dataset
        target_split = split.upper()

    return _eval_ds(dataset_id=ds_id, split=target_split, **kwargs)
