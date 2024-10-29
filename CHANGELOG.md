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

## 2024-10

### Changed

- Resolved IMS's longstanding 6-open-tab limitation ([#1320](https://github.com/burningmantech/ranger-ims-server/issues/1320)) ([#1322](https://github.com/burningmantech/ranger-ims-server/pull/1322))
- Changed login screen to encourage users to log in by email address, rather than by Ranger handle ([#1293](https://github.com/burningmantech/ranger-ims-server/pull/1293))
- Used text and datalist for "Add Ranger" on incident page, rather than a select field ([#1292](https://github.com/burningmantech/ranger-ims-server/pull/1292))
- Removed email address from the personnel API endpoint ([#1317](https://github.com/burningmantech/ranger-ims-server/pull/1317))

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
