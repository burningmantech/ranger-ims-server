/* This migration fixes an FK and adds the new ATTACHED_FILE column. */

/* Firstly, fix up a foreign key on FIELD_REPORT__REPORT_ENTRY, which
   may still reference the renamed "INCIDENT_REPORT" table. */

alter table `FIELD_REPORT__REPORT_ENTRY`
    drop foreign key if exists `INCIDENT_REPORT__REPORT_ENTRY_ibfk_2`;
alter table `FIELD_REPORT__REPORT_ENTRY`
    drop foreign key if exists `FIELD_REPORT__REPORT_ENTRY_ibfk_2`;

alter table `FIELD_REPORT__REPORT_ENTRY`
    add constraint `FIELD_REPORT__REPORT_ENTRY___FIELD_REPORT_FK`
        foreign key if not exists (`EVENT`, `FIELD_REPORT_NUMBER`) references `FIELD_REPORT` (`EVENT`, `NUMBER`);

/* Add support for file attachments */

alter table `REPORT_ENTRY`
    add column `ATTACHED_FILE` varchar(128)
;

/* Update schema version */

update `SCHEMA_INFO` set `VERSION` = 10;
