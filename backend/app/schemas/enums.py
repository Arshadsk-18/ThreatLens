"""Enums for ThreatLens v3.

Contract Version: 3.0.0
Single Source of Truth: docs/ARCHITECTURE_API_CONTRACT.md, Section 10
"""

from enum import Enum


class ScanMode(str, Enum):
    """Scan execution mode."""

    LIVE = "LIVE"
    DEMO = "DEMO"


class SourceMode(str, Enum):
    """Origin mode for a candidate record or source outcome."""

    LIVE = "LIVE"
    CACHED = "CACHED"
    SIMULATED = "SIMULATED"


class SourceStatus(str, Enum):
    """Health/query status of an external provider source."""

    CONNECTED = "CONNECTED"
    PARTIAL = "PARTIAL"
    NOT_CONNECTED = "NOT_CONNECTED"
    RATE_LIMITED = "RATE_LIMITED"
    ERROR = "ERROR"


class ScanStatus(str, Enum):
    """Lifecycle status of a scan job."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_ERRORS = "COMPLETED_WITH_ERRORS"
    FAILED = "FAILED"


class ScanStage(str, Enum):
    """Detailed pipeline progress stage."""

    queued = "queued"
    resolving_brand = "resolving_brand"
    planning_queries = "planning_queries"
    fetching = "fetching"
    normalizing = "normalizing"
    hashing_images = "hashing_images"
    assessing = "assessing"
    persisting = "persisting"
    completed = "completed"
    failed = "failed"


class AssetType(str, Enum):
    """Asset class."""

    IOS_APP = "IOS_APP"
    ANDROID_APP = "ANDROID_APP"
    SOCIAL_ACCOUNT = "SOCIAL_ACCOUNT"


class Relationship(str, Enum):
    """Relationship of an asset to the brand."""

    OFFICIAL = "OFFICIAL"
    AUTHORIZED_PARTNER = "AUTHORIZED_PARTNER"


class VerificationMethod(str, Enum):
    """Method by which an official asset was verified."""

    OWNER_PROVIDED = "OWNER_PROVIDED"
    STORE_LOOKUP = "STORE_LOOKUP"
    DOMAIN_VERIFIED_HANDLE = "DOMAIN_VERIFIED_HANDLE"


class IdentityDecision(str, Enum):
    """Outcome of IdentityGuard and scoring evaluation."""

    CLEARED_BY_IDENTITY = "CLEARED_BY_IDENTITY"
    OFFICIAL_EXACT_MATCH = "OFFICIAL_EXACT_MATCH"
    OFFICIAL_PUBLISHER_MATCH = "OFFICIAL_PUBLISHER_MATCH"
    AUTHORIZED_PARTNER_MATCH = "AUTHORIZED_PARTNER_MATCH"
    BENIGN_LOOKALIKE = "BENIGN_LOOKALIKE"
    BELOW_THRESHOLD = "BELOW_THRESHOLD"
    CANDIDATE_FOR_REVIEW = "CANDIDATE_FOR_REVIEW"

    def __eq__(self, other: object) -> bool:
        if other == "CLEARED_BY_IDENTITY" and self.value in (
            "OFFICIAL_EXACT_MATCH",
            "OFFICIAL_PUBLISHER_MATCH",
            "AUTHORIZED_PARTNER_MATCH",
        ):
            return True
        return super().__eq__(other)

    def __hash__(self) -> int:
        return hash(self.value)


class Severity(str, Enum):
    """Severity band for findings."""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class FindingStatus(str, Enum):
    """Analyst workflow review state."""

    NEW = "NEW"
    IN_REVIEW = "IN_REVIEW"
    CONFIRMED_SUSPICIOUS = "CONFIRMED_SUSPICIOUS"
    DISMISSED_FALSE_POSITIVE = "DISMISSED_FALSE_POSITIVE"
    INCONCLUSIVE = "INCONCLUSIVE"


class EvidenceStatus(str, Enum):
    """Observation reliability status for an individual signal."""

    OBSERVED = "OBSERVED"
    INFERRED = "INFERRED"
    UNAVAILABLE = "UNAVAILABLE"
    SIMULATED = "SIMULATED"


class EvidenceGroup(str, Enum):
    """Independent evidence group for corroboration."""

    NAME = "NAME"
    IDENTITY = "IDENTITY"
    VISUAL = "VISUAL"
    CONTENT = "CONTENT"
    CONTEXT = "CONTEXT"


class LookalikeTechnique(str, Enum):
    """Classification of name lookalike variation technique."""

    EXACT_NAME_REUSE = "EXACT_NAME_REUSE"
    HOMOGLYPH = "HOMOGLYPH"
    CHARACTER_SWAP = "CHARACTER_SWAP"
    OMISSION = "OMISSION"
    REPETITION = "REPETITION"
    KEYBOARD_ADJACENT = "KEYBOARD_ADJACENT"
    ADDED_WORD = "ADDED_WORD"
    SPACING = "SPACING"
    SEPARATOR = "SEPARATOR"
    NONE = "NONE"


class ProviderErrorCode(str, Enum):
    """Upstream provider error classification."""

    TIMEOUT = "TIMEOUT"
    RATE_LIMITED = "RATE_LIMITED"
    AUTH_REQUIRED = "AUTH_REQUIRED"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    NOT_CONFIGURED = "NOT_CONFIGURED"
    INVALID_RESPONSE = "INVALID_RESPONSE"
    BLOCKED_URL = "BLOCKED_URL"


class ApiErrorCode(str, Enum):
    """API-level error codes mapped to specific HTTP status codes."""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    SCAN_ALREADY_RUNNING = "SCAN_ALREADY_RUNNING"
    MODE_NOT_ALLOWED = "MODE_NOT_ALLOWED"
    RATE_LIMITED = "RATE_LIMITED"
    UNAUTHORIZED = "UNAUTHORIZED"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class EvalLabel(str, Enum):
    """Ground truth evaluation dataset label."""

    IMPERSONATION = "IMPERSONATION"
    BENIGN_NAMESAKE = "BENIGN_NAMESAKE"
    OFFICIAL = "OFFICIAL"


class EvalProvenance(str, Enum):
    """Evaluation case provenance."""

    REAL_CAPTURED = "REAL_CAPTURED"
    SYNTHETIC = "SYNTHETIC"


class EvalSplit(str, Enum):
    """Evaluation split."""

    DEV = "DEV"
    HELDOUT = "HELDOUT"


class SourceId(str, Enum):
    """Fixed source identifier enumeration."""

    apple_itunes = "apple_itunes"
    bluesky_public = "bluesky_public"
    bluesky_posts = "bluesky_posts"
    google_play_snapshot = "google_play_snapshot"
    instagram = "instagram"
    x = "x"
    facebook = "facebook"
    demo_fixtures = "demo_fixtures"
    recorded_fixtures = "recorded_fixtures"
