from config import get_config
from profiles import cpsam_v1, dhcl8881

PROFILES = {p.NAME: p for p in (dhcl8881, cpsam_v1)}
DEFAULT_PROFILE = get_config()["default_profile"]
