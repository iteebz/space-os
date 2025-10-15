from space import config
from space.lib import paths


def test_init_creates_default_file(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "dot_space", lambda base_path=None: tmp_path / ".space")

    target = tmp_path / ".space" / "config.yaml"
    assert not target.exists()

    config.init_config()

    assert target.exists()
    assert target.read_text().startswith("agents:")


def test_init_no_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "dot_space", lambda base_path=None: tmp_path / ".space")

    target = tmp_path / ".space" / "config.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("custom: config")

    config.init_config()

    assert target.read_text() == "custom: config"
