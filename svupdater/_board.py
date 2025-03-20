"""Helper to identify board we are running on."""

import functools
import distro

# These are all board
BOARDS = ("mox", "omnia", "turris1x")

# turrishw mapping to updater names
BOARD_MAP = {
    "Turris Mox": "mox",
    "Turris Omnia": "omnia",
    "Turris 1.x": "turris1x",
}


@functools.lru_cache(maxsize=1)
def board() -> str:
    """Returns board name as expected by updater components of current board host."""
    return BOARD_MAP.get(distro.os_release_attr("openwrt_device_product"), "unknown")
