from config import get_config
from profiles import cpsam_v1, dhcl8881

PROFILES = {p.NAME: p for p in (dhcl8881, cpsam_v1)}
DEFAULT_PROFILE = get_config()["default_profile"]


def offered(analyses):
    """Profiles users may pick for all of these analyses (config offered_in_app), default first."""
    def ok(name):
        return set(analyses) <= set(get_config()["profiles"][name].get("offered_in_app", PROFILES[name].ANALYSES))
    return sorted(filter(ok, PROFILES), key=lambda name: name != DEFAULT_PROFILE)
