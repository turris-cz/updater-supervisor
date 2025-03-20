"""Package lists control functions."""

import os
import json
import gettext
import typing
import euci
from . import const, _board
from .exceptions import UpdaterNoSuchListError, UpdaterNoSuchListOptionError

PkgListLabel = typing.Dict[str, str]
PkgListOption = typing.Dict[str, typing.Union[bool, str, None, PkgListLabel]]
PkgListEntry = typing.Dict[
    str, typing.Union[bool, str, None, PkgListOption, PkgListLabel]
]
# We can't use TypedDict as it is available since Python 3.8 but we are still using Python 3.7. TypedDict implementation
# is kept here for future replacement.
#
# class PkgListLabel(typing.TypeDict):
#    title: str
#    desription: str
#    severity: str
#
# class PkgListOption(typing.TypeDict):
#    enabled: bool
#    title: str
#    description: str
#    url: typing.Optional[str]
#    labels: typing.Dict[str, PkgListLabel]
#
# class PkgListEntry(typing.TypeDict):
#    enabled: bool
#    title: str
#    description: str
#    url: typing.Optional[str]
#    options: typing.Dict[str, PkgListOption]
#    labels: typing.Dict[str, PkgListLabel]


def _load_json_dict(file_path):
    if not os.path.isfile(file_path):
        return {}
    with open(file_path, "r") as file:
        return json.load(file)


def __labels(known_labels, trans, labels):
    """Convert list of label names to label dictionaries with all info."""
    return {
        lbl: {
            "title": trans.gettext(known_labels[lbl]["title"]),
            "description": trans.gettext(known_labels[lbl]["description"]),
            "severity": known_labels[lbl].get("severity", "primary"),
        }
        for lbl in labels
        if lbl in known_labels.keys()
    }


def __options(pkglist_name, trans, uci, known_labels, options):
    """Convert list of options to option dictionaries with all info."""
    return {
        name: {
            "enabled": uci.get(
                "pkglists",
                pkglist_name,
                name,
                dtype=bool,
                default=option.get("default", False),
            ),
            "title": trans.gettext(option["title"]),
            "description": trans.gettext(option["description"]),
            "url": option.get("url"),
            "labels": __labels(known_labels, trans, option.get("labels", {})),
        }
        for name, option in options.items()
        if _board.board() in option.get("boards", _board.BOARDS)
    }


def pkglists(lang=None) -> typing.Dict[str, PkgListEntry]:
    """Returns dict of pkglists.
    Argument lang is expected to be a string containing language code. This code is then used for gettext translations
    of titles and descriptions of messages.

    Return pkglists are in dictionary where key is name of pkglist and value is another dictionary with following
    content:
      "enabled": This is boolean value containing info if pkglist is enabled.
      "title": This is title text describing pkglist (human readable name).
      "description": This is human readable description of given pkglist.
      "url": Optional URL to documentation. This can be None if not provided.
      "options": Additional package options stored in dictionary where keys are option names and value another
        dictionary with content:
          "enabled": Boolean value if option is enabled or not.
          "title": Human readable name of option.
          "description": Human readable description of given pkglist option.
          "url": Optional URL to documentation. This can be None if not provided.
          "labels": Labels assigned to option. Value is dictionary same as for pkglists labels.
      "labels": Labels assigned to pkglist. Value is dictionary with keys being name of labels and values dictionaries
        with following content:
          "title": Human readable name of label.
          "description": Human readable text describing label's meaning.
          "severity": String that is one of following values:
            * "danger"
            * "warning"
            * "info"
            * "success"
            * "primary"
            * "secondary"
            * "light"
            * "dark"
    """
    trans = gettext.translation(
        "pkglists", languages=[lang] if lang is not None else None, fallback=True
    )
    known_lists = _load_json_dict(const.PKGLISTS_FILE)
    known_labels = _load_json_dict(const.PKGLISTS_LABELS_FILE)

    with euci.EUci() as uci:
        enabled_lists = uci.get(
            "pkglists", "pkglists", "pkglist", list=True, default=[]
        )
        return {
            name: {
                "enabled": name in enabled_lists,
                "title": trans.gettext(lst["title"]),
                "description": trans.gettext(lst["description"]),
                "url": lst.get("url"),
                "options": __options(
                    name, trans, uci, known_labels, lst.get("options", {})
                ),
                "labels": __labels(known_labels, trans, lst.get("labels", {})),
            }
            for name, lst in known_lists.items()
            if _board.board() in lst.get("boards", _board.BOARDS)
        }


def update_pkglists(lists: typing.Dict[str, typing.Dict[str, bool]]):
    """
    Lists is expected to be nested dictionary consisting of pklist names to be enabled and sub-dictionary with their
    options.
    Anything omitted will be disabled.
    """
    known_lists = _load_json_dict(const.PKGLISTS_FILE)

    for name, options in lists.items():
        if name not in known_lists:
            raise UpdaterNoSuchListError(
                "Can't enable unknown package list: {}".format(name)
            )
        for opt in options:
            if opt not in known_lists[name]["options"]:
                raise UpdaterNoSuchListOptionError(
                    "Can't enable unknown package list option: {}: {}".format(name, opt)
                )
    with euci.EUci() as uci:
        uci.set("pkglists", "pkglists", "pkglist", list(lists.keys()))
        for name, options in lists.items():
            uci.delete("pkglists", name)
            uci.set("pkglists", name, name)
            for opt, value in options.items():
                uci.set("pkglists", name, opt, value)
