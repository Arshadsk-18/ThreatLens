"""Pytest configuration and test environment setup."""

from __future__ import annotations

from pathlib import Path

from dotenv import load_dotenv

# Ensure .env from project root is loaded into environment
project_root = Path(__file__).resolve().parents[2]
env_path = project_root / ".env"
if env_path.exists():
    load_dotenv(env_path)
