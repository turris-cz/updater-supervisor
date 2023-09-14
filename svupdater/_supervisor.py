"""This module is core of udpdater-supervisor. It runs and supervise updater execution."""
import atexit
import datetime
import os
import signal
import subprocess
import sys
import typing
from threading import Lock, Thread

from . import approvals, autorun, hook, notify
from ._pidlock import PidLock
from .const import APPROVALS_ASK_FILE, PKGUPDATE_CMD
from .utils import report, setup_alarm


class Supervisor:
    """Supervisor itself."""

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.kill_timeout = 0
        self.process: typing.Optional[subprocess.Popen] = None
        self.trace = ""
        self.trace_lock = Lock()
        self._devnull = open(os.devnull, "w")
        self._stdout_thread = Thread(target=self._stdout, name="pkgupdate-stdout")
        self._stderr_thread = Thread(target=self._stderr, name="pkgupdate-stderr")
        atexit.register(self._at_exit)

    def run(self, now: typing.Optional[datetime.datetime] = None, reinstall_packages: bool = False):
        """Run pkgupdate"""
        if self.process is not None:
            raise Exception("Only one call to Supervisor.run is allowed.")
        self.trace = ""
        # Prepare command to be run
        cmd = list(PKGUPDATE_CMD)
        if reinstall_packages:
            cmd.append("--reinstall-all")
        if autorun.approvals():
            auto_grant_window = autorun.auto_approve_window()
            if (
                autorun.auto_approve_time() is not None
                or auto_grant_window is None
                or auto_grant_window.in_window(now) is None
            ):
                # Ask for approval only if approve time delay is configured (in such case there has to be at least one
                # run to plan it and thus we need approval file to delay installation). Another option is that we are
                # outside of auto-grant window and thus should ask for approval instead of directly installing.
                cmd.append("--ask-approval=" + str(APPROVALS_ASK_FILE))
                approved = approvals._approved(now)
                if approved is not None:
                    cmd.append("--approve=" + approved)
        # Clear old dump files
        notify.clear_logs()
        # Open process
        self.process = subprocess.Popen(cmd, stdin=self._devnull, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self._stdout_thread.start()
        self._stderr_thread.start()

    def join(self, timeout, killtimeout):
        """Join pkgupdate execution and return exit code."""
        self.kill_timeout = killtimeout
        # Wait for pkgupdate to exit (with timeout)
        setup_alarm(self._timeout, timeout)
        exit_code = self.process.wait()
        signal.alarm(0)
        # Wait untill we process all output
        self._stdout_thread.join()
        self._stderr_thread.join()
        # Dump process
        self.process = None
        # Return exit code
        return exit_code

    def _stdout(self):
        while True:
            line = self.process.stdout.readline().decode(sys.getdefaultencoding())
            self.trace_lock.acquire()
            self.trace += line
            self.trace_lock.release()
            if not line:
                break
            if self.verbose:
                print(line, end="")
                sys.stdout.flush()

    def _stderr(self):
        while True:
            line = self.process.stderr.readline().decode(sys.getdefaultencoding())
            self.trace_lock.acquire()
            self.trace += line
            self.trace_lock.release()
            if not line:
                break
            if self.verbose:
                print(line, end="", file=sys.stderr)
                sys.stderr.flush()

    def _at_exit(self):
        if self.process is not None:
            self.process.terminate()

    def _timeout(self):
        report("Timeout run out. Terminating pkgupdate.")
        self.process.terminate()
        setup_alarm(self._kill_timeout, self.kill_timeout)
        self.process.wait()
        signal.alarm(0)

    def _kill_timeout(self):
        report("Kill timeout run out. Killing pkgupdate.")
        self.process.kill()


def run(
    ensure_run: bool,
    timeout: int,
    timeout_kill: int,
    verbose: bool,
    hooklist=None,
    now: typing.Optional[datetime.datetime] = None,
    reinstall_packages: bool = False
):
    """Run updater."""
    pidlock = PidLock()
    plown = pidlock.acquire(ensure_run)
    hook.register_list(hooklist)
    if not plown:
        sys.exit(1)
    exit_code = 0

    while True:
        pidlock.unblock()
        supervisor = Supervisor(verbose=verbose)
        report("Running pkgupdate")
        supervisor.run(now, reinstall_packages)
        exit_code = supervisor.join(timeout, timeout_kill)
        if exit_code != 0:
            report("pkgupdate exited with: " + str(exit_code))
            notify.crash(exit_code, supervisor.trace)
        else:
            report("pkgupdate reported no errors")
        del supervisor  # To clean signals and more
        approvals._update_stat()
        notify.changes()
        pidlock.block()
        if pidlock.sigusr1:
            report("Rerunning pkgupdate as requested.")
        else:
            break

    hook._run()
    notify.notifier()
    # Note: pid_lock is freed using atexit
    return exit_code
