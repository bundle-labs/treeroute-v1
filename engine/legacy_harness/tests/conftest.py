"""Anchor pytest's temporary folders inside legacy_harness/tests/_pytest_tmp (not the system temp
folder), so a harness test run writes nothing outside the harness folder. pytest clears that folder
at the start of each run; it holds only files these tests created. Mirrors engine/tests/conftest.py.
"""
from pathlib import Path

import pytest

BASETEMP = Path(__file__).resolve().parent / "_pytest_tmp"


@pytest.hookimpl(tryfirst=True)
def pytest_configure(config):
    if not config.option.basetemp:
        config.option.basetemp = str(BASETEMP)
