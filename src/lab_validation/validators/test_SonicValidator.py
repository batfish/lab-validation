import pathlib

from .SonicValidator import SonicValidator


def test_nothing() -> None:
    fake_path = pathlib.Path("/tmp/foo")
    SonicValidator(fake_path)
    assert True
