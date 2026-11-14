import pytest

from betty import local


@pytest.fixture(autouse=True)
def _own_settings(tmp_path, monkeypatch):
    """Tests never read or write the real ~/.cache/betty settings or offline data."""
    monkeypatch.setattr(local, "HOME", str(tmp_path / "betty-home"))
    monkeypatch.setattr(local, "SETTINGS", str(tmp_path / "betty-home" / "settings.json"))
    monkeypatch.setattr(local, "DISABLED", False)
