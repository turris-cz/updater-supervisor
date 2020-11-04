"""Access and control functions of update approvals.
"""
import os
import time
import typing
from . import const, autorun, notify, utils
from .exceptions import UpdaterApproveInvalidError


PlannedPackage = typing.Dict[str, str]
ApprovalRequest = typing.Dict[str, typing.Union[str, int, typing.List[PlannedPackage], bool]]
# We can't use TypedDict as it is available since Python 3.8 but we are still using Python 3.7. TypedDict implementation
# is kept here for future replacement.
#
#class PlannedPackage(typing.TypedDict):
#    name: str
#    op: str
#    cur_ver: str
#    new_ver: str
#
#class ApprovalRequest(typing.TypedDict):
#    hash: str
#    status: str
#    time: int
#    plan: typing.List[PlannedPackage]
#    reboot: bool


def current() -> ApprovalRequest:
    """Returns currently existing aprroval request. If there is no approval
    request pending then it returns None.

    Existing approval is returned as a dictonary with following keys:
    "hash": This contains string identifying current request. This is used for
        updater's plan identification, most probably you won't need it.
    "status": This contains one following strings:
        "asked" if request was created and user have not decided yet.
        "granted" if request was approved.
        "denied" if request was denied and should be hidden.
    "time": This is time of request creation. It's number, a Unix time.
    "plan": This contains exact plan to be approved.
        "name": Name of package.
        "op": string identifying operation. One of following are allowed:
            "install" if package should be installed. Because of backward
                compatibility this also means upgrade or downgrade of package.
            "upgrade" if package should be upgraded (install newer version).
            "downgrade" if package should be downgraded (install older
                version).
            "remove" if package should be removed from system.
        "cur_ver: Currently installed version of package as a string. This can
            be None if it makes no sense for given operation (such as install).
            This can also be None when such information wasn't provided (should
            be expected because of compatibility reasons).
        "new_ver": Target version of packages as a string. This is None if it
            makes no sense for given operation (such as remove). This can also
            be None when such information wasn't provided.
    "reboot": This is boolean value informing if reboot will be done durring
            update. Note that this is forced immediate reboot.
    """
    # Both files have to exists otherwise it is invalid approval request
    if not os.path.isfile(const.APPROVALS_ASK_FILE) or \
            not os.path.isfile(const.APPROVALS_STAT_FILE) or \
            not autorun.approvals():
        return None

    result = dict()
    result['reboot'] = False

    with open(const.APPROVALS_STAT_FILE, 'r') as file:
        cols = file.readline().split(' ')
        result['hash'] = cols[0].strip()
        result['status'] = cols[1].strip()
        result['time'] = int(cols[2].strip())

    with open(const.APPROVALS_ASK_FILE, 'r') as file:
        # First line contains hash. We have has from stat file so just compare
        if file.readline().strip() != result['hash']:
            return None  # Invalid request
        # Rest of the lines contains operations
        result['plan'] = list()
        for line in file.readlines():
            cols = line.split('\t')
            pkg = dict()
            pkg['op'] = cols[0].strip()
            if cols[1] != '-':
                pkg['new_ver'] = cols[1].strip()
            else:
                pkg['new_ver'] = None
            pkg['cur_ver'] = None
            pkg['name'] = cols[2].strip()
            result['plan'].append(pkg)
            result['reboot'] = result['reboot'] or \
                cols[3].strip() == 'immediate'

    return result


def _set_stat(status, hsh):
    "Set given status to APPROVALS_STAT_FILE if hsh matches current hash"
    # Both files have to exists otherwise it is invalid approval request
    if not os.path.isfile(const.APPROVALS_ASK_FILE) or \
            not os.path.isfile(const.APPROVALS_STAT_FILE) or \
            not autorun.approvals():
        return

    # TODO locks (we should lock stat file before doing this)
    # Read current stat
    cols = list()
    with open(const.APPROVALS_STAT_FILE, 'r') as file:
        cols.extend(file.readline().split(' '))

    if hsh is not None and cols[0].strip() != hsh:
        raise UpdaterApproveInvalidError("Not matching hash passed")

    # Write new stat
    cols[1] = status
    with open(const.APPROVALS_STAT_FILE, 'w') as file:
        file.write(' '.join(cols))


def approve(hsh: str):
    """Approve current plan. Passed hash should match with hash returned from
    current(). If it doesn't match then UpdaterApproveInvalidError is
    thrown. You can pass None to skip this check.
    """
    _set_stat('granted', hsh)


def deny(hsh: str):
    """Deny current plan. This makes it effectively never timeout
    (automatically installed). Passed hash should be same as the one returned
    from current(). If it doesn't match then UpdaterApproveInvalidError is
    thrown. You can pass None to skip this check.
    """
    _set_stat('denied', hsh)


def _approved():
    """This returns hash of approved plan. If there is no approved plan then it
    returns None.
    """
    if not os.path.isfile(const.APPROVALS_ASK_FILE) or \
            not os.path.isfile(const.APPROVALS_STAT_FILE) or \
            not autorun.approvals():
        return None

    with open(const.APPROVALS_STAT_FILE, 'r') as file:
        cols = file.readline().split(' ')
        auto_grant_time = autorun.auto_approve_time()
        if cols[1].strip() == 'granted' or (auto_grant_time > 0 and int(cols[2]) < (time.time() - (auto_grant_time * 3600))):
            return cols[0]
        return None


def _gen_new_stat(new_hash):
    "Generate new stat file and send notification."
    utils.report('Generating new approval request')
    # Write to stat file
    with open(const.APPROVALS_STAT_FILE, 'w') as file:
        file.write(' '.join((new_hash, 'asked', str(int(time.time())))))
    # Send notification
    notify.approval()


def _update_stat():
    """This function should be run when updater finished its execution. It
    checks if stat file is consistent with plan. If there is new plan (old was
    replaced with some newer one) then it updates stat file.
    When new plan is presented then it also sends notification to user about
    it.
    """
    if not os.path.isfile(const.APPROVALS_ASK_FILE) or not autorun.approvals():
        # Drop any existing stat file
        if os.path.isfile(const.APPROVALS_STAT_FILE):
            os.remove(const.APPROVALS_STAT_FILE)
        return

    new_hash = ''
    with open(const.APPROVALS_ASK_FILE, 'r') as file:
        new_hash = file.readline().strip()

    if not os.path.isfile(const.APPROVALS_STAT_FILE):
        # No previous stat file so just generate it
        _gen_new_stat(new_hash)
        return

    # For existing stat file compare hashes and if they differ then generate
    with open(const.APPROVALS_STAT_FILE, 'r') as file:
        cols = file.readline().split(' ')
        if cols[0].strip() != new_hash:
            _gen_new_stat(new_hash)
