# Copyright (c) 2018, CZ.NIC, z.s.p.o. (http://www.nic.cz/)
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
from euci import EUci, UciExceptionNotFound
from .const import PKGLISTS_FILE
from .exceptions import UpdaterNoSuchListError, UpdaterNoSuchListOptionError

__PKGLIST_ENTRIES = typing.Dict[str, typing.Union[str, bool]]


def _load_lists():
    if os.path.isfile(PKGLISTS_FILE):  # Just to be sure
        with open(PKGLISTS_FILE, 'r') as file:
            return json.load(file)
    else:
        return {}


def pkglists(lang=None) -> typing.Dict[str, __PKGLIST_ENTRIES]:
    """Returns dict of pkglists.
    Argument lang is expected to be a string containing language code. This
    code is then used for gettext translations of titles and descriptions of
    messages.

    Return pkglists are in dictionary where key is name of pkglist and value is
    another dictionary with following content:
    "enabled": This is boolean value containing info if pkglist is enabled.
    "hidden": This is boolean value specifying if pkglist is visible.
    "official": This is boolean value specifying if pkglist is supported.
    "title": This is title text describing pkglist (human readable name).
    "description": This is human readable description of given pkglist.
    "url": Optional URL to documentation. This can be None if not provided.
    "options": Additional package options
    """
    trans = gettext.translation(
        'pkglists',
        languages=[lang] if lang is not None else None,
        fallback=True)
    known_lists = _load_lists()

    result = {}
    with EUci() as uci:
        enabled_lists = uci.get('pkglists', 'pkglists', 'pkglist', list=True, default=[])
        for name, lst in known_lists.items():
            result[name] = {
                "enabled": name in enabled_lists,
                "title": trans.gettext(lst['title']),
                "description": trans.gettext(lst['description']),
                "official": lst.get('official', False),
                "url": lst.get('url'),
                "hidden": True,  # Obsolete option for backward compatibility
                "options": {},
            }
            for opt_name, option in lst['options']:
                result[name]['options'][opt_name] = {
                    "enabled": uci.get('pkglists', name, opt_name,
                                       dtype=bool, default=option.get('default', False)),
                    "title": trans.gettext(lst['title']),
                    "description": trans.gettext(lst['description']),
                }
    return result


def update_pkglists(lists: typing.Dict[str, typing.Dict[str, bool]]):
    """
    Lists is expected to be nested dictionary consisting of pklist names to be enabled
    and sub-dictionary with their options.
    Anything omitted will be disabled.
    """
    known_lists = _load_lists()

    for name, options in lists.items():
        if name not in known_lists:
            raise UpdaterNoSuchListError("Can't enable unknown package list: {}".format(name))
        for opt in options:
            if opt not in known_lists[name]['options']:
                raise UpdaterNoSuchListOptionError("Can't enable unknown package list option: {}: {}".format(name, opt))
    with EUci() as uci:
        uci.set('pkglists', 'pkglists', 'pkglist', lists.keys())
        for name, options in lists.items():
            uci.delete('pkglists', name)
            uci.set('pkglists', name, name)
            for opt, value in options.items():
                uci.set('pkglists', name, opt, value)
