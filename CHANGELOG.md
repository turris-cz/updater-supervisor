# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.5.5] - 2023-09-15
### Added
- Option to pass --reinstall-all to pkgupdate, needed by switch-branch

## [1.5.4] - 2022-11-04
### Fixed
- Do not send whole stacktrace in notification for handled errors. Send just
  the actual error message.

## [1.5.3] - 2022-07-27
### Fixed
- Fixed case when updates were installed automatically, even though manual
  confirmation was required.
- Fix detection of delayed reboot and thus create complete notification for it.


## [1.5.2] - 2022-03-17
### Fixed
- crash when approvals are enabled without window being configured


## [1.5.1] - 2022-02-24
### Fixed
- block of execution when package is removed or reinstalled using opkg
- do not attempt recovery of journal on package installation


## [1.5.0] - 2022-02-16
### Added
- Reboot requirement info to approval message
- Ability to set window when update is automatically approved or installed in
  case of delayed approve

### Changed
- Switch from state log to changelog and improve notifications about changes and
  updater crashes
- `approvals.current` now returns `reboot` field as optional string instead of
  boolean. This was done to allow access to the information when reboot is
  requested to be performed.


## [1.4.3] - 2020-12-04
### Fixed
- `packages` module failure when there is uninstalled package in index


## [1.4.2] - 2020-12-01
### Fixed
- Missing defaults for `--rand-sleep` and `--wait-for-network` arguments
- Deprecated usage of `collections`


## [1.4.1] - 2020-11-20
- Merged changes from 1.3.3 fixup release


## [1.4.0] - 2020-11-06
### Added
- `msgtrace` module with ability to provide info such as date of last check for
  updates or updater execution messages
- `packages` module that allows read access of installed packages info
- Option `--no-network-fail` to skip updater run when network connection is
  unavailable
- Possibility to disable network test by setting zero
- System shutdown is now retained till there is process holding opkg lock
- argument `--autorun` to mark execution as automatic run to adhere autorun
  configuration

### Changed
- Disabled autorun now won't prevent from update, you have to use `--autorun` to
  get previous behavior


## [1.3.3] - 2020-11-20
### Fixed
- exception raised when "approvals needed" was configured there was pending
  approval

## [1.3.2] - 2020-08-17
### Changed
- pkgupdate is now not run with `--task-log`


## [1.3.1] - 2020-05-06
### Added
- Support for package lists filter based on board
- New dependency is now distro


## [1.3.0] - 2020-04-09
### Added
- options for pkglists
- labels for pkglists

### Changes
- Exceptions renamed to be more consistent with standard Python ones

### Refactor
- Used new UCI set/get methods instead of obsolete get_boolean/set_boolean ones
