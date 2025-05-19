/* This migration is about adding VALIDITY to EVENT_ACCESS */

alter table EVENT_ACCESS
    add column VALIDITY enum ('always', 'onsite')
    not null
    default 'always';

/* Update schema version */

update `SCHEMA_INFO` set `VERSION` = 9;
