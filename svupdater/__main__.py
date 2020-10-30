import sys
import argparse
from svupdater import autorun
from svupdater.prerun import random_sleep, wait_for_network
from svupdater._supervisor import run
from svupdater.const import PKGUPDATE_TIMEOUT, PKGUPDATE_TIMEOUT_KILL
from svupdater.const import PING_TIMEOUT
from svupdater.utils import daemonize

HELP_DESCRIPTION = """
    Updater-ng supervisor used for system updating.
    """


def parse_arguments():
    "Parse script arguments"
    prs = argparse.ArgumentParser(description=HELP_DESCRIPTION)
    prs.add_argument('--daemon', '-d', action='store_true',
                     help="""
                     Run supervisor in background (detach from terminal).
                     """)
    prs.add_argument('--rand-sleep', const=7200, nargs='?', type=int,
                     help="""
                     Sleep random amount of the time with maximum of given
                     number of seconds. In default two hours are used.
                     """)
    prs.add_argument('--wait-for-network', const=PING_TIMEOUT, type=int,
                     nargs='?', help="""
                     Check if Turris repository is accessible (even before
                     going to background). You can specify timeout in seconds
                     as an argument. 10 seconds is used if no argument is
                     specified.
                     """)
    prs.add_argument('--ensure-run', action='store_true',
                     help="""
                     Make sure that updater runs at least once after current
                     time. This can be used to ensure that latest changes are
                     applied as soon as possible even if another instance of
                     updater is already running.
                     """)
    prs.add_argument('--quiet', '-q', action='store_true',
                     help="""
                     Don't print pkgupdate's output to console. But still print
                     supervisor output.
                     """)
    prs.add_argument('--timeout', default=PKGUPDATE_TIMEOUT,
                     help="""
                     Set time limit in seconds for updater execution. pkgupdate
                     is gracefully exited when this timeout runs out. This is
                     protection for pkgupdate stall. In defaut one hour is set
                     as timeout.
                     """)
    prs.add_argument('--timeout-kill', default=PKGUPDATE_TIMEOUT_KILL,
                     help="""
                     Set time in seconds after which pkgupdate is killed. This
                     is time from timeout. In default one minute is used.
                     """)
    return prs.parse_args()


def main():
    "Main function for updater-supervisor run as executable"
    if not autorun.enabled():
        print('Updater autorun disabled.')
        sys.exit(0)

    args = parse_arguments()

    if args.daemon and daemonize():
        return

    random_sleep(args.rand_sleep)
    wait_for_network(args.wait_for_network)

    sys.exit(run(
        ensure_run=args.ensure_run,
        timeout=args.timeout,
        timeout_kill=args.timeout_kill,
        verbose=not args.quiet))


if __name__ == '__main__':
    main()
