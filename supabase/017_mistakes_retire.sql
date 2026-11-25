-- v3.35: gli errori risolti escono dalla coda di ripasso.
-- Le schede già in casella 3-5 (ripassate 2+ volte) vengono considerate risolte.
update mistake_cards set box = 5, due_at = '2099-01-01T00:00:00Z' where box >= 3;
create index if not exists mistake_cards_due_idx on mistake_cards (user_email, box, due_at);
