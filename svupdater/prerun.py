"""These are functions we use before we even take pid lock file. They allow
updater-supervisor to be suspended for random amount of time or it allows it to
wait for internet connection
"""
import os
import subprocess
import time
from random import randrange
from multiprocessing import Process
from .const import PING_ADDRESS
from .utils import report


def random_sleep(max_seconds):
    "Sleep random amount of seconds with maximum of max_seconds"
    if max_seconds is None or max_seconds <= 0:
        return  # No sleep at all
    suspend = randrange(max_seconds)
    if suspend > 0:  # Just nice to have no print if we wait for 0 seconds
        report("Suspending updater start for " + str(suspend) + " seconds")
    time.sleep(suspend)

def ping(address=PING_ADDRESS, count=1, deadline=1):
    """Ping address with given amount of pings and deadline.
    Returns True on success and False if ping fails.
    """
    with open(os.devnull, 'w') as devnull:
        return subprocess.call(
            ['ping', '-c', str(count), '-w', str(deadline), address],
            stdin=devnull,
            stdout=devnull,
            stderr=devnull
            )

def wait_for_network(max_stall):
    """This tries to connect to repo.turris.cz to check if we can access it and
    otherwise it stalls execution for given maximum number of seconds.

    Returns True if connection is successful and False otherwise.
    """

    def network_test():
        "Run network test (expected to be run as subprocess)"
        if ping():
            report("Waiting for network connection")
            while ping():
                pass

    if max_stall is None:
        return  # None means no stall
    process = Process(target=network_test)
    process.start()
    process.join(max_stall)
    if process.is_alive():
        process.terminate()
        return False
    return True
