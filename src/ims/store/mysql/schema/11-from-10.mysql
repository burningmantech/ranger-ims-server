/*
  Change the problematic primary key for EVENT_ACCESS,
  which frequently causes transaction contention/rollback
  when multiple event accesses are being changed at the
  same time (for different events, event!). This seemed
  to arise because of the complex composite primary key
  (event (int), expression (varchar)), plus the complex
  transactions we were doing when setting ACLs.

  These rollbacks would probably never happen in prod, but
  they were a nightmare in automated testing.

  Related:
  https://stackoverflow.com/questions/64789956/mariadb-innodb-deadlock-while-doing-many-inserts
*/

alter table `EVENT_ACCESS`
    drop foreign key event_access_ibfk_1;

alter table `EVENT_ACCESS`
    add column `ID` int not null auto_increment first,
    drop primary key,
    add primary key(`ID`);

alter table `EVENT_ACCESS`
    add constraint event_access_ibfk_1
        foreign key (`EVENT`) references `EVENT` (`ID`);

/* Update schema version */

update `SCHEMA_INFO` set `VERSION` = 11;
