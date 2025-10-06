import os
import importlib.util
from pathlib import Path

from space.os.config import DEFAULT_CONFIG

def load_config():
    """
    Loads the configuration, starting with defaults and applying overrides.
    Precedence: User Config File > Environment Variables > Defaults.
    """
    config = DEFAULT_CONFIG.copy()

    # 1. Apply environment variable overrides
    for key, value in os.environ.items():
        if key.startswith("SPACE_"):
            config_key = key[len("SPACE_"):].lower()
            if config_key in config:
                # Attempt to convert value to original type if possible
                original_value = config[config_key]
                if isinstance(original_value, bool):
                    config[config_key] = value.lower() in ('true', '1', 't', 'y', 'yes')
                elif isinstance(original_value, int):
                    try:
                        config[config_key] = int(value)
                    except ValueError:
                        pass # Keep original if conversion fails
                else:
                    config[config_key] = value

    # 2. Apply user config file overrides
    user_config_path = Path(os.path.expanduser("~/.space/config.py"))
    if user_config_path.is_file():
        try:
            spec = importlib.util.spec_from_file_location("user_config", user_config_path)
            if spec and spec.loader:
                user_config_module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(user_config_module)
                if hasattr(user_config_module, "USER_CONFIG") and isinstance(user_config_module.USER_CONFIG, dict):
                    config.update(user_config_module.USER_CONFIG)
        except Exception:
            # Log the error but continue with current config if user file is malformed
            pass # In a real app, you'd log this.

    return config
