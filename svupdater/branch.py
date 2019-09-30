from euci import EUci


def get_os_branch_or_version():
    """Get OS branch or version from uci."""
    with EUci() as uci:
        mode = uci.get("updater", "turris", "mode", dtype=str)
        value = uci.get("update", "turris", mode, dtype=str, default="")

    if mode == "version" and not value:
        # fallback to branch when no version is provided
        mode = "branch"

    if mode == "branch" and not value:
        value = "hbs"

    return mode, value
