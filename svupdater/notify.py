"""Functions generating notifications about various events. These are notifications send to user using notification
system.
"""
import os
import sys
import subprocess
from . import utils, const, approvals


def clear_logs():
    """Remove files updater dumps when it detects failure.
    """
    if os.path.isfile(const.PKGUPDATE_ERROR_LOG):
        os.remove(const.PKGUPDATE_ERROR_LOG)
    if os.path.isfile(const.PKGUPDATE_CRASH_LOG):
        os.remove(const.PKGUPDATE_CRASH_LOG)


def failure(exit_code: int, trace: str):
    """Send notification about updater's failure
    """
    if exit_code == 0 and not os.path.isfile(const.PKGUPDATE_ERROR_LOG):
        return

    msg_cs = "Updater selhal: "
    msg_en = "Updater failed: "

    if os.path.isfile(const.PKGUPDATE_ERROR_LOG):
        with open(const.PKGUPDATE_ERROR_LOG, 'r') as file:
            content = '\n'.join(file.readlines())
        msg_en += content
        msg_cs += content
    elif os.path.isfile(const.PKGUPDATE_CRASH_LOG):
        with open(const.PKGUPDATE_CRASH_LOG, 'r') as file:
            content = '\n'.join(file.readlines())
        msg_en += content
        msg_cs += content
    elif trace is not None:
        msg_en += trace + "\n\nExit code: " + str(exit_code)
        msg_cs += trace + "\n\nNávratový kód: " + str(exit_code)
    else:
        msg_en += "Unknown error"
        msg_cs += "Neznámá chyba"

    if subprocess.call(['create_notification', '-s', 'error',
                        msg_cs, msg_en]) != 0:
        utils.report('Notification creation failed.')

    clear_logs()


def changes():
    """Send notification about changes.
    """
    if not os.path.isfile(const.PKGUPDATE_LOG):
        return

    text_en = ""
    text_cs = ""
    with open(const.PKGUPDATE_LOG, 'r') as file:
        for line in file.readlines():
            pkg = line.split(' ')
            if pkg[0].strip() == 'I':
                text_en += " • Installed version {} of package {}\n".format(
                    pkg[2].strip(), pkg[1].strip())
                text_cs += " • Nainstalovaná verze {} balíku {}\n".format(
                    pkg[2].strip(), pkg[1].strip())
            elif pkg[0].strip() == 'R':
                text_en += " • Removed package {}\n".format(pkg[1].strip())
                text_cs += " • Odstraněn balík {}\n".format(pkg[1].strip())
            elif pkg[0].strip() == 'D':
                # Ignore package downloads
                pass
            else:
                utils.report("Unknown log entry: " + line.strip())

    if text_en and text_cs:
        if subprocess.call(['create_notification', '-s', 'update',
                            text_cs.encode(sys.getdefaultencoding()),
                            text_en.encode(sys.getdefaultencoding())
                            ]) != 0:
            utils.report('Notification creation failed.')

    os.remove(const.PKGUPDATE_LOG)


def approval():
    """Send notification about approval request.
    """
    apprv = approvals.current()
    text = ""
    for pkg in apprv['plan']:
        text += "\n • {0} {1} {2}".format(
            pkg['op'].title(), pkg['name'],
            "" if pkg['new_ver'] is None else pkg['new_ver'])
    if subprocess.call(['create_notification', '-s', 'update',
                        const.NOTIFY_MESSAGE_CS + text, const.NOTIFY_MESSAGE_EN + text]) \
            != 0:
        utils.report('Notification creation failed.')


def notifier():
    """This just calls notifier. It processes new notification and sends them together.
    """
    if subprocess.call(['notifier']) != 0:
        utils.report('Notifier failed')
