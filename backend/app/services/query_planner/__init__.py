"""Query planner package.

Contract Section 12 re-exports.
"""

try:
    from app.services.query_planner.planner import plan_queries
except (ImportError, ModuleNotFoundError):
    from backend.app.services.query_planner.planner import plan_queries

__all__ = ["plan_queries"]
