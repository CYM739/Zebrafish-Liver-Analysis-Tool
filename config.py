import yaml
from pathlib import Path

_ROOT = Path(__file__).parent
_CONFIG_PATH = _ROOT / "config.yaml"
_config = None


def get_config():
    global _config
    if _config is None:
        with open(_CONFIG_PATH, "r") as f:
            _config = yaml.safe_load(f)
    return _config


def merge_overrides(section, overrides):
    """Return a copy of config[section] with user overrides applied.

    Only keys present in overrides (and not None) replace defaults.
    """
    cfg = dict(get_config()[section])
    if overrides:
        for k, v in overrides.items():
            if v is not None:
                cfg[k] = v
    return cfg
