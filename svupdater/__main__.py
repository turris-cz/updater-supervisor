import argparse
import datetime
import sys

from . import autorun
from ._supervisor import run
from .const import PKGUPDATE_TIMEOUT, PKGUPDATE_TIMEOUT_KILL, TURRIS_REPO_HEALTH_TIMEOUT
from .prerun import random_sleep, wait_for_network
from .utils import daemonize, report


def parse_arguments():
    """Parse script arguments"""
    prs = argparse.ArgumentParser(description="Updater-ng supervisor used for system updating.")
    prs.add_argument(
        "--daemon",
        "-d",
        action="store_true",
        help="Run supervisor in background (detach from terminal).",
    )
    prs.add_argument(
        "--autorun",
        "-a",
        action="store_true",
        help="Use this option when this is automatic execution. It prevents run of updater when autorun is not enabled.",
    )
    prs.add_argument(
        "--rand-sleep",
        const=7200,
        nargs="?",
        type=int,
        default=0,
        help="Sleep random amount of the time with maximum of given number of seconds. In default two hours are used.",
    )
    prs.add_argument(
        "--wait-for-network",
        const=TURRIS_REPO_HEALTH_TIMEOUT,
        type=int,
        default=10,
        nargs="?",
        help="Check if Turris repository is accessible before running updater. You can specify timeout in seconds as an argument. 10 seconds is used if no argument is specified. Specify zero to disable network check.",
    )
    prs.add_argument(
        "--no-network-fail",
        action="store_true",
        help="Do not run pkgupdate when network connection is not detected.",
    )
    prs.add_argument(
        "--ensure-run",
        action="store_true",
        help="Make sure that updater runs at least once after current time. This can be used to ensure that latest changes are applied as soon as possible even if another instance of updater is already running.",
    )
    prs.add_argument(
        "--quiet",
        "-q",
        action="store_true",
        help="Don't print pkgupdate's output to console. But still print supervisor output.",
    )
    prs.add_argument(
        "--timeout",
        default=PKGUPDATE_TIMEOUT,
        help="Set time limit in seconds for updater execution. pkgupdate is gracefully exited when this timeout runs out. This is protection for pkgupdate stall. In defaut one hour is set as timeout.",
    )
    prs.add_argument(
        "--timeout-kill",
        default=PKGUPDATE_TIMEOUT_KILL,
        help="Set time in seconds after which pkgupdate is killed. This is time from timeout. In default one minute is used.",
    )
    return prs.parse_args()


def main():
    """Main function for updater-supervisor run as executable."""
    args = parse_arguments()

    if args.autorun and not autorun.enabled():
        print("Updater autorun disabled.")
        sys.exit(0)

    if args.daemon and daemonize():
        return

    fixednow = None
    if args.rand_sleep > 0:
        now = datetime.datetime.now()
        sleep_start = now
        sleep_end = now + datetime.timedelta(seconds=args.rand_sleep)
        auto_grant_window = autorun.auto_approve_window()
        if auto_grant_window is not None:
            wstart, wend = auto_grant_window.next_window(now)
            # Note: the random sleep could skip the allowed window so if we detect one then we tweak sleep to hit it.
            # In other words we use window start as sleep start if it is before end of the sleep.
            sleep_start = sleep_start if wstart > sleep_end else max(sleep_start, wstart)
            sleep_end = sleep_end if wend < sleep_start else min(sleep_end, wend)
        random_sleep((sleep_start - now).total_seconds(), (sleep_end - now).total_seconds())
        # Note: we fake the current time to hit the auto-grant-window even if we sleep right to the end
        fixednow = min(datetime.datetime.now(), sleep_end)

    if not wait_for_network(args.wait_for_network) and args.no_network_fail:
        report("There seems to be no network connection to Turris servers. Please try again later.")
        sys.exit(1)

    sys.exit(
        run(
            ensure_run=args.ensure_run,
            timeout=args.timeout,
            timeout_kill=args.timeout_kill,
            verbose=not args.quiet,
            now=fixednow,
        )
    )


if __name__ == "__main__":
    main()
