-- Storico importato per account collegato (esegui dopo 004)
alter table profili_scacchi add column if not exists history_n int not null default 0;
