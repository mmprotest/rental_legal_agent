"""Minimal FastAPI-compatible surface for offline testing.

This stub supports the small subset of functionality used by the prototype so
that we can exercise flows without downloading external dependencies.
"""

from .app import APIRouter, FastAPI, HTTPException

__all__ = ["APIRouter", "FastAPI", "HTTPException"]

