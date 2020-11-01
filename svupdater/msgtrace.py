"""This plugin allows easy access to debug informations send by pkgupdate to syslog.

This is pretty fragile and info provided by this module should not be considered as strictly correct. There is
possibility that some of the logs might fail to match or that logging to syslog is disabled or even syslog being broken.
"""
import os
import re
import sys
import abc
import time
import typing
import datetime
from . import const
from . import opkg_lock as _opkg_lock


class Msg(metaclass=abc.ABCMeta):
    """Generic message parent class.

    Attributes:
      date: time of message creation.
    """

    def __init__(self, date, match):
        self.date = date


class MsgTargetTurrisOS(Msg):
    """This message is the first common message printed by updater.

    Attributes:
      version: string with Turris OS version (commonly in format X.Y.Z)

    This message and its format is provided by Turris updater's lists so it is no way ensured to be present at the
    beginning of updater execution.
    """

    def __init__(self, date, match):
        super().__init__(date, match)
        self.version = match.group(1)


class MsgQueue(Msg):
    """This message is printed as an info about changes to be done. There is no message if there are no changes queued.

    Attributes:
      operation: This is string informing about operation. Know list includes: install, upgrade, downgrade, reinstall
        and removal.
      name: This is string with name of package operation applies on.
      repo: This is string with name of repository (feed) package is from.
      version: This is string with package version (that is target version of package).
      current_version: This contains string with version of package before upgrade or downgrade otherwise should be
        None.
    """

    def __init__(self, date, match):
        super().__init__(date, match)
        self.operation = match.group(1)
        self.name = match.group(2)
        self.repo = match.group(3)
        self.version = match.group(4)
        self.current_version = match.group(6) if match.lastindex >= 6 else None


class MsgPackageScript(Msg):
    """This message is printed when package script execution is started.

    Attributes:
      type: This is string with type of script executed. There are four types: preinst, prerm, postinst, postrm
      package: This is string with name of package script belongs to.
    """

    def __init__(self, date, match):
        super().__init__(date, match)
        self.type = match.group(1)
        self.package = match.group(2)


class MsgHook(Msg):
    """This message is printed when updater's hook is started.

    Attributes:
      type: This is string with type of hook executed. There are three types: preupdate, postupdate, reboot_required
      name: This is string with name of hook.
    """

    def __init__(self, date, match):
        super().__init__(date, match)
        self.type = match.group(1)
        self.name = match.group(2)


class MsgDownloadingPackages(Msg):
    """This message simply informs that queued packages are being downloaded. No progress info is provided.
    This is first step when updater is running updates not just planning them, that is this is this won't be printed
    unless update was approved.
    """


class MsgUnpacking(Msg):
    """This message simply informs that packages are being unpacked. No progress info is provided.
    This is printed after MsgDownloadingPackages. You can expect to see MsgHook with preupdate type between them.
    """


class MsgCheckingForCollisions(Msg):
    """This message simply informs that updater is sanity checking packages and is looking for unknown file collisions.
    This message is printed after MsgUnpacking.
    """


class MsgInstall(Msg):
    """This message informs that updater is merging files to root file-system and is running pre-install and pre-remove
    scripts.
    This message is printed after MsgCheckingForCollisions. You can expect MsgPackageScript with 'preinst' and 'prerm'
    types after this message.
    """


class MsgRemoving(Msg):
    """This message informs that updater is removing files belonging to packages to be removed as well as any other
    leftover files.
    This message is printed after MsgInstall and possible subsequent MsgPackageScript messages.
    """


class MsgPostScripts(Msg):
    """This message informs that updater is running post-install and post-remove script of packages.
    This message is printed after MsgRemoving. You can expect MsgPackageScript with 'postinst' and 'postrm' types after
    this message.
    """


class MsgCleanup(Msg):
    """This message informs that updater is doing cleanup of packge's control files. This is the last step of update.
    This message is printed after MsgPostScripts and possible subsequent MsgPackageScript messages. You can expect
    MsgHook messages with 'reboot_required' and 'postupdate' types. No other messages are in standard printed after
    those.
    """


class LogReader:
    """This class can be used to read syslog and receive parsed updater's messages. Note that this replies all messages
    located in log unless you seek latest one or one specific.

    To receive logs from currently running instance (for example if opkg_lock() is True) you can just create instance of
    LogReader, call method seek_latest() and start calling read() method. An example:
        with LogReader(blocking=True) as lr:
            print(lr.seek_latest())
            for msg in lr:
                    print(msg)

    To receive logs from started instance you have to use method seek_after() with appropriate time. Example:
        now = datetime.datetime.utcnow()
        run()
        with LogReader(blocking=True) as lr:
            print(lr.seek_after(now))
            for msg in lr:
                    print(msg)
    """
    _log_line = r"([^ ]+ +[^ ]+ [^ ]+) [^ ]+ updater\[[\d]+\]: [^ :]+:[\d]+ \([^)]*\): (.*)"
    _lines_repre = {
        r"Target Turris OS: (.*)": MsgTargetTurrisOS,
        r"Queue ([^ ]+) of ([^/]+)/(.+)/([^/[]+)(\[(.*)\])?": MsgQueue,
        r"Running ([^ ]+) of (.*)": MsgPackageScript,
        r"Executing ([^ ]+) hook: ([^ ]+)": MsgHook,
        r"Downloading packages": MsgDownloadingPackages,
        r"Unpacking download packages": MsgUnpacking,
        r"Checking for file collisions between packages": MsgCheckingForCollisions,
        r"Running pre-install and pre-rm scripts and merging packages to root file system": MsgInstall,
        r"Removing packages and leftover files": MsgRemoving,
        r"Running post-install and post-rm scripts": MsgPostScripts,
        r"Cleaning up control files": MsgCleanup,
    }

    def __init__(self, log: str = const.SYSLOG_MESSAGES, blocking: bool = False):
        """
        "log" has to be string with path to messages file.
        "blocking" has to be bool value. False means that it returns as soon as end of the log is reached. If True is
            used it instead block till the opkg/updater lock is taken (updater is running).
        """
        self.log = log
        self.blocking = blocking
        self._file = None
        self._re_log_line = re.compile(self._log_line)
        self._re_lines = {re.compile(regexp): repre for regexp, repre in self._lines_repre.items()}

    def open(self):
        """Open log for reading.
        You have to call this before any other method.
        """
        if self._file is not None:
            self._file.close()
        self._file = open(self.log, "rb")

    def close(self):
        """Close log file.
        """
        self._file.close()
        self._file = None

    @staticmethod
    def _parse_date(strdate):
        date = datetime.datetime.strptime(strdate, '%b %d %H:%M:%S')
        # We do not have year in syslog. We have to somehow identify it. Reasonable expectation is current year but we
        # have to cover new year so we have to check month and possibly decrease year by one.
        now = datetime.datetime.utcnow()
        return date.replace(year=now.year if now.month >= date.month else (now.year - 1))

    def _clasify_line(self, line):
        line = line.decode(sys.getdefaultencoding(), 'ignore').rstrip('\n')
        match = self._re_log_line.fullmatch(line)
        if match is not None:
            date = self._parse_date(match.group(1))
            updater_line = match.group(2)
            for re_line in self._re_lines:
                lmatch = re_line.fullmatch(updater_line)
                if lmatch is not None:
                    return self._re_lines[re_line](date, lmatch)
        return None

    def seek_latest(self, msgtype: Msg = MsgTargetTurrisOS) -> typing.Optional[Msg]:
        """Seeks latest message of given type. In default that is MsgTargetTurrisOS as that is in general the first
        message printed by updater.
        It returns that message if it was located or None of not.
        """
        # We do not want to use blocking so disable it for now
        blocking = self.blocking
        self.blocking = False

        latest_index = None
        latest_msg = None
        for msg in self:
            if isinstance(msg, msgtype):
                latest_index = self._file.tell()
                latest_msg = msg
        if latest_index is not None:
            self._file.seek(latest_index)

        self.blocking = blocking
        return latest_msg

    def seek_after(self, date: datetime.datetime = datetime.datetime.utcnow(),
                   msgtype: Msg = MsgTargetTurrisOS) -> typing.Optional[Msg]:
        """Seeks message of given type that happens right after given date. In default message type this looks for is
        MsgTargetTurrisOS and date is utcnow.
        Note that date has to be in UTC as syslog logs in UTC.
        It returns that message. Note that this can block forever if no updater instance is running.
        """
        # TODO possibly add timeout?
        # We do not have microseconds in syslog and it can be the difference between now and before
        date.replace(microsecond=0)
        while True:
            for msg in self:
                if isinstance(msg, msgtype) and date <= msg.date:
                    return msg
            time.sleep(0.1)

    def read(self) -> typing.Optional[Msg]:
        """Reads log till the updater output line is located or end of log is reached. In case of blocking being set it
        tries to read log even after end is reached and returns only when opkg lock is freed.

        It returns parsed updater's line or None if end of the log was reached.
        """
        while True:
            line = self._file.readline()
            if not line:
                if self.blocking and _opkg_lock():
                    time.sleep(0.1)
                    continue
                return None
            msg = self._clasify_line(line)
            if msg is not None:
                return msg

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def __iter__(self):
        return self

    def __next__(self):
        res = self.read()
        if res is None:
            raise StopIteration
        return res


def latest_message(msgtype: Msg):
    """This function looks for latest message of given type in log and returns its date.
    This is unreliable. We might not have that in syslog as reboot happened or someone removed log. This also does not
    support and so not reads gzipped logs.

    It returns datetime or None if message wasn't located.
    """
    for messages in (const.SYSLOG_MESSAGES, const.SYSLOG_MESSAGES_1):
        if os.path.exists(messages):
            with LogReader(messages) as logread:
                msg = logread.seek_latest(msgtype)
                if msg is not None:
                    return msg.date
    return None


def last_check() -> typing.Optional[datetime.datetime]:
    """This is simple function that checks for date of last updater's execution.
    This function uses latest_message so same note about unreliable result applies here as well. Not only that but this
    is also based on unreliable MsgTargetTurrisOS.

    It returns datetime or None if time of last check is unknown.
    """
    return latest_message(MsgTargetTurrisOS)


def last_run() -> typing.Optional[datetime.datetime]:
    """This is simple function that checks for date of last updater's execution.
    This function uses latest_message so same note about unreliable result applies here as well.

    It returns datetime or None if time of last update is unknown.
    """
    return latest_message(MsgInstall)
