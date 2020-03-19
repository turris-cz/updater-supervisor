# Copyright (c) 2018-2020, CZ.NIC, z.s.p.o. (http://www.nic.cz/)
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the CZ.NIC nor the
#      names of its contributors may be used to endorse or promote products
#      derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL CZ.NIC BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
# LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE,
# EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
import os
import json
import gettext
import typing
from euci import EUci
from .const import PKGLISTS_FILE, PKGLISTS_LABELS_FILE
from .exceptions import UpdaterNoSuchListError, UpdaterNoSuchListOptionError

__PKGLIST_ENTRIES_LABELS = typing.Dict[str, str]
__PKGLIST_ENTRIES_OPTIONS = typing.Dict[str, typing.Union[str, bool, __PKGLIST_ENTRIES_LABELS]]
__PKGLIST_ENTRIES = typing.Dict[
    str, typing.Union[
        str, bool, __PKGLIST_ENTRIES_OPTIONS, __PKGLIST_ENTRIES_LABELS
    ]
]


def _load_json_dict(file_path):
    if not os.path.isfile(file_path):
        return {}
    with open(file_path, 'r') as file:
        return json.load(file)


def __labels(known_labels, trans, labels):
    """Convert list of label names to label dictionaries with all info.
    """
    return {
        lbl: {
            "title": trans.gettext(known_labels[lbl]['title']),
            "description": trans.gettext(known_labels[lbl]['description']),
            "severity": known_labels[lbl].get('severity', "primary"),
        } for lbl in labels if lbl in known_labels.keys()
    }


def __options(pkglist_name, trans, uci, known_labels, options):
    """Convert list of options to option dictionaries with all info.
    """
    return {
        name: {
            "enabled": uci.get('pkglists', pkglist_name, name, dtype=bool, default=option.get('default', False)),
            "title": trans.gettext(option['title']),
            "description": trans.gettext(option['description']),
            "url": option.get('url'),
            "labels": __labels(known_labels, trans, option.get('labels', {})),
        } for name, option in options.items()
    }


def pkglists(lang=None) -> typing.Dict[str, __PKGLIST_ENTRIES]:
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
        'pkglists',
        languages=[lang] if lang is not None else None,
        fallback=True)
    known_lists = _load_json_dict(PKGLISTS_FILE)
    known_labels = _load_json_dict(PKGLISTS_LABELS_FILE)

    with EUci() as uci:
        enabled_lists = uci.get('pkglists', 'pkglists', 'pkglist', list=True, default=[])
        return {
            name: {
                "enabled": name in enabled_lists,
                "title": trans.gettext(lst['title']),
                "description": trans.gettext(lst['description']),
                "url": lst.get('url'),
                "options": __options(name, trans, uci, known_labels, lst.get('options', {})),
                "labels": __labels(known_labels, trans, lst.get('labels', {})),
            } for name, lst in known_lists.items()
        }


def update_pkglists(lists: typing.Dict[str, typing.Dict[str, bool]]):
    """
    Lists is expected to be nested dictionary consisting of pklist names to be enabled
    and sub-dictionary with their options.
    Anything omitted will be disabled.
    """
    known_lists = _load_json_dict(PKGLISTS_FILE)

    for name, options in lists.items():
        if name not in known_lists:
            raise UpdaterNoSuchListError("Can't enable unknown package list: {}".format(name))
        for opt in options:
            if opt not in known_lists[name]['options']:
                raise UpdaterNoSuchListOptionError("Can't enable unknown package list option: {}: {}".format(name, opt))
    with EUci() as uci:
        uci.set('pkglists', 'pkglists', 'pkglist', list(lists.keys()))
        for name, options in lists.items():
            uci.delete('pkglists', name)
            uci.set('pkglists', name, name)
            for opt, value in options.items():
                uci.set('pkglists', name, opt, value)
