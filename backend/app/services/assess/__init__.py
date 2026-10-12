"""Assessment, comparison, and scoring service package.

Contract Section 12 re-exports.
"""

try:
    from app.services.assess.engine import assess
    from app.services.compare.comparison import compare, icon_similarity
except (ImportError, ModuleNotFoundError):
    from backend.app.services.assess.engine import assess
    from backend.app.services.compare.comparison import compare, icon_similarity

__all__ = ["assess", "compare", "icon_similarity"]
