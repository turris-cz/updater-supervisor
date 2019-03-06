Updater-ng supervisor
=====================
Supervising daemon, tool and Python3 library for Updater-ng. The idea is that
updater it self takes a long time to run and this should add simple enough layer
on top of it to run and manage updater from some front-end. It fulfills following
roles and features:
* Supervises user unsupervised `pkgupdate` execution and reports fatal failures
* Allows front-end to run updater in background
* Provides a way to check for updater lock status (to see if updater is running)
* Provides configuration wrapper for updater
* Implements delayed and approved updates (generally known as updater approvals)
* Periodic updater execution with possible random delay

This tool is Turris OS specific. You can use this as a code base to write your own
but you are going to have hard time in integrating it to other distributions.

Checking for updater status
----------------------------
Currently only checks if updater or opkg is running and check if there is instance
of updater running in supervisor are implemented.

To check if updater or opkg is running you can use function `opkg_lock()` which
returns boolean depending on opkg lock status.

To check if there is supervised updater running then you can call
`updater_supervised()`.

Running pkgupdate with supervisor
---------------------------------
To run updater you can either directly run `updater-supervisor` script or you can
use library and `run(wait_for_network, ensure_run, timeout, timeout_kill,
hooklist)` function.

Updater and updater-supervisor configuration
---------------------------------------------
Both updater-ng and updater-supervisor are using UCI for configuration. There are
three primary sections of configuration: `autorun`, `l10n` and `lists`.

All configuration is in UCI file `updater`.

### autorun
This is intended as a configuration for updater-supervisor. It configures
automatic execution and approvals.

`enabled()` and `set_enabled(enabled)` are getter and setter for
`updater.autorun.enabled` config. If this is not set to `True` updater-supervisor
won't start `pkgupdate`.

`approvals()` and `set_approvals(enabled)` are getter and setter for
`updater.autorun.approvals`. This informs updater-supervisor if `pkgupdate` should
be run so it immediately updates system or if it should rather only generate plan
that has to be approved.

`auto_approve_time()` and `set_auto_approve_time(approve_time)` are getter and
setter for `updater.autorun.auto_approve_time`. This is number of hours before
approval is automatically granted. This implements update delay.

### l10n
Updater in Turris OS support multiple languages. Supported languages are provided
by additional file provided by separate package but updater-supervisor serves as
a bridge between that file and updater configuration (`updater.l10n`)

To get current state and list of all supported languages at once you can call
function `l10n.languages()`. This returns dictionary where keys are language codes
and values are boolean specification if language should or should not be
installed. You can edit this table and pass it back to
`l10n.update_languages(langs)` to save settings. By that you are adding or
removing lists to/from `updater.l10n.langs`.

### lists
Updater in Turris OS supports additional sets of packages called package lists.
The definition is provided as file by package the same way as in case of l10n. The
approach to lists is same as in case of l10n with exception that more information
are provided by `lists.pkglists(lang)`.

Approvals
---------
This is a feature that simulates otherwise normal package manager execution with
user approving changes to system explicitly. This feature can also be configured
to serve as delayed updates to just delay update by some amount of time.

The implementation expects updater to be run as usual in periodic runs but
supervisor automatically configures updater to not install update unless it was
approved by it. This is done by providing hash of approved plan (or not providing
any). Updater automatically only plans actions and unless those actions were
approved (hash is same as provided by supervisor) it does not continue and instead
dumps plan information. Front-end can receive such plan with
`approvals.current()`. It later can either approve it by `approvals.approve(hash)`
or deny it `approvals.approve(hash)`. If plan is denied then it won't be
automatically approved later on if delayed updates are configured.

See also `autorun` configuration section for configuration options that are
considered in approvals.

Note that for correct functionality there is `files/hook_postupdate` script that
should be placed in `/etc/updater/hook_postupdate` to be run after `pkgupdate`
completion. It is supporting script to handle situation when supervisor is not the
only one running `pkgupdate`.

Periodic runs
-------------
Cron is used to run updater periodically to check for updates. In short there is a
cron file in `files` directory that can be used to run updater every four hours.

Updater supervisor is in such case run in background which is required because
otherwise it would hang cron execution. Another argument is `--rand-sleep`. This
delays real `pkgupdate` execution by random amount of time. This was introduced to
spread server load, it is highly suggested to use random delay for periodic
updater execution.
