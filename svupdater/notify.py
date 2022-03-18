"""Functions generating notifications about various events.

These are notifications send to user using notification system.
"""
import datetime
import os
import subprocess
import typing

import packaging.version

from . import approvals, changelog, const, utils


def clear_logs():
    """Remove file updater dumps when it detects failure."""
    if const.PKGUPDATE_CRASH_LOG.is_file():
        const.PKGUPDATE_CRASH_LOG.unlink()


def crash(exit_code: int, trace: typing.Optional[str]):
    """Send notification about updater's failure."""
    if exit_code == 0 or exit_code == 1 and not const.PKGUPDATE_CRASH_LOG.is_file():
        # Nothing to report if we do not have crash log or if we exited with expected exit codes.
        return

    msg_en = "Updater execution failed:\n"
    msg_cs = "Běh updateru selhal:\n"
    if exit_code == 1:
        if not const.PKGUPDATE_CRASH_LOG.is_file():
            # The exit code 1 is used if there were some issues that updater handled. We are interested only in Lua
            # crashes. Anything else is package installation failure and crash log is not relevant.
            return
        with const.PKGUPDATE_CRASH_LOG.open("r") as file:
            content = "\n".join(file.readlines())
        msg_en += content
        msg_cs += content
    elif trace:
        msg_en += trace + f"\n\nExit code: {exit_code}"
        msg_cs += trace + f"\n\nNávratový kód: {exit_code}"
    else:
        msg_en += f"Unknown error (Exit code: {exit_code})"
        msg_cs += f"Neznámá chyba (Návratový kód: {exit_code})"

    if subprocess.call(["create_notification", "-s", "error", msg_cs, msg_en]) != 0:
        utils.report("Notification creation about crash failed.")

    clear_logs()


def changes():
    """Send notification about changes and failures in package scripts."""
    last_message = 0
    if const.CHANGELOG_LAST_REPORT.is_file():
        with const.CHANGELOG_LAST_REPORT.open("r") as file:
            last_message = int(file.read().strip())

    transactions = changelog.parse_changelog()

    text_en = ""
    text_cs = ""
    fail_en = ""
    fail_cs = ""
    for transaction in transactions:
        # Skip already reported transactions and not finished transaction
        if transaction.start <= last_message or transaction.end is None:
            continue
        last_message = transaction.start
        date = datetime.datetime.fromtimestamp(transaction.start, tz=datetime.timezone.utc).isoformat()
        text_en += f"Changes performed by updater at {date}\n"
        text_cs += f"Změny provedené updaterem v {date}\n"
        for pkg in transaction.changes:
            if not pkg.old_version:
                text_en += f" • Installed package {pkg.name} version {pkg.new_version}\n"
                text_cs += f" • Nainstalován balíček {pkg.name} verze {pkg.new_version}\n"
            elif not pkg.new_version:
                text_en += f" • Removed package {pkg.name} version {pkg.old_version}\n"
                text_cs += f" • Odstraněn balíček {pkg.name} verze {pkg.old_version}\n"
            else:
                old_version = packaging.version.parse(pkg.old_version)
                new_version = packaging.version.parse(pkg.new_version)
                if old_version > new_version:
                    text_en += f" • Downgraded package {pkg.name} from version {pkg.old_version} to version {pkg.new_version}\n"
                    text_cs += f" • Balíček {pkg.name} byl ponížen z verze {pkg.old_version} na verzi {pkg.new_version}\n"
                elif old_version < new_version:
                    text_en += (
                        f" • Updated package {pkg.name} from version {pkg.old_version} to version {pkg.new_version}\n"
                    )
                    text_cs += (
                        f" • Aktualizován balíček {pkg.name} z verze {pkg.old_version} na verzi {pkg.new_version}\n"
                    )
                else:
                    text_en += f" • Reinstalled package {pkg.name} version {pkg.old_version}\n"
                    text_cs += f" • Přeinstalován balíček {pkg.name} verze {pkg.old_version}\n"
        for fail in transaction.fails:
            type_en = {
                "preinst": "pre-installation",
                "prerm": "pre-removal",
                "postinst": "post-installation",
                "postrm": "post-removal",
            }
            type_cs = {
                "preinst": "Před-instalační skript",
                "prerm": "Skript před ostraněním",
                "postinst": "Instalační skript",
                "postrm": "Skript po odstranění",
            }
            date = datetime.datetime.fromtimestamp(transaction.start, tz=datetime.timezone.utc).isoformat()
            fail_en += f"Package's {fail.pkgname} {type_en[fail.script]} script exited with error (exit code: {fail.exit_code}) during update at {date}\n"
            fail_cs += f"{type_cs[fail.script]} selhal pro balíček {fail.pkgname} (kód ukončení:  {fail.exit_code}) při aktualizaci v {date}\n"
            if fail.log:
                fail_en += "Captured output:\n"
                fail_cs += "Zachycený výstup:\n"
                log = "\n".join("> " + line for line in fail.log.splitlines())
                fail_en += log + "\n"
                fail_cs += log + "\n"
            fail_en += "\n"
            fail_cs += "\n"

    if text_en and text_cs:
        if subprocess.call(["create_notification", "-s", "update", text_cs.encode(), text_en.encode()]) != 0:
            utils.report("Notification creation about update failed.")
    if fail_en and fail_cs:
        if subprocess.call(["create_notification", "-s", "error", fail_cs.encode(), fail_en.encode()]) != 0:
            utils.report("Notification creation about errors duing update failed.")

    with const.CHANGELOG_LAST_REPORT.open("w") as file:
        file.write(str(last_message))


def approval():
    """Send notification about approval request."""
    apprv = approvals.current()
    changelist = ""
    for pkg in apprv["plan"]:
        changelist += f"\n • {pkg['op'].title()} {pkg['name']} {'' if pkg['new_ver'] is None else pkg['new_ver']}"
    installdate = approvals.next_approve()
    text_en = (
        "Your approval is required to apply pending updates. You can grant it in the reForis administrative interface in the 'Package Management — Updates' menu."
        + (
            "\nWarning: Reboot of the device is going to be performed automatically as part of update process."
            if apprv["reboot"] == "finished"
            else ""
        )
        + (
            "\nReboot of the device is going to be required to fully apply this update."
            if apprv["reboot"] == "delayed"
            else ""
        )
        + changelist
        + (
            f"\n\nThe update is going to be automatically updated some time after {installdate.isoformat()} unless there a newer update."
            if installdate is not None
            else ""
        )
    )
    text_cs = (
        "Updater žádá o autorizaci akcí. Autorizaci můžete přidělit v administračním rozhraní reForis v záložce 'Správa balíčků — Aktualizace'."
        + ("\nPozor: Součástí aktualizace bude automatický restart zařízení." if apprv["reboot"] == "finished" else "")
        + ("\nTato aktualizace vyžaduje restart zařízení k úplné aplikaci." if apprv["reboot"] == "delayed" else "")
        + changelist
        + (
            f"\n\nAktualizace bude automaticky nainstalována někdy po {installdate.isoformat()}, pakliže se neobjeví novější."
            if installdate is not None
            else ""
        )
    )
    if subprocess.call(["create_notification", "-s", "update", text_cs.encode(), text_en.encode()]) != 0:
        utils.report("Approval notification creation failed.")


def notifier():
    """Process new notifications and send them together."""
    if subprocess.call(["notifier"]) != 0:
        utils.report("Notifier failed")
