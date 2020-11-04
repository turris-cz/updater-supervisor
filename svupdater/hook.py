"""Support for hook commands executed at the end of updater execution. It is in general a way to get notification about
updater execution termination even if we are not the master of that process.
"""
import os
import sys
import fcntl
import errno
import subprocess
import typing
import threading
from . import utils, const, _pidlock
from .exceptions import UpdaterInvalidHookCommandError


def __run_command(command):
    def _fthread(file):
        while True:
            line = file.readline()
            if not line:
                break
            utils.report(line.decode(sys.getdefaultencoding()))

    utils.report('Running command: ' + command)
    process = subprocess.Popen(command, stderr=subprocess.PIPE,
                               stdout=subprocess.PIPE,
                               shell=True)
    tout = threading.Thread(target=_fthread, args=(process.stdout,))
    terr = threading.Thread(target=_fthread, args=(process.stderr,))
    tout.daemon = True
    terr.daemon = True
    tout.start()
    terr.start()
    exit_code = process.wait()
    if exit_code != 0:
        utils.report('Command failed with exit code: ' + str(exit_code))


def register(command: str):
    """Add given command (format is expected to be same as if you call
    subprocess.run) to be executed when updater exits. Note that this hook is
    executed no matter if updater passed or failed or even if it just requested
    user's approval. In all of those cases when updater exits this hook is
    executed.

    "commands" has to be single line shell script.
    """
    if '\n' in command:
        raise UpdaterInvalidHookCommandError(
            "Argument register can be only single line string.")
    # Open file for writing and take exclusive lock
    file = os.open(const.POSTRUN_HOOK_FILE, os.O_WRONLY | os.O_CREAT | os.O_APPEND)
    fcntl.lockf(file, fcntl.LOCK_EX)
    # Check if we are working with existing file
    invalid = False
    try:
        if os.fstat(file).st_ino != os.stat(const.POSTRUN_HOOK_FILE).st_ino:
            invalid = True
    except OSError as excp:
        if excp.errno == errno.ENOENT:
            invalid = True
        raise
    if invalid:  # File was removed before we locked it
        os.close(file)
        register(command)
        return
    if not _pidlock.pid_locked():  # Check if updater is running
        os.close(file)
        # If there is no running instance then just run given command
        __run_command(command)
        return
    # Append given arguments to file
    # Note: This takes ownership of file and automatically closes it. (at least
    # it seems that way)
    with os.fdopen(file, 'w') as fhook:
        fhook.write(command + '\n')
    utils.report('Postrun hook registered: ' + command)


def register_list(commands: typing.Iterable[str]):
    """Same as register but it allows multiple commands to be registered at
    once.
    """
    if commands is not None:
        for cmd in commands:
            register(cmd)


def _run():
    """Run all registered commands.
    """
    # Open file for reading and take exclusive lock
    try:
        file = os.open(const.POSTRUN_HOOK_FILE, os.O_RDWR)
    except OSError as excp:
        if excp.errno == errno.ENOENT:
            return  # No file means nothing to do
        raise
    fcntl.lockf(file, fcntl.LOCK_EX)
    # Note: nobody except us should be able to remove this file (because we
    # should hold pidlock) so we don't have to check if file we opened is still
    # on FS.
    with os.fdopen(file, 'r') as fhook:
        for line in fhook.readlines():
            __run_command(line)
        os.remove(const.POSTRUN_HOOK_FILE)
