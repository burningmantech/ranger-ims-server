# Changelog

This is the changelog for ranger-ims-server. This is intended to summarize changes over time. It's
probably too verbose for consumption by general users of IMS, but it might be useful for anyone
trying to follow along with IMS's progression as a system.

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

## 2025-01

<!-- TODO: document keyboard shortcut updates, once they've settled down a bit -->

### Changed

- Sped up the incidents page background refresh by only refreshing the incident that changed. Previously we reloaded all the data from the server for the whole table on any update to any incident. https://github.com/burningmantech/ranger-ims-server/pull/1493
- Improved background refresh resiliency by having clients track their last received server-side event. https://github.com/burningmantech/ranger-ims-server/pull/1504
- Created a slight pause after search field input prior to actually running the search. This will reduce perceived latency in typing/deleting in the search field. https://github.com/burningmantech/ranger-ims-server/issues/1481 https://github.com/burningmantech/ranger-ims-server/pull/1483
- Started Field Report numbering from 1 each event, as we already did for Incidents. https://github.com/burningmantech/ranger-ims-server/pull/1506
- Enhanced the "permission denied" error page, to make it more descriptive for when we block access for an authenticated Ranger. https://github.com/burningmantech/ranger-ims-server/pull/1530
- Stopped showing Ranger legal names in IMS; started linking from Ranger handles into Clubhouse person pages instead. https://github.com/burningmantech/ranger-ims-server/issues/1536

### Added

- Introduced "striking" of report entries. This allows a user to hide an outdated/inaccurate entry, such that it doesn't appear by default on the Incident or Field Report page. https://github.com/burningmantech/ranger-ims-server/issues/249
- Added help modals, toggled by pressing "?", which show keyboard shortcuts for the current page. https://github.com/burningmantech/ranger-ims-server/issues/1482
- Started publishing Field Report entity updates to the web clients (via server-sent events), and started automatically background-updating the Field Reports (table) and Field Report pages on updates. https://github.com/burningmantech/ranger-ims-server/issues/1498
- Also started background-updating the Incident page based on Field Report updates, so that the user shouldn't ever need to reload an Incident page to pick up updates from the server. https://github.com/burningmantech/ranger-ims-server/pull/1555
- Added a help link from the Incident page to documentation about the meaning of the many Incident Types. https://github.com/burningmantech/ranger-ims-server/pull/1512
- Added Subresource Integrity checks to our JavaScript dependencies, improving our security against supply chain attacks. https://github.com/burningmantech/ranger-ims-server/issues/1517
- Got rid of the "requireActive" global setting, and changed it into a "validity" property of each event permission instead. This allows us to specify which permissions should be granted all year, and which should only be available to Rangers while they are on-playa. https://github.com/burningmantech/ranger-ims-server/issues/1540

### Removed

- Dropped "\*\*"-style ACLs, which we didn't use and didn't actually work at all. https://github.com/burningmantech/ranger-ims-server/pull/1553

### Fixed

- Removed confusing messaging from login screen when a user was already logged in. https://github.com/burningmantech/ranger-ims-server/pull/1511 https://github.com/burningmantech/ranger-ims-server/issues/1508

## 2024-12

### Changed

- Upgraded to Bootstrap 5 (from 3). This unlocks a bunch of neat new features. It required many minor UI changes https://github.com/burningmantech/ranger-ims-server/pull/1445
- Started collapsing the Instructions on the Field Report page by default https://github.com/burningmantech/ranger-ims-server/pull/1445
- Modernized the login screen a bit, by using form-floating input fields https://github.com/burningmantech/ranger-ims-server/pull/1445

### Added

- Added dark mode and a light/dark mode toggler https://github.com/burningmantech/ranger-ims-server/pull/1445 https://github.com/burningmantech/ranger-ims-server/issues/290
- Started showing the (currently read-only) IMS number on the Field Report page https://github.com/burningmantech/ranger-ims-server/pull/1429
- Added a button on the Field Report page that allows instant creation of a new Incident based on that Field Report. This button will only appear for users with writeIncident permission (e.g. Operators and Shift Command) https://github.com/burningmantech/ranger-ims-server/pull/1429

### Fixed

- Resolved a longstanding bug in which a user would be forced to log in twice in a short period of time. https://github.com/burningmantech/ranger-ims-server/pull/1456
- Fixed a glitch in which the placeholder text for the "Summary" field was never showing up on the Incident and Field Report pages. We simultaneously altered the Field Report summary placeholder to suggest the user include an IMS number in that field. https://github.com/burningmantech/ranger-ims-server/pull/1443

## 2024-11

### Changed

- Switched to text-fields with datalists for "Add Ranger" and "Add Incident Types" on the incident page. Previously we used select dropdowns, which were long and cumbersome https://github.com/burningmantech/ranger-ims-server/pull/1292, https://github.com/burningmantech/ranger-ims-server/pull/1365
- Stopped showing empty locations in the UI as "(?:?)@?", but rather as just an empty string https://github.com/burningmantech/ranger-ims-server/pull/1362
- Tightened security on the personnel endpoint, by restricting it to those with at least readIncident permission, and by removing Ranger email addresses from the response https://github.com/burningmantech/ranger-ims-server/pull/1355, https://github.com/burningmantech/ranger-ims-server/pull/1317
- Made the incidents table load another 2x faster, by not retrieving system-generated report entries as part of that call. This should make the table more responsive too https://github.com/burningmantech/ranger-ims-server/pull/1396
- Tweaked the navbar's formatting to align better with Clubhouse https://github.com/burningmantech/ranger-ims-server/pull/1394
- On incident page, for a brand-new incident, stopped scrolling down to focus on the "add entry" box. Instead the page will focus on the summary field in that case. https://github.com/burningmantech/ranger-ims-server/pull/1419
- Started hiding system-generated incident history by default on the incident page. This can still be toggled by the "show history" checkbox, but the default is now that this is unchecked https://github.com/burningmantech/ranger-ims-server/pull/1421

### Added

- Added an Incident Type filter to the Incidents page https://github.com/burningmantech/ranger-ims-server/pull/1401
- Added full Unicode support to IMS. All text fields now accept previously unsupported characters, like those from Cyrillic, Chinese, emoji, and much more https://github.com/burningmantech/ranger-ims-server/issues/1353
- Started doing client-side retries on any EventSource connection failures. This should mean that an IMS web session will be better kept in sync with incident updates, in particular in the off-season, when IMS is running on AWS https://github.com/burningmantech/ranger-ims-server/pull/1389
- Added a warning banner to non-production instances of the web UI, to make sure people don't accidentally put prod data into non-production IMS instances. https://github.com/burningmantech/ranger-ims-server/issues/1366
- Started showing full datetimes, including time zone, when a user hovers over a time on the incidents page. All times have always been in the user's locale, but this wasn't indicated anywhere https://github.com/burningmantech/ranger-ims-server/pull/1412

### Removed

- Got rid of Moment.js dependency, as it's deprecated and we're able to use the newer Intl JavaScript browser construct instead https://github.com/burningmantech/ranger-ims-server/pull/1412

### Fixed

- Made incident printouts look much better https://github.com/burningmantech/ranger-ims-server/pull/1382, https://github.com/burningmantech/ranger-ims-server/pull/1405
- Fixed bug that caused the incident page to reload data multiple times for each incident update https://github.com/burningmantech/ranger-ims-server/issues/1369
- Uncovered and resolved some subtle XSS vulnerabilities https://github.com/burningmantech/ranger-ims-server/pull/1402

## 2024-10

### Changed

- Resolved IMS's longstanding 6-open-tab limitation, by using a BroadcastChannel to share one EventSource connection between tabs https://github.com/burningmantech/ranger-ims-server/issues/1320, https://github.com/burningmantech/ranger-ims-server/pull/1322
- Changed login screen to encourage users to log in by email address, rather than by Ranger handle https://github.com/burningmantech/ranger-ims-server/pull/1293
- Optimized the API calls that back the incidents endpoint. This speeds up the web UI incidents table load by around 3x https://github.com/burningmantech/ranger-ims-server/pull/1349, https://github.com/burningmantech/ranger-ims-server/issues/1324

### Added

- Added groupings to the "add Field Report" dropdown, which emphasize which Field Reports are or are not attached to any other incident. This also simplified the sort order for that list https://github.com/burningmantech/ranger-ims-server/pull/1321

### Fixed

- Stopped using hardcoded 1-hour duration limit on IMS sessions, allowing us to make sessions that will last for a whole shift on playa. https://github.com/burningmantech/ranger-ims-server/pull/1301
- Got rid of the browser popup alerts that occurred frequently on JavaScript errors. Instead, error messages will now be written to a text field near the top of each page https://github.com/burningmantech/ranger-ims-server/pull/1335

## 2024-01

### Added

- Added "Changes you made may not be saved" browser popup when a user might otherwise lose data on incident entries and Field Report entries https://github.com/burningmantech/ranger-ims-server/pull/1088

### Fixed

- Do case-insensitive sorting of Ranger handles on incident page https://github.com/burningmantech/ranger-ims-server/pull/1089
