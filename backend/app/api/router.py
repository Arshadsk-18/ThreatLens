"""Modular API router for ThreatLens v3.

Contract Version: 3.0.0
Prefix: /api/v1
"""

from fastapi import APIRouter

from app.api.routes import assets, brands, findings, health, scans, sources

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(brands.router)
api_router.include_router(assets.router)
api_router.include_router(scans.router)
api_router.include_router(sources.router)
api_router.include_router(findings.router)
