from space.lib import config as libconfig
from space.spawn import config


def test_init_config_creates_file_from_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(libconfig, "workspace_root", lambda: tmp_path)

    target = tmp_path / ".space" / "config.yaml"
    assert not target.exists()

    config.init_config()

    assert target.exists()
    assert target.read_text().startswith("agents:")


def test_init_config_does_not_overwrite_existing(tmp_path, monkeypatch):
    monkeypatch.setattr(libconfig, "workspace_root", lambda: tmp_path)

    target = tmp_path / ".space" / "config.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("custom: config")

    config.init_config()

    assert target.read_text() == "custom: config"
