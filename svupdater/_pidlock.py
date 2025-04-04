"""This implements updater-supervisor pid file lock.
This ensures that only one instance of updater-supervisor is running and that any other just spawned instance can send
signal to this instance.
Signals are used in updater-supervisor for simple comunication between instance holding lock and any other spawned
instance.
"""

import os
import fcntl
import errno
import signal
from .const import PID_FILE_PATH
from .utils import report, check_exclusive_lock
from .exceptions import UpdaterPidLockFailureError


def pid_locked():
    """Check if someone holds pid lock. It won't check if process holding the
    lock is alive. But it can potentially also catch such situation as in that
    case we would manage to get exclusive lock. But we can't ensure that
    because some other instance can have shared lock at the same time because
    it wants to read content.
    """
    return check_exclusive_lock(PID_FILE_PATH, True)


def pid_lock_content():
    """Get content of our pid lock. That is, it returns pid (as an integer).
    If there is no lock or its content is invalid then it returns None.
    """
    file = None
    try:
        file = os.open(PID_FILE_PATH, os.O_RDONLY)
    except IOError as excp:
        # There is no such file
        if excp.errno == errno.EACCES:
            return None
        raise
    # TODO timeout
    fcntl.flock(file, fcntl.LOCK_SH)  # Lock for shared read
    # Check if we are reading existing file (if it wasn't unlinked)
    invalid = False
    try:
        if os.fstat(file).st_ino != os.stat(PID_FILE_PATH).st_ino:
            invalid = True
    except OSError as excp:
        if excp.errno == errno.ENOENT:
            invalid = True
        raise
    if invalid:  # Otherwise try again
        os.close(file)
        return pid_lock_content()
    val = None
    with os.fdopen(file, "r") as filed:
        try:
            val = int(filed.readline())
        except ValueError:
            pass  # Failed to convert for us means that pid is invalid (None)
    # Note: file is closed when we leave fdopen closure
    return val


class PidLock:
    """Supervisor pid file to ensure that only one instance is running and that
    that specific instance can receive SIGUSR1 to inform it that it should run
    pkgupdate once again. This functionality is exported using sigusr property.

    Note that there should be only once PidLock object used in single process
    because it registers signal.
    """

    def __init__(self):
        self.file = None
        self._sigusr_rec = False
        signal.signal(signal.SIGUSR1, self._sigusr1)

    def __del__(self):
        if self.file is not None:
            self.free()

    def _sigusr1(self, *_):
        self._sigusr_rec = True

    @property
    def sigusr1(self):
        "If SIGUSR1 was receiver. Reading this sets it back to False"
        val = self._sigusr_rec
        self._sigusr_rec = False
        return val

    def _take(self, overtake):
        "Take lock if possible"
        flags = (
            os.O_WRONLY | os.O_SYNC | os.O_CREAT | (os.O_EXCL if not overtake else 0)
        )
        while True:
            try:
                self.file = os.open(PID_FILE_PATH, flags)
                fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as excp:
                # File exists or lock couldn't been acquired
                if excp.errno == errno.EEXIST or excp.errno == errno.EWOULDBLOCK:
                    return False
                raise
            # There is possible race condition when file is removed before we
            # lock it. This ensures that we have file that is on FS
            invalid = False
            try:
                if os.fstat(self.file).st_ino == os.stat(PID_FILE_PATH).st_ino:
                    invalid = True
            except OSError as excp:
                if excp.errno == errno.ENOENT:
                    invalid = True
                raise
            if invalid:
                os.ftruncate(self.file, 0)
                os.write(self.file, str.encode(str(os.getpid())))
                os.fsync(self.file)
                return True
            # File was removed before we were able to acquire lock. Try again.
            os.close(self.file)

    def acquire(self, send_signal):
        """Try to take supervisor pid lock. Returns boolean signaling if lock
        was taken successfully.
        """
        if self._take(False):
            return True  # We have lock so return
        pid = pid_lock_content()
        if pid is None:
            report(
                "Taking lock for PID file failed but no pid loaded. Trying to lock pid again."
            )
            if self._take(True):
                return True
            pid = pid_lock_content()  # Second attempt
            if pid is None:
                report("Second attempt failed too. Giving up.")
                return False
        # Here we have loaded pid
        sig = signal.SIGUSR1 if send_signal else 0
        try:
            os.kill(pid, sig)
        except OSError as excp:
            if excp.errno != errno.ESRCH:
                raise
            # It doesn't runs
            report("There is no running process with stored pid. Overtaking it.")
            if self._take(True):
                return True
            report("Pid file overtake failed. Giving up.")
            return False
        # Signal sent successfully
        if send_signal:
            report(
                "Another instance is already running. It was notified to run pkgupdate again."
            )
        else:
            report("Another instance of supervisor is already running.")
        return False

    def free(self):
        """Free pid lock if we have it at the moment"""
        if self.file is None:
            raise UpdaterPidLockFailureError("Can't free not taken pidlock")
        file = self.file
        self.file = None
        # TODO timeout
        fcntl.flock(file, fcntl.LOCK_EX)
        os.remove(PID_FILE_PATH)
        os.close(file)
        file = None

    def block(self):
        """Block read access to pid lock."""
        if self.file is None:
            raise UpdaterPidLockFailureError("Can't block not taken pidlock")
        # TODO timeout
        fcntl.flock(self.file, fcntl.LOCK_EX)

    def unblock(self):
        """Unblock previously blocked read access. Note that in default when
        lock is acquired it is blocking read access.
        """
        if self.file is None:
            raise UpdaterPidLockFailureError("Can't block not taken pidlock")
        # TODO timeout
        fcntl.flock(self.file, fcntl.LOCK_SH)
