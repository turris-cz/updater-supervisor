"""Access and control functions of update approvals."""
import datetime
import os
import time
import typing

from . import autorun, const, notify, utils
from .exceptions import UpdaterApproveInvalidError


class PlannedPackage(typing.TypedDict):
    name: str
    op: str
    cur_ver: typing.Optional[str]
    new_ver: typing.Optional[str]


class ApprovalRequest(typing.TypedDict):
    hash: str
    status: str
    time: int
    plan: typing.List[PlannedPackage]
    reboot: typing.Optional[typing.Union[typing.Literal["delayed"], typing.Literal["finished"]]]


def current() -> typing.Optional[ApprovalRequest]:
    """Return currently existing aprroval request. If there is no approval request pending then it returns None.

    Existing approval is returned as a dictonary with following keys:
    "hash": This contains string identifying current request. This is used for updater's plan identification, most
        probably you won't need it.
    "status": This contains one following strings:
        "asked" if request was created and user have not decided yet.
        "granted" if request was approved.
        "denied" if request was denied and should be hidden.
    "time": This is time of request creation. It's number, a Unix time.
    "plan": This contains exact plan to be approved.
        "name": Name of package.
        "op": string identifying operation. One of following are allowed: "install" if package should be installed.
              Because of backward compatibility this also means upgrade or downgrade of package.
            "upgrade" if package should be upgraded (install newer version).
            "downgrade" if package should be downgraded (install older version).
            "remove" if package should be removed from system.
        "cur_ver: Currently installed version of package as a string. This can be None if it makes no sense for given
            operation (such as install).  This can also be None when such information wasn't provided (should be
            expected because of compatibility reasons).
        "new_ver": Target version of packages as a string. This is None if it makes no sense for given operation (such
            as remove). This can also be None when such information wasn't provided.
    "reboot": This is either None if no package required reboot or "delayed" or "finished" if some package does.
    """
    # Both files have to exists otherwise it is invalid approval request
    if not const.APPROVALS_ASK_FILE.is_file() or not const.APPROVALS_STAT_FILE.is_file() or not autorun.approvals():
        return None

    with const.APPROVALS_STAT_FILE.open("r") as file:
        cols = file.readline().split(" ")
        result: ApprovalRequest = {
            "hash": cols[0].strip(),
            "status": cols[1].strip(),
            "time": int(cols[2].strip()),
            "plan": [],
            "reboot": None,
        }

    with const.APPROVALS_ASK_FILE.open("r") as file:
        # First line contains hash. We have has from stat file so just compare
        if file.readline().strip() != result["hash"]:
            return None  # Invalid request
        # Rest of the lines contains operations
        for line in file.readlines():
            cols = line.split("\t")
            result["plan"].append(
                {
                    "op": cols[0].strip(),
                    "new_ver": cols[1].strip() if cols[1] != "-" else None,
                    "cur_ver": None,
                    "name": cols[2].strip(),
                }
            )
            result["reboot"] = (
                "finished"
                if "finished" in (result["reboot"], cols[3].strip())
                else "delayed"
                if "delayd" in (result["reboot"], cols[3].strip())
                else None
            )

    return result


def _set_stat(status, hsh):
    """Set given status to APPROVALS_STAT_FILE if hsh matches current hash"""
    # Both files have to exists otherwise it is invalid approval request
    if not const.APPROVALS_ASK_FILE.is_file() or not const.APPROVALS_STAT_FILE.is_file() or not autorun.approvals():
        return

    # TODO locks (we should lock stat file before doing this)
    # Read current stat
    cols = []
    with const.APPROVALS_STAT_FILE.open("r") as file:
        cols.extend(file.readline().split(" "))

    if hsh is not None and cols[0].strip() != hsh:
        raise UpdaterApproveInvalidError("Not matching hash passed")

    # Write new stat
    cols[1] = status
    with const.APPROVALS_STAT_FILE.open("w") as file:
        file.write(" ".join(cols))


def approve(hsh: str) -> None:
    """Approve current plan.

    Passed hash should match with hash returned from current(). If it doesn't match then UpdaterApproveInvalidError is
    thrown. You can pass None to skip this check.
    """
    _set_stat("granted", hsh)


def deny(hsh: str) -> None:
    """Deny current plan.

    This makes it effectively never timeout (automatically installed). Passed hash should be same as the one returned
    from current(). If it doesn't match then UpdaterApproveInvalidError is thrown. You can pass None to skip this check.
    """
    _set_stat("denied", hsh)


def _approved(now: typing.Optional[datetime.datetime] = None):
    """Return hash of approved plan.

    If there is no approved plan then it returns None.
    """
    # Both files have to exists otherwise it is invalid approval request
    if not const.APPROVALS_ASK_FILE.is_file() or not const.APPROVALS_STAT_FILE.is_file() or not autorun.approvals():
        return None

    now = now or datetime.datetime.now()
    auto_grant_time = autorun.auto_approve_time()
    auto_grant_window = autorun.auto_approve_window()
    with const.APPROVALS_STAT_FILE.open("r") as file:
        cols = file.readline().split(" ")
        if cols[1].strip() == "granted" or (
            (auto_grant_window is None or auto_grant_window.in_window(now))
            and (
                not auto_grant_time or auto_grant_time and (int(cols[2]) < (now.timestamp() - (auto_grant_time * 3600)))
            )
        ):
            return cols[0]
        return None


def next_approve(now: typing.Optional[datetime.datetime] = None) -> typing.Optional[datetime.datetime]:
    """Check when approval created now would be auto approved. Returns None if never."""
    now = now or datetime.datetime.now()
    auto_grant_time = autorun.auto_approve_time()
    auto_grant_window = autorun.auto_approve_window()
    auto_grant_date = now + datetime.timedelta(seconds=auto_grant_time or 0)
    if auto_grant_window is not None:
        return auto_grant_window.next_window(auto_grant_date)[0]
    if auto_grant_time is not None:
        return auto_grant_date
    return None


def _gen_new_stat(new_hash):
    """Generate new stat file and send notification."""
    utils.report("Generating new approval request")
    # Write to stat file
    with const.APPROVALS_STAT_FILE.open("w") as file:
        file.write(" ".join((new_hash, "asked", str(int(time.time())))))
    # Send notification
    notify.approval()


def _update_stat():
    """This function should be run when updater finished its execution.

    It checks if stat file is consistent with plan. If there is new plan (old was replaced with some newer one) then it
    updates stat file.  When new plan is presented then it also sends notification to user about it.
    """
    if not const.APPROVALS_ASK_FILE.is_file() or not autorun.approvals():
        # Drop any existing stat file
        if const.APPROVALS_STAT_FILE.is_file():
            const.APPROVALS_STAT_FILE.unlink()
        return

    new_hash = ""
    with const.APPROVALS_ASK_FILE.open("r") as file:
        new_hash = file.readline().strip()

    if not const.APPROVALS_STAT_FILE.is_file():
        # No previous stat file so just generate it
        _gen_new_stat(new_hash)
        return

    # For existing stat file compare hashes and if they differ then generate
    with const.APPROVALS_STAT_FILE.open("r") as file:
        cols = file.readline().split(" ")
        if cols[0].strip() != new_hash:
            _gen_new_stat(new_hash)
