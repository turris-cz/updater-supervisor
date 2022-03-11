import typing
from . import autorun, const
from .utils import check_exclusive_lock as _check_exclusive_lock
from .utils import daemonize as _daemonize
from ._pidlock import pid_locked as _pid_locked
from ._supervisor import run as _run
from .prerun import wait_for_network as _wait_for_network
from .exceptions import UpdaterDisabledError


def opkg_lock() -> bool:
    """Returns True if opkg lock is taken. It can be taken by any other process. It doesn't have to be updater.
    """
    return _check_exclusive_lock(const.OPKG_LOCK, False)


def updater_supervised() -> bool:
    """This returns True if there is running updater-supervisor instance.
    (Running means as a running process not as a library in some other process)
    """
    # This is in reality a wrapper on top of pidlock
    return _pid_locked()


def run(wait_for_network: typing.Union[bool, int] = False, ensure_run: bool = False, timeout:
        int = const.PKGUPDATE_TIMEOUT,
        timeout_kill: int = const.PKGUPDATE_TIMEOUT_KILL,
        hooklist: typing.Union[None, typing.Iterable[str]] = None):
    """Run updater.

    This call will spawn daemon process and returns. But be aware that at first it checks if some other supervisor is
    not running and it takes file lock because of that. If someone messed up that lock then it won't return immediately.
    Calling this with timeout is advised for time sensitive applications.
    If there is already running daemon then it just sends signal to it and exits.
    You can pass hooks (single line shell scripts) to be run after updater.
    """
    if not autorun.enabled():
        raise UpdaterDisabledError("Can't run. Updater is configured to be disabled.")
    # Fork to daemon
    if _daemonize():
        return
    # Wait for network if configured
    if wait_for_network:
        if isinstance(wait_for_network, bool):
            wait_for_network = const.TURRIS_REPO_HEALTH_TIMEOUT
        _wait_for_network(wait_for_network)
    # And run updater
    _run(
        ensure_run=ensure_run,
        timeout=timeout,
        timeout_kill=timeout_kill,
        verbose=False,
        hooklist=hooklist)
    exit()
