/* this migration is about renaming INCIDENT_REPORT to FIELD_REPORT */

alter table `INCIDENT_REPORT__REPORT_ENTRY` rename column `INCIDENT_REPORT_NUMBER` to `FIELD_REPORT_NUMBER`, rename to `FIELD_REPORT__REPORT_ENTRY`;
alter table `INCIDENT_REPORT` rename to `FIELD_REPORT`;

/* Update schema version */

update `SCHEMA_INFO` set `VERSION` = 8;
