"""This module provides easy way to access mode and target of updates. That is version branch updater follow."""

import typing
import euci


def get_os_branch_or_version() -> typing.Tuple[str, str]:
    """Get OS branch or version from uci."""
    with euci.EUci() as uci:
        mode = uci.get("updater", "turris", "mode", dtype=str, default="branch")
        value = uci.get("updater", "turris", mode, dtype=str, default="")

    if mode == "version" and not value:
        # fallback to branch when no version is provided
        mode = "branch"

    if mode == "branch" and not value:
        value = "hbs"

    return mode, value
