"""Tests for configuration module."""
import pytest
from backend.config import (
    CRITICAL_RISK_THRESHOLD,
    WARNING_RISK_THRESHOLD,
    GEMINI_PRO_MODEL,
    GEMINI_FLASH_MODEL,
)


def test_risk_thresholds_are_valid():
    """Risk thresholds should be between 1 and 10."""
    assert 1 <= CRITICAL_RISK_THRESHOLD <= 10
    assert 1 <= WARNING_RISK_THRESHOLD <= 10
    assert CRITICAL_RISK_THRESHOLD > WARNING_RISK_THRESHOLD


def test_model_names_are_set():
    """Model names should be non-empty strings."""
    assert isinstance(GEMINI_PRO_MODEL, str) and len(GEMINI_PRO_MODEL) > 0
    assert isinstance(GEMINI_FLASH_MODEL, str) and len(GEMINI_FLASH_MODEL) > 0
