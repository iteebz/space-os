from space import config
from space.lib import paths


def test_config_loads_default_values(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "dot_space", lambda base_path=None: tmp_path / ".space")
    target = tmp_path / ".space" / "config.yaml"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("agents:\n  test: {command: test}")

    cfg = config.load_config()
    assert isinstance(cfg, dict)
    assert "agents" in cfg


def test_config_cache_clears(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "dot_space", lambda base_path=None: tmp_path / ".space")
    config.clear_cache()
    assert config.clear_cache() is None
