"""Scaffold smoke test: the package is importable and exposes a version."""

import yc_radar


def test_package_imports_and_has_version():
    assert isinstance(yc_radar.__version__, str)
    assert yc_radar.__version__
