"""Scaffold smoke test: the package is importable and exposes a version."""

import yc_scouter


def test_package_imports_and_has_version():
    assert isinstance(yc_scouter.__version__, str)
    assert yc_scouter.__version__
