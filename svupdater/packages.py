"""This module provides access to state of installed packages. That can be used to check which packages are installed
and more.

Examples:
To check is package is installed you can use:
    from svupdater.packages import Status
    st = Status()
    pkgs = st.installed('ca-certs')
To get any attribute of installed package such as maintainer:
    from svupdater.packages import Status
    st = Status()
    if 'ca-cert' in st and 'Maintainer' in st['ca-cert']:
        print(st['ca-cert']['Maintainer']
Note: Only field ensure to be present is 'Package'. You should check for any other to not fail. There are some other
fields such as 'Version', 'Status' and 'Installed-Time' but that is not verified by this library but rather given by
OPKG.
"""
import typing
import pathlib
import collections.abc
import datetime


class Package:
    """Generic representation of installed package state.
    This assembles info from both package's control file as well as from opkg status file. Note that opkg status file
    has precedence and duplicate fields are ignored and only first occurrence is considered.
    """

    @staticmethod
    def _parse_field(line):
        parsed = line.rstrip('\n').split(':', 1)
        name = parsed[0]
        value = parsed[1].strip() if len(parsed) > 1 else None
        return name, value

    @staticmethod
    def _commasplit(value):
        return tuple(value.split(', '))

    @staticmethod
    def _status(value):
        return tuple(value.split(' '))

    @staticmethod
    def _time(value):
        return datetime.datetime.utcfromtimestamp(int(value))

    def _add_field(self, name, value):
        parse = {
            "Depends": self._commasplit,
            "Conflicts": self._commasplit,
            "Provides": self._commasplit,
            "Status": self._status,
            "Installed-Time": self._time,
        }
        if name in parse:
            self._fields[name] = parse[name](value)
        elif name and value:
            self._fields[name] = value

    def __init__(self, rootdir, block: typing.Iterable[str]):
        self._fields = dict()
        # TODO this does not support description we just skip space indented lines
        for line in block:
            name, value = self._parse_field(line)
            self._add_field(name, value)
        if "Package" not in self._fields:
            return  # Can't continue
        control_file = pathlib.Path(rootdir) / "/usr/lib/opkg/info/" / (self._fields["Package"] + ".control")
        if control_file.exists():
            with open(control_file, "r") as file:
                for line in file:
                    name, value = self._parse_field(line)
                    if name not in self._fields:
                        self._add_field(name, value)

    def __getitem__(self, key):
        return self._fields[key]

    def __len__(self):
        return len(self._fields)

    def __iter__(self):
        return iter(self._fields)

    def is_installed(self):
        """Just simple existence of package does not ensure it is installed. It can be in some broken state or kept for
        system consistency while being in reality mostly removed. This function checks if package is fully installed.
        """
        return self._fields["Status"][2] == "installed"


class Status(collections.abc.Mapping):
    """Abstraction on top of /usr/lib/opkg/status file.
    """

    def _next_block(self, file):
        block = []
        for line in file:
            if line == "\n":
                return block
            block.append(line)
        return block if block else None

    def __init__(self, rootdir: str = "/"):
        self._packages = dict()
        with open(pathlib.Path(rootdir) / "/usr/lib/opkg/status", "r") as file:
            while True:
                block = self._next_block(file)
                if block is None:
                    break
                pkg = Package(rootdir, block)
                if "Package" in pkg:
                    self._packages[pkg["Package"]] = pkg

    def installed(self, package):
        """Check if given package is installed and returns names of all packages matching that name.
        This looks for not only packages with exactly same name as requested but also for any package providing such it.
        It returns tuple of all package names.
        """
        res = []
        if package in self._packages and self._packages[package].is_installed():
            res.append(package)
        for name, pkg in self._packages.items():
            if pkg.is_installed() and "Provides" in pkg and package in pkg["Provides"]:
                res.append(name)
        return tuple(res)

    def __getitem__(self, key):
        return self._packages[key]

    def __len__(self):
        return len(self._packages)

    def __iter__(self):
        return iter(self._packages)
