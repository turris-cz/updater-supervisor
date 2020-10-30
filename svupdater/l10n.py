import os
import typing
from euci import EUci
from .const import L10N_FILE
from .exceptions import UpdaterNoSuchLangError


def languages() -> typing.Dict[str, bool]:
    """Returns dict with all available l10n translations for system packages.
    """
    result = dict()

    if os.path.isfile(L10N_FILE):  # Just to be sure
        with open(L10N_FILE, 'r') as file:
            for line in file.readlines():
                if not line.strip():
                    continue  # ignore empty lines
                result[line.strip()] = False

    with EUci() as uci:
        l10n_enabled = uci.get("updater", "l10n", "langs", list=True, default=[])
    for lang in l10n_enabled:
        result[lang] = True

    return result


def update_languages(langs: typing.Iterable[str]):
    """Updates what languages should be installed to system.
    langs is expected to be a list of strings where values are ISO languages
    codes.
    Note that this doesn't verifies that those languages are specified as
    supported in appropriate file.
    """
    # Verify langs
    expected = set()
    if os.path.isfile(L10N_FILE):  # Just to be sure
        with open(L10N_FILE, 'r') as file:
            for line in file.readlines():
                expected.add(line.strip())
    for lang in langs:
        if lang not in expected:
            raise UpdaterNoSuchLangError(
                "Can't enable unsupported language code:" + str(lang))

    # Set
    with EUci() as uci:
        uci.set('updater', 'l10n', 'l10n')
        uci.set('updater', 'l10n', 'langs', langs)
