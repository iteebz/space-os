from space import config
from space.lib import paths


def test_config_loads_default_values(tmp_path, monkeypatch):
    config.load_config.cache_clear()
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    config_file = data_dir / "config.yaml"
    config_file.write_text("agents:\n  test: {command: test}")

    monkeypatch.setattr(paths, "space_data", lambda: data_dir)
    cfg = config.load_config()
    assert isinstance(cfg, dict)
    assert "agents" in cfg
