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
    "Main function for updater-supervisor run as executable"
    args = parse_arguments()

    if args.autorun and not autorun.enabled():
        print("Updater autorun disabled.")
        sys.exit(0)

    if args.daemon and daemonize():
        return

    fixednow = None
    if args.rand_sleep > 0:
        now = datetime.datetime.now()
        # Note: the random sleep could skip the allowed window so if we detect one then we tweak sleep to hit it.
        wstart, wend = autorun.auto_approve_window().next_window(now)
        overlap_start = max(now, wstart)
        overlap_end = min(now + datetime.timedelta(seconds=args.rand_sleep), wend)
        if overlap_start >= overlap_end:
            random_sleep(0, args.rand_sleep)
        else:
            random_sleep((overlap_start - now).total_seconds(), (overlap_end - now).total_seconds())
            fixednow = min(datetime.datetime.now(), wend)

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
