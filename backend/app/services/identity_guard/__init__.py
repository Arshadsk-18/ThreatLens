"""Identity guard package.

Contract Section 12 re-exports.
"""

try:
    from app.services.identity_guard.guard import evaluate_identity_guard
except (ImportError, ModuleNotFoundError):
    from backend.app.services.identity_guard.guard import evaluate_identity_guard

__all__ = ["evaluate_identity_guard"]
