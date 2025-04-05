/*
  Add an index on INCIDENT__RANGER

  I was a bit brash in 12-from-11. In removing EVENT and INCIDENT_NUMBER
  from the PK, I made our lookups into this table significantly slower.
  We can have the best of both worlds, by continuing to not have a VARCHAR
  as part of the PK, but also by having a (non-unique) index on the table.
*/

create index INCIDENT__RANGER_EVENT_INCIDENT_NUMBER_index
    on `INCIDENT__RANGER` (EVENT, INCIDENT_NUMBER);

/* Update schema version */

update `SCHEMA_INFO` set `VERSION` = 13;
