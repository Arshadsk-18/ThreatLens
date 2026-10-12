"""Export helpers for ThreatLens evidence reports and CSV data export."""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from typing import Any

from app.db.models import (
    AnalystDecision,
    Assessment,
    CandidateAsset,
    Evidence,
    OfficialAsset,
)
from app.db.session import SessionLocal
from app.repositories.protocols import EntityNotFoundError, Page
from app.repositories.sqlalchemy_repo import SqlAlchemyAssessmentRepo
from sqlalchemy import desc, select
from sqlalchemy.orm import Session, sessionmaker

FORMULA_PREFIXES: tuple[str, ...] = ("=", "+", "-", "@", "\t", "\r")

LIMITATIONS_DISCLAIMER: str = (
    "Factual evidence report generated from stored observation signals and heuristic comparison. "
    "Automated detection does not constitute a legal determination of trademark infringement or malicious intent."
)


def sanitize_csv_cell(value: Any) -> str:
    """Sanitize a cell value to prevent spreadsheet formula injection.

    Prefix cells starting with '=', '+', '-', '@', tab, or CR with a single quote (').
    """
    if value is None:
        return ""
    text = str(value)
    if text and text[0] in FORMULA_PREFIXES:
        return f"'{text}"
    return text


def build_evidence_report(
    finding_id: str,
    session_factory: sessionmaker[Session] | None = None,
) -> dict[str, Any]:
    """Build a structured evidence report dictionary from stored assessment data.

    Contains:
    - candidate metadata
    - official asset compared against
    - identity_guard rule and outcome
    - full score_breakdown
    - gates applied
    - evidence coverage
    - observable evidence rows with source and timestamp
    - analyst decision history
    - limitations disclaimer
    - scoring_version and source_mode

    Contains stored data only, with no accusatory wording or generated claims.
    """
    factory = session_factory or SessionLocal

    with factory() as session:
        assessment = session.get(Assessment, finding_id)
        if assessment is None:
            raise EntityNotFoundError(
                f"Assessment/finding with id '{finding_id}' not found"
            )

        cand = session.get(CandidateAsset, assessment.candidate_asset_id)
        if cand is None:
            raise EntityNotFoundError(
                f"Candidate asset '{assessment.candidate_asset_id}' not found"
            )

        official_id = (
            assessment.matched_official_asset_id or assessment.nearest_official_asset_id
        )
        official_asset: OfficialAsset | None = None
        if official_id:
            official_asset = session.get(OfficialAsset, official_id)

        evidence_rows_query = (
            select(Evidence)
            .where(Evidence.assessment_id == finding_id)
            .order_by(Evidence.observed_at)
        )
        evidence_items: Sequence[Evidence] = session.scalars(evidence_rows_query).all()

        decisions_query = (
            select(AnalystDecision)
            .where(AnalystDecision.candidate_asset_id == cand.id)
            .order_by(desc(AnalystDecision.created_at))
        )
        decisions: Sequence[AnalystDecision] = session.scalars(decisions_query).all()

        # Build candidate dictionary
        candidate_data = {
            "id": cand.id,
            "platform": cand.platform,
            "asset_type": cand.asset_type,
            "stable_identifier": cand.stable_identifier,
            "secondary_identifiers": cand.secondary_identifiers,
            "display_name": cand.display_name,
            "handle": cand.handle,
            "publisher_name": cand.publisher_name,
            "developer_id": cand.developer_id,
            "description": cand.description,
            "category": cand.category,
            "external_links": cand.external_links,
            "icon_url": cand.icon_url,
            "icon_hash": cand.icon_hash,
            "canonical_url": cand.canonical_url,
            "created_at_source": cand.created_at_source.isoformat()
            if cand.created_at_source
            else None,
            "followers": cand.followers,
            "following": cand.following,
            "posts_count": cand.posts_count,
            "rating_count": cand.rating_count,
            "first_seen_at": cand.first_seen_at.isoformat()
            if cand.first_seen_at
            else None,
            "last_seen_at": cand.last_seen_at.isoformat()
            if cand.last_seen_at
            else None,
            "analyst_status": cand.analyst_status,
        }

        # Build compared official asset dictionary
        official_data = None
        if official_asset is not None:
            official_data = {
                "id": official_asset.id,
                "platform": official_asset.platform,
                "asset_type": official_asset.asset_type,
                "stable_identifier": official_asset.stable_identifier,
                "secondary_identifiers": official_asset.secondary_identifiers,
                "display_name": official_asset.display_name,
                "handle": official_asset.handle,
                "publisher_name": official_asset.publisher_name,
                "developer_id": official_asset.developer_id,
                "icon_url": official_asset.icon_url,
                "icon_hash": official_asset.icon_hash,
                "relationship": official_asset.relationship,
                "is_verified": official_asset.is_verified,
            }

        # Format evidence rows
        evidence_list = [
            {
                "id": ev.id,
                "source_id": ev.source_id,
                "evidence_type": ev.evidence_type,
                "field_name": ev.field_name,
                "status": ev.status,
                "observed_value": ev.observed_value,
                "source_url": ev.source_url,
                "observed_at": ev.observed_at.isoformat() if ev.observed_at else None,
                "notes": ev.notes,
            }
            for ev in evidence_items
        ]

        # Format decision history
        decision_list = [
            {
                "id": d.id,
                "previous_status": d.previous_status,
                "new_status": d.new_status,
                "decision_reason": d.decision_reason,
                "notes": d.notes,
                "actor_label": d.actor_label,
                "decided_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in decisions
        ]

        return {
            "finding_id": assessment.id,
            "brand_id": assessment.brand_id,
            "scan_id": assessment.scan_id,
            "candidate": candidate_data,
            "official_asset": official_data,
            "identity_guard": {
                "identity_decision": assessment.identity_decision,
                "rule": assessment.rule,
                "matched_official_asset_id": assessment.matched_official_asset_id,
                "explanation": assessment.explanation,
            },
            "risk_score": assessment.risk_score,
            "severity": assessment.severity,
            "technique": assessment.technique,
            "score_breakdown": assessment.score_breakdown,
            "gates": assessment.gates_applied,
            "evidence_coverage": assessment.evidence_coverage,
            "evidence_rows": evidence_list,
            "decision_history": decision_list,
            "limitations": LIMITATIONS_DISCLAIMER,
            "scoring_version": assessment.scoring_version,
            "source_mode": assessment.source_mode,
            "assessed_at": assessment.created_at.isoformat()
            if assessment.created_at
            else None,
        }


def findings_to_csv(
    brand_id: str,
    filters: dict[str, Any] | None = None,
    session_factory: sessionmaker[Session] | None = None,
) -> str:
    """Export findings for a brand to a spreadsheet-formula-safe CSV string.

    Guarantees:
    - Prefix cells starting with '=', '+', '-', '@', tab, or CR with a single quote.
    - Proper RFC 4180 quoting.
    - UTF-8 compatible encoding.
    """
    factory = session_factory or SessionLocal
    assessment_repo = SqlAlchemyAssessmentRepo(factory)

    filter_kwargs = dict(filters or {})
    filter_kwargs.setdefault("limit", 1000)
    filter_kwargs.setdefault("offset", 0)

    page: Page[Any] = assessment_repo.list_findings(brand_id=brand_id, **filter_kwargs)

    output = io.StringIO()
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    headers = [
        "finding_id",
        "candidate_id",
        "display_name",
        "publisher_name",
        "platform",
        "asset_type",
        "stable_identifier",
        "risk_score",
        "severity",
        "technique",
        "status",
        "source_mode",
        "observed_at",
        "canonical_url",
    ]
    writer.writerow(headers)

    for item in page.items:
        cand = item.candidate or {}
        row = [
            sanitize_csv_cell(item.id),
            sanitize_csv_cell(item.candidate_asset_id),
            sanitize_csv_cell(cand.get("display_name")),
            sanitize_csv_cell(cand.get("publisher_name")),
            sanitize_csv_cell(cand.get("platform")),
            sanitize_csv_cell(cand.get("asset_type")),
            sanitize_csv_cell(cand.get("stable_identifier")),
            sanitize_csv_cell(item.risk_score),
            sanitize_csv_cell(item.severity),
            sanitize_csv_cell(item.technique),
            sanitize_csv_cell(item.status),
            sanitize_csv_cell(item.source_mode),
            sanitize_csv_cell(
                item.observed_at.isoformat() if item.observed_at else None
            ),
            sanitize_csv_cell(cand.get("canonical_url")),
        ]
        writer.writerow(row)

    return output.getvalue()
