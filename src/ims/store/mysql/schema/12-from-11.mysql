/*
  Change the problematic primary key for INCIDENT__RANGER,
  which frequently causes transaction contention/rollback. Having
  a VARCHAR as part of a primary key is ugly.

  These rollbacks would probably never happen in prod, but
  they were a nightmare in automated testing.

  Related:
  https://stackoverflow.com/questions/64789956/mariadb-innodb-deadlock-while-doing-many-inserts
*/

alter table `INCIDENT__RANGER`
    add column `ID` int not null auto_increment first,
    drop primary key,
    add primary key(`ID`);

/* Update schema version */

update `SCHEMA_INFO` set `VERSION` = 12;
