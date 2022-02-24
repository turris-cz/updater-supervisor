#!/usr/bin/env python3
from setuptools import setup

setup(
    name='svupdater',
    version='1.5.1',
    description="Supervising application and library for updater-ng.",
    url="https://gitlab.labs.nic.cz/turris/updater/supervisor",
    author="CZ.NIC, z. s. p. o.",
    author_email="karel.koci@nic.cz",
    license="MIT",

    packages=['svupdater'],
    entry_points={
        'console_scripts': [
            'updater-supervisor=svupdater.__main__:main'
        ]
    },
    install_requires=[
        "packaging",
        "distro",
        "crontab",
        "pyuci @ git+https://gitlab.labs.nic.cz/turris/pyuci.git",
    ],
)
