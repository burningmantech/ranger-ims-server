# Changelog

This is the changelog for ranger-ims-server. This is intended to summarize changes over time,
for example to inform the Operator team each event of any differences to expect.

This file must use the [Common Changelog format](https://common-changelog.org/), with the variation
that we use months rather than version numbers. We don't include dependency version upgrades in the
changelog, as those would pollute this too much.

## 2024-10

### Added

- Encourage users to log in by email address, rather than by Ranger handle ([#1293](https://github.com/burningmantech/ranger-ims-server/pull/1293))
- Use text and datalist for "Add Ranger" on incident page, rather than a select ([#1292](https://github.com/burningmantech/ranger-ims-server/pull/1292))

### Fixed

- Stop using hardcoded 1-hour limit on IMS sessions; use timeout from JWT instead ([#1301](https://github.com/burningmantech/ranger-ims-server/pull/1301))

## 2024-01

### Added

- Help user not lose unsaved changes to incident entries and incident report entries ([#1088](https://github.com/burningmantech/ranger-ims-server/pull/1088))

### Fixed

- Do case-insensitive sorting of Ranger handles on incident page ([#1089](https://github.com/burningmantech/ranger-ims-server/pull/1089))
