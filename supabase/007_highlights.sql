-- Momenti salienti di ogni partita analizzata (rimonta, mosse brillanti). Esegui dopo 006.
alter table games add column if not exists highlights jsonb;
