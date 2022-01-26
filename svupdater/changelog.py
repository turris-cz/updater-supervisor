"""Parser of changelog file.

The changelog file tracks transactions (in other words set of changes) applied on system by updater.
"""
import dataclasses
import typing

from . import const, utils


@dataclasses.dataclass
class UpdaterPackageChange:
    name: str
    old_version: str
    new_version: str


@dataclasses.dataclass
class UpdaterScriptFail:
    script: typing.Union[
        typing.Literal["preinst"], typing.Literal["prerm"], typing.Literal["postinst"], typing.Literal["postrm"]
    ]
    pkgname: str
    exit_code: int
    log: str


@dataclasses.dataclass
class UpdaterTransaction:
    start: int
    end: typing.Optional[int]
    changes: tuple[UpdaterPackageChange, ...]
    fails: tuple[UpdaterScriptFail, ...]


def parse_changelog() -> tuple[UpdaterTransaction, ...]:
    """Read and parse updater's changelog file."""
    try:
        with const.PKGUPDATE_CHANGELOG.open("r") as file:
            res: list[dict] = []
            for line in file:
                line = line.rstrip('\n')
                if line.startswith("|"):
                    res[-1]["fails"][-1]["log"].append(line[1:])
                else:
                    clms = line.split("\t")
                    if clms[0] == "START":
                        res.append(
                            {
                                "start": int(clms[1]),
                                "end": None,
                                "changes": [],
                                "fails": [],
                            }
                        )
                    elif clms[0] == "END":
                        res[-1]["end"] = int(clms[1])
                    elif clms[0] == "PKG":
                        res[-1]["changes"].append(
                            UpdaterPackageChange(name=clms[1], old_version=clms[2], new_version=clms[3])
                        )
                    elif clms[0] == "SCRIPT":
                        res[-1]["fails"].append(
                            {"script": clms[2], "pkgname": clms[1], "exit_code": int(clms[3]), "log": []}
                        )
                    else:
                        utils.report(f"Unknown line in updater's changelog: {line}")
            return tuple(
                UpdaterTransaction(
                    start=t["start"],
                    end=t["end"],
                    changes=tuple(t["changes"]),
                    fails=tuple(UpdaterScriptFail(**f) for f in res[-1]["fails"]),
                )
                for t in res
            )
    except FileNotFoundError:
        return tuple()
