import typing
from euci import EUci, UciExceptionNotFound


def enabled() -> typing.Optional[bool]:
    """Returns True if updater can be automatically started by various system
    utils. This includes automatic periodic execution, after-boot recovery and
    other tools call to configuration aplication. This returns None if no
    configuration was set so it is possible to catch no configuration case.
    Relevant uci configuration is: updater.autorun.enable
    """
    with EUci() as uci:
        try:
            return uci.get("updater", "autorun", "enable", dtype=bool)
        except UciExceptionNotFound:
            # No option means disabled but instead of False we return None to
            # allow to handle no setting situation.
            return None


def set_enabled(enable: bool):
    """Set value that can be later received with enable function.
    It sets uci configuration value: updater.autorun.enable
    """
    with EUci() as uci:
        uci.set('updater', 'autorun', 'autorun')
        uci.set('updater', 'autorun', 'enable', enable)


def approvals() -> bool:
    """Returns True if updater approvals are enabled.
    Relevant uci configuration is: updater.autorun.approvals
    """
    with EUci() as uci:
        return uci.get("updater", "autorun", "approvals", dtype=bool, default=False)


def set_approvals(enabled: bool):
    """Set value that can later be received by enabled function.
    This is relevant to uci config: updater.autorun.approvals
    """
    with EUci() as uci:
        uci.set('updater', 'autorun', 'autorun')
        uci.set('updater', 'autorun', 'approvals', enabled)


def auto_approve_time() -> typing.Optional[int]:
    """Returns number of hours before automatic approval is granted. If no
    approval time is configured then this function returns None.
    This is releavant to uci config: updater.autorun.auto_approve_time
    """
    with EUci() as uci:
        value = uci.get("updater", "autorun", "auto_approve_time", dtype=int, default=0)
        return value if value > 0 else None


def set_auto_approve_time(approve_time: typing.Optional[int]):
    """Sets time in hours after which approval is granted. You can provide None
    or value that is less or equal to zero and in that case this feature is
    disabled and if approvals are enabled only manual approve can be granted.
    """
    with EUci() as uci:
        if approve_time and approve_time > 0:
            uci.set('updater', 'autorun', 'autorun')
            uci.set('updater', 'autorun', 'auto_approve_time', approve_time)
        else:
            uci.delete('updater', 'autorun', 'auto_approve_time')
