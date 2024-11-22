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
- Switched to text-fields with datalists for "Add Ranger" and "Add Incident Types" on the incident page. Previously we used select dropdowns, which were long and cumbersome ([#1292](https://github.com/burningmantech/ranger-ims-server/pull/1292), [#1365](https://github.com/burningmantech/ranger-ims-server/pull/1365))
- Stopped showing empty locations in the UI as "(?:?)@?", but rather as just an empty string ([#1362](https://github.com/burningmantech/ranger-ims-server/pull/1362))
- Tightened security on the personnel endpoint, by restricting it to those with at least readIncident permission, and by removing Ranger email addresses from the response ([#1355](https://github.com/burningmantech/ranger-ims-server/pull/1355), [#1317](https://github.com/burningmantech/ranger-ims-server/pull/1317))
- Made the incidents table load another 2x faster, by not retrieving system-generated report entries as part of that call. This should make the table more responsive too ([#1396](https://github.com/burningmantech/ranger-ims-server/pull/1396))
- Tweaked the navbar's formatting to align better with Clubhouse ([#1394](https://github.com/burningmantech/ranger-ims-server/pull/1394))
- On incident page, for a brand-new incident, stopped scrolling down to focus on the "add entry" box. Instead the page will focus on the summary field in that case. ([#1419](https://github.com/burningmantech/ranger-ims-server/pull/1419))
- Started hiding system-generated incident history by default on the incident page. This can still be toggled by the "show history" checkbox, but the default is now that this is unchecked ([#1421](https://github.com/burningmantech/ranger-ims-server/pull/1421))

### Added

- Added an Incident Type filter to the Incidents page ([#1401](https://github.com/burningmantech/ranger-ims-server/pull/1401))
- Added full Unicode support to IMS. All text fields now accept previously unsupported characters, like those from Cyrillic, Chinese, emoji, and much more ([#1353](https://github.com/burningmantech/ranger-ims-server/issues/1353))
- Started doing client-side retries on any EventSource connection failures. This should mean that an IMS web session will be better kept in sync with incident updates, in particular in the off-season, when IMS is running on AWS ([#1389](https://github.com/burningmantech/ranger-ims-server/pull/1389))
- Added a warning banner to non-production instances of the web UI, to make sure people don't accidentally put prod data into non-production IMS instances. [(#1366](https://github.com/burningmantech/ranger-ims-server/issues/1366))
- Started showing full datetimes, including time zone, when a user hovers over a time on the incidents page. All times have always been in the user's locale, but this wasn't indicated anywhere ([#1412](https://github.com/burningmantech/ranger-ims-server/pull/1412))

### Removed

- Got rid of Moment.js dependency, as it's deprecated and we're able to use the newer Intl JavaScript browser construct instead ([#1412](https://github.com/burningmantech/ranger-ims-server/pull/1412))

### Fixed

- Made incident printouts look much better ([#1382](https://github.com/burningmantech/ranger-ims-server/pull/1382), [#1405](https://github.com/burningmantech/ranger-ims-server/pull/1405))
- Fixed bug that caused the incident page to reload data multiple times for each incident update ([#1369](https://github.com/burningmantech/ranger-ims-server/issues/1369))
- Uncovered and resolved some subtle XSS vulnerabilities ([#1402](https://github.com/burningmantech/ranger-ims-server/pull/1402))

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
