#!/usr/bin/env python3
"""The one error type the eat-your-own-food loop raises, shared so `except` catches it.

Both `cook` and `qa` refuse rounds, and two identically named exception classes
would be caught by neither's handler.
"""
from __future__ import annotations


class CookError(Exception):
    """An eat-your-own-food round that cannot be trusted, with the reason a human needs."""
