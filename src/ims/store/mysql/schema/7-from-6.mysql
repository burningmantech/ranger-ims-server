/* Switch all tables to utf8mb4 character set (from latin1) to support Unicode text in IMS */

/* This is the only constraint that needs to be dropped and re-added, since it includes varchars as part of the key. */
alter table `INCIDENT` drop constraint `INCIDENT_ibfk_2`;

alter table `CONCENTRIC_STREET` convert to character set utf8mb4 collate utf8mb4_unicode_ci;
alter table `EVENT` convert to character set utf8mb4 collate utf8mb4_unicode_ci;
alter table `EVENT_ACCESS` convert to character set utf8mb4 collate utf8mb4_unicode_ci;
alter table `INCIDENT` convert to character set utf8mb4 collate utf8mb4_unicode_ci;
alter table `INCIDENT_REPORT` convert to character set utf8mb4 collate utf8mb4_unicode_ci;
alter table `INCIDENT_REPORT__REPORT_ENTRY` convert to character set utf8mb4 collate utf8mb4_unicode_ci;
alter table `INCIDENT_TYPE` convert to character set utf8mb4 collate utf8mb4_unicode_ci;
alter table `INCIDENT__INCIDENT_TYPE` convert to character set utf8mb4 collate utf8mb4_unicode_ci;
alter table `INCIDENT__RANGER` convert to character set utf8mb4 collate utf8mb4_unicode_ci;
alter table `INCIDENT__REPORT_ENTRY` convert to character set utf8mb4 collate utf8mb4_unicode_ci;
alter table `REPORT_ENTRY` convert to character set utf8mb4 collate utf8mb4_unicode_ci;
alter table `SCHEMA_INFO` convert to character set utf8mb4 collate utf8mb4_unicode_ci;

alter table `INCIDENT` add constraint `INCIDENT_ibfk_2` foreign key (`EVENT`, `LOCATION_CONCENTRIC`) references `CONCENTRIC_STREET` (`EVENT`, `ID`);

/* Update schema version */

update `SCHEMA_INFO` set VERSION = 7;
