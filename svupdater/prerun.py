"""These are functions we use before we even take pid lock file.

They allow updater-supervisor to be suspended for random amount of time or it allows it to wait for internet connection.
"""

import time
import random
import subprocess
import multiprocessing
from . import const, utils


def random_sleep(min_seconds: int, max_seconds: int):
    """Sleep random amount of seconds with given range (min and max amount of seconds)."""
    if max_seconds is None or max_seconds <= 0 or max_seconds < min_seconds:
        return  # No sleep at all
    suspend = min_seconds + random.randrange(max_seconds - min_seconds)
    if suspend > 0:  # Just nice to have no print if we wait for 0 seconds
        utils.report("Suspending updater start for " + str(suspend) + " seconds")
    time.sleep(suspend)


def turris_repo_health(address: str = const.TURRIS_REPO_HEALTH_URL) -> bool:
    """Try to receive provided address and checks if result is "ok".

    Returns True on success and False if download in any way fails.
    """
    res = subprocess.run(
        ["curl", address],
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        check=False,
    )
    return res.returncode == 0 and res.stdout == "ok\n"


def wait_for_network(max_stall: int) -> bool:
    """Wait for ability to access the repo.turris.cz.

    The max_stall can be any number of seconds but too small numbers (few seconds) should not be used as it might not be
    enough time to actually perform even a single network connection test. For zero and negative numbers this function
    behaves the same way as call to the turris_repo_health.

    Returns True if connection is successful and False if wait timed out.
    """

    def network_test():
        """Run network test (expected to be run as subprocess)."""
        if not turris_repo_health():
            utils.report("Waiting for network connection")
            delay = 2
            while True:
                now = time.time()
                if turris_repo_health():
                    return
                sleep_time = delay - time.time() - now
                if sleep_time > 0:
                    time.sleep(sleep_time)
                delay *= 2

    if max_stall <= 0:
        return turris_repo_health()
    process = multiprocessing.Process(target=network_test)
    process.start()
    process.join(max_stall)
    if process.is_alive():
        process.terminate()
        return False
    return True
