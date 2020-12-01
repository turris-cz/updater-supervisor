# Changelog
All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
