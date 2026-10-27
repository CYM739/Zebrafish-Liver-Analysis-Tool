import yaml
from pathlib import Path

_ROOT = Path(__file__).parent
_CONFIG_PATH = _ROOT / "config.yaml"
_config = None


def get_config():
    global _config
    if _config is None:
        with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
            _config = yaml.safe_load(f)
    return _config


def profile_config(profile, analysis):
    """Default settings of one analysis ("count", "boundary" or "cell") in one profile."""
    return get_config()["profiles"][profile][analysis]


def merge_overrides(defaults, overrides):
    """Return a copy of defaults with user overrides applied.

    Only keys present in overrides (and not None) replace defaults.
    """
    cfg = dict(defaults)
    if overrides:
        for k, v in overrides.items():
            if v is not None:
                cfg[k] = v
    return cfg
