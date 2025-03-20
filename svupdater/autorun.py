"""Configuration of updater's automatic execution."""

import collections.abc
import datetime
import typing
import warnings

import crontab
import euci


def enabled() -> typing.Optional[bool]:
    """Return True if updater can be automatically started by various system utils.

    This includes automatic periodic execution, after-boot recovery and other tools call to configuration aplication.
    This returns None if no configuration was set so it is possible to catch no configuration case.  Relevant uci
    configuration is: updater.autorun.enable
    """
    try:
        return euci.EUci().get("updater", "autorun", "enable", dtype=bool)
    except euci.UciExceptionNotFound:
        # No option means disabled but instead of False we return None to
        # allow to handle no setting situation.
        return None


def set_enabled(enable: bool) -> None:
    """Set value that can be later received with enable function.

    It sets uci configuration value: updater.autorun.enable
    """
    with euci.EUci() as uci:
        uci.set("updater", "autorun", "autorun")
        uci.set("updater", "autorun", "enable", enable)


def approvals() -> bool:
    """Return True if updater approvals are enabled.

    Relevant uci configuration is: updater.autorun.approvals
    """
    return euci.EUci().get("updater", "autorun", "approvals", dtype=bool, default=False)


def set_approvals(enabled: bool) -> None:
    """Set value that can later be received by enabled function.

    This is relevant to uci config: updater.autorun.approvals
    """
    with euci.EUci() as uci:
        uci.set("updater", "autorun", "autorun")
        uci.set("updater", "autorun", "approvals", enabled)


def auto_approve_time() -> typing.Optional[int]:
    """Return number of hours before automatic approval is granted.

    If no approval time is configured then this function returns None. This is releavant to uci config:
    updater.autorun.auto_approve_time
    """
    value = euci.EUci().get(
        "updater", "autorun", "auto_approve_time", dtype=int, default=0
    )
    return value if value > 0 else None


def set_auto_approve_time(approve_time: typing.Optional[int]) -> None:
    """Set time in hours after which approval is granted.

    You can provide None or value that is less or equal to zero and in that case this feature is disabled and if
    approvals are enabled only manual approve can be granted.
    """
    with euci.EUci() as uci:
        if approve_time and approve_time > 0:
            uci.set("updater", "autorun", "autorun")
            uci.set("updater", "autorun", "auto_approve_time", approve_time)
        else:
            uci.delete("updater", "autorun", "auto_approve_time")


class ApproveWindow:
    """Description and abstraction of auto-approve window.

    The window is specified by set of periodic points. The enable points open the window and disable points close it.
    That is used to identify the appropriate window.
    """

    def __init__(
        self,
        enables: collections.abc.Collection[str],
        disables: collections.abc.Collection[str],
    ):
        self.enables = set(enables)
        self.disables = set(disables)
        self._enables: dict[str, crontab.CronTab] = {}
        self._disables: dict[str, crontab.CronTab] = {}

    def _update_internal(self):
        def update(srcset, resdict):
            for cron in srcset - resdict.keys():
                try:
                    resdict[cron] = crontab.CronTab(cron)
                except ValueError as err:
                    warnings.warn(f"Invalid crontab format '{cron}': {err.args}")
            for cron in resdict.keys() - srcset:
                del resdict[cron]

        update(self.enables, self._enables)
        update(self.disables, self._disables)

    def add_enable(self, entry: str):
        """Add given crontab-like entry as enable.

        This is preffered way to add entry as it verifies it. It raises ValueError if entry is invalid.
        """
        self._enables[entry] = crontab.CronTab(entry)
        self.enables.add(entry)

    def add_disable(self, entry: str):
        """Add given crontab-like entry as enable.

        This is preffered way to add entry as it verifies it. It raises ValueError if entry is invalid.
        """
        self._disables[entry] = crontab.CronTab(entry)
        self.disables.add(entry)

    def in_window(
        self, now: typing.Optional[datetime.datetime] = None
    ) -> typing.Optional[datetime.datetime]:
        """Check if we are in auto-approve window.

        It returns None if we are not or the end of the window if we are.
        """
        self._update_internal()
        now = datetime.datetime.now()
        start = min(cron.previous(now) for cron in self._enables.values())
        if any(cron.previous(now) < start for cron in self._disables.values()):
            return None  # There is disable that is closer to now than any enable so we are in disabled window
        end = min(cron.next(now) for cron in self._disables.values())
        return now + datetime.timedelta(seconds=end)

    def next_window(
        self, now: typing.Optional[datetime.datetime] = None
    ) -> tuple[datetime.datetime, datetime.datetime]:
        """Return closest window for auto-approve.

        Two datetimes are returned. The first one is start of the window and the second one is end. If we are in window
        then the first one is in the past.
        """
        self._update_internal()
        now = datetime.datetime.now()
        start = -min(cron.previous(now) for cron in self._enables.values())
        if any(cron.previous(now) <= -start for cron in self._disables.values()):
            start = min(cron.next(now) for cron in self._enables.values())
        startdate = now + datetime.timedelta(seconds=start)
        end = min(cron.next(startdate) for cron in self._disables.values())
        return startdate, startdate + datetime.timedelta(seconds=end)


def auto_approve_window() -> typing.Optional[ApproveWindow]:
    """Return configuration for approve window.

    The approve window consists of periodic enables and disables. The discuite enables and disables are cron-like
    periods. For any given time we can find if we are in auto-approve window by checking if closest time is for enable
    and not for disable.
    """
    uci = euci.EUci()
    enables = uci.get(
        "updater", "autorun", "auto_approve_start", dtype=str, list=True, default=()
    )
    disables = uci.get(
        "updater", "autorun", "auto_approve_end", dtype=str, list=True, default=()
    )
    return ApproveWindow(enables, disables) if enables and disables else None


def set_auto_approve_window(window: typing.Optional[ApproveWindow]):
    """Set window when approvals are automatically granted.

    You can provide None to disable approval window.
    """
    with euci.EUci() as uci:
        if window is not None and window.enables:
            uci.set("updater", "autorun", "auto_approve_start", list(window.enables))
        else:
            uci.delete("updater", "autorun", "auto_approve_start")
        if window is not None and window.disables:
            uci.set("updater", "autorun", "auto_approve_end", list(window.disables))
        else:
            uci.delete("updater", "autorun", "auto_approve_end")
