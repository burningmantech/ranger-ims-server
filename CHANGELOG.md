# Changelog

This is the changelog for ranger-ims-server. This is intended to summarize changes over time,
for example to inform the Operator team each event of any differences to expect.

This file must use the [Common Changelog format](https://common-changelog.org/), with the variation
that we use months rather than version numbers. We don't include dependency version upgrades in the
changelog, as those would pollute this too much.

<!--
Each month below should look like the following, using the same ordering for the four categories:
## YYYY-MM
### Changed
### Added
### Removed
### Fixed
-->

## 2024-11

### Changed
- Switched to text-fields with datalists for "Add Ranger" and "Add Incident Types" on the incident page. Previously we used select fields, which were long and cumbersome ([#1292](https://github.com/burningmantech/ranger-ims-server/pull/1292), [#1365](https://github.com/burningmantech/ranger-ims-server/pull/1365))
- Stopped showing empty locations in the UI as "(?:?)@?", but rather as just an empty string ([#1362](https://github.com/burningmantech/ranger-ims-server/pull/1362))
- Tightened security on the personnel endpoint, by restricting it to those with at least readIncident permission, and by removing Ranger email addresses from the response ([#1355](https://github.com/burningmantech/ranger-ims-server/pull/1355), [#1317](https://github.com/burningmantech/ranger-ims-server/pull/1317))

### Added

- Added full Unicode support to IMS. All text fields now accept previously unsupported characters, like those from Cyrillic, Chinese, emoji, and much more ([#1353](https://github.com/burningmantech/ranger-ims-server/issues/1353))
- Started doing client-side retries on any EventSource connection failures. This should mean that an IMS web session will be better kept in sync with incident updates, in particular in the off-season, when IMS is running on AWS ([#1389](https://github.com/burningmantech/ranger-ims-server/pull/1389))

### Fixed

- Made incident printouts look much better ([#1382](https://github.com/burningmantech/ranger-ims-server/pull/1382))
- Fixed bug that caused the incident page to reload data multiple times for each incident update ([#1369](https://github.com/burningmantech/ranger-ims-server/issues/1369))

## 2024-10

### Changed

- Resolved IMS's longstanding 6-open-tab limitation, by using a BroadcastChannel to share one EventSource connection between tabs ([#1320](https://github.com/burningmantech/ranger-ims-server/issues/1320), [#1322](https://github.com/burningmantech/ranger-ims-server/pull/1322))
- Changed login screen to encourage users to log in by email address, rather than by Ranger handle ([#1293](https://github.com/burningmantech/ranger-ims-server/pull/1293))
- Optimized the API calls that back the incidents endpoint. This speeds up the web UI incidents table load by around 3x ([#1349](https://github.com/burningmantech/ranger-ims-server/pull/1349), [#1324](https://github.com/burningmantech/ranger-ims-server/issues/1324))

### Added

- Added groupings to the "add incident report" dropdown, which emphasize which incident reports are or are not attached to any other incident. This also simplified the sort order for that list ([#1321](https://github.com/burningmantech/ranger-ims-server/pull/1321))

### Fixed

- Stopped using hardcoded 1-hour limit on IMS sessions; used timeout from JWT instead ([#1301](https://github.com/burningmantech/ranger-ims-server/pull/1301))
- Got rid of the browser popup alerts that occurred frequently on JavaScript errors. Instead, error messages will now be written to a text field near the top of each page ([#1335](https://github.com/burningmantech/ranger-ims-server/pull/1335))

## 2024-01

### Added

- Added "Changes you made may not be saved" browser popup when a user might otherwise lose data on incident entries and incident report entries ([#1088](https://github.com/burningmantech/ranger-ims-server/pull/1088))

### Fixed

- Do case-insensitive sorting of Ranger handles on incident page ([#1089](https://github.com/burningmantech/ranger-ims-server/pull/1089))
