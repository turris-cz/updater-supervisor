"""Various utility functions used in more than one other updater-supervisor
module.
"""
import os
import sys
import fcntl
import errno
import resource
import signal
import traceback
import syslog
import typing


def report(msg: str):
    """Report message to syslog and to terminal.
    """
    if sys.stderr.isatty():
        print("\x1b[32mSupervisor\x1b[0m:" + msg, file=sys.stderr)
    else:
        print("Supervisor:" + msg, file=sys.stderr)
    syslog.syslog(msg)


def setup_alarm(func: typing.Callable, timeout: int):
    "This is simple alarm setup function with possibility of None timeout"
    if timeout is None:
        return
    signal.signal(signal.SIGALRM, func)
    signal.alarm(timeout)


def check_exclusive_lock(path: str, isflock: bool = False) -> bool:
    """This returns True if someone holds exclusive lock on given path.
    Otherwise it returns False.
    """
    try:
        file = os.open(path, os.O_RDWR)
    except (IOError, OSError) as excp:
        if excp.errno == errno.ENOENT:
            # There is no such file so no lock
            return False
        raise
    try:
        if isflock:
            fcntl.flock(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        else:
            fcntl.lockf(file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError as excp:
        os.close(file)
        if excp.errno == errno.EACCES or excp.errno == errno.EAGAIN:
            # We can't take lock so someone holds it
            return True
        raise
    os.close(file)
    # We successfully locked file so no one holds its lock
    return False


def daemonize() -> bool:
    """Fork to daemon. It returns True for parent process and False for child
    process.

    This does double fork to lost parent. And it closes standard pipes.
    """
    # First fork
    fpid = os.fork()
    if fpid != 0:
        os.waitpid(fpid, 0)
        return True
    # Set process name (just to distinguish it from parent process
    sys.argv[0] = 'updater-supervisor'
    # Second fork
    if os.fork() != 0:
        os._exit(0)
    # Setup syslog
    syslog.openlog('updater-supervisor')
    # Setup exceptions reporting hook
    sys.excepthook = lambda type, value, tb: report(
        ' '.join(traceback.format_exception(type, value, tb)))
    # Disconnect from ubus if connected
    try:
        import ubus
        if ubus.get_connected():
            ubus.disconnect(False)
    except Exception as excp:
        report("Ubus disconnect failed: " + str(excp))
    # Close all non-standard file descriptors
    for fd in range(3, resource.getrlimit(resource.RLIMIT_NOFILE)[0]):
        try:
            os.close(fd)
        except OSError:
            pass
    # Redirect standard outputs and input to devnull
    devnull = os.open(os.devnull, os.O_WRONLY)
    os.dup2(devnull, 0)
    os.dup2(devnull, 1)
    os.dup2(devnull, 2)
    os.close(devnull)
    return False
