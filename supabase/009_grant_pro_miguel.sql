-- Regalo: piano Pro senza scadenza per un utente specifico.
-- Esegui nel SQL Editor di Supabase. Funziona anche se la riga config_utenti non esiste ancora.
insert into config_utenti (user_email, tier, data_scadenza)
values ('jmtmargarido@gmail.com', 'Pro', null)
on conflict (user_email) do update set tier = 'Pro', data_scadenza = null;

-- Verifica
select user_email, tier, data_scadenza from config_utenti where user_email = 'jmtmargarido@gmail.com';
