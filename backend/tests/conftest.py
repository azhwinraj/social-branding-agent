"""Shared fixtures and markers for the test suite."""
import pytest


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "integration: marks tests that make real LLM / API calls (skip with -m 'not integration')",
    )
