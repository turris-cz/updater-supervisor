import os
import sys
import subprocess
from .utils import report
from .const import PKGUPDATE_LOG, NOTIFY_MESSAGE_CS, NOTIFY_MESSAGE_EN
from .const import PKGUPDATE_ERROR_LOG, PKGUPDATE_CRASH_LOG
if sys.version_info < (3, 0):
    import approvals
else:
    from . import approvals


def clear_logs():
    """Remove files updater dumps when it detects failure.
    """
    if os.path.isfile(PKGUPDATE_ERROR_LOG):
        os.remove(PKGUPDATE_ERROR_LOG)
    if os.path.isfile(PKGUPDATE_CRASH_LOG):
        os.remove(PKGUPDATE_CRASH_LOG)


def failure(exit_code: int, trace: str):
    """Send notification about updater's failure
    """
    if exit_code == 0 and not os.path.isfile(PKGUPDATE_ERROR_LOG):
        return

    msg_cs = "Updater selhal: "
    msg_en = "Updater failed: "

    if os.path.isfile(PKGUPDATE_ERROR_LOG):
        with open(PKGUPDATE_ERROR_LOG, 'r') as file:
            content = '\n'.join(file.readlines())
        msg_en += content
        msg_cs += content
    elif os.path.isfile(PKGUPDATE_CRASH_LOG):
        with open(PKGUPDATE_CRASH_LOG, 'r') as file:
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
        report('Notification creation failed.')

    clear_logs()


def changes():
    """Send notification about changes.
    """
    if not os.path.isfile(PKGUPDATE_LOG):
        return

    text_en = ""
    text_cs = ""
    with open(PKGUPDATE_LOG, 'r') as file:
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
                report("Unknown log entry: " + line.strip())

    if text_en and text_cs:
        if subprocess.call(['create_notification', '-s', 'update',
                            text_cs.encode(sys.getdefaultencoding()),
                            text_en.encode(sys.getdefaultencoding())
                            ]) != 0:
            report('Notification creation failed.')

    os.remove(PKGUPDATE_LOG)


def approval():
    """Send notification about approval request.
    """
    apprv = approvals.current()
    text = ""
    for pkg in apprv['plan']:
        text += u"\n • {0} {1} {2}".format(
            pkg['op'].title(), pkg['name'],
            "" if pkg['new_ver'] is None else pkg['new_ver'])
    if subprocess.call(['create_notification', '-s', 'update',
                        NOTIFY_MESSAGE_CS + text, NOTIFY_MESSAGE_EN + text]) \
            != 0:
        report('Notification creation failed.')


def notifier():
    """This just calls notifier. It processes new notification and sends them together.
    """
    if subprocess.call(['notifier']) != 0:
        report('Notifier failed')
