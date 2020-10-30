"""updater-supervisor specific exceptions.
"""


class UpdaterError(Exception):
    """Generic updater-supervisor exception"""


class UpdaterDisabledError(UpdaterError):
    """This exception is thrown when you try to run updater when it's
    configured to be disabled.
    """


class UpdaterApproveInvalidError(UpdaterError):
    """Exception thrown from either approve.approve() or approve.deny() when
    given hash doesn't match the one from approve.current().
    """


class UpdaterPidLockFailureError(UpdaterError):
    """This exception is thrown when we encounter some invalid usage of
    pidlock.
    """


class UpdaterNoSuchListError(UpdaterError):
    """Exception thrown from lists.update when non-existent list is given.
    """


class UpdaterNoSuchLangError(UpdaterError):
    """Exception thrown from l10n.update when unsupported language code is
    given.
    """


class UpdaterInvalidHookCommandError(UpdaterError):
    """Thrown from hook.register when argument command contains more than one
    line.
    """


class UpdaterNoSuchListOptionError(UpdaterError):
    """Exception thrown from lists.update when non-existent option for list is given.
    """


# Backward compatible exception mapping
ExceptionUpdaterDisabled = UpdaterDisabledError
ExceptionUpdaterApproveInvalid = UpdaterApproveInvalidError
ExceptionUpdaterPidLockFailure = UpdaterPidLockFailureError
ExceptionUpdaterNoSuchList = UpdaterNoSuchListError
ExceptionUpdaterNoSuchLang = UpdaterNoSuchLangError
ExceptionUpdaterInvalidHookCommand = UpdaterInvalidHookCommandError
