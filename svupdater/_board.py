import distro

# These are all board
BOARDS = (
    "mox",
    "omnia",
    "turris1x"
)

# turrishw mapping to updater names
BOARD_MAP = {
    "Turris Mox": "mox",
    "Turris Omnia": "omnia",
    "Turris 1.x": "turris1x",
}

__board = None


def board():
    """Returns board name as expected by updater components of current board host.
    """
    global __board
    if __board is None:
        __board = BOARD_MAP.get(distro.os_release_attr("openwrt_device_product"), "unknown")
    return __board
