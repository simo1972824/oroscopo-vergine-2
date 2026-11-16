# oroscopo-vergine-2

Invio automatico via email dell'**oroscopo giornaliero della Vergine ♍** alle **06:00 (ora Europe/Rome)**,
tramite GitHub Actions. Il corpo della mail riporta gli estratti delle previsioni recuperate online
(Style Corriere, Amica, Oggi.it) con le fonti e il disclaimer, nello stesso formato di AstroVibe.

## Come funziona

- `.github/workflows/oroscopo-vergine.yml` gira con cron alle `04:00` e `05:00` UTC:
  in inverno (CET, UTC+1) 06:00 a Roma = 05:00 UTC, in estate (CEST, UTC+2) = 04:00 UTC.
  Lo script (`scripts/invia_oroscopo.py`) ha una guardia: invia **solo se l'ora di Roma è 06:00**,
  quindi viene mandata una sola email al giorno all'orario giusto. È anche avviabile a mano
  (`workflow_dispatch`) per i test.
- Lo script legge le pagine del giorno corrente, compone la mail e la invia via SMTP Gmail
  (`smtp.gmail.com:465`) usando una **app password**.

## Setup (una volta sola)

1. In questo repo: **Settings → Secrets and variables → Actions → New repository secret** e aggiungi:
   - `GMAIL_USER` = indirizzo Gmail completo (es. `debianchisimone@gmail.com`)
   - `GMAIL_APP_PASSWORD` = app password di 16 caratteri generata su
     **Account Google → Sicurezza → Verifica in due passaggi → Password per le app**
     (senza spazi; non la password dell'account)
   - `MAIL_TO` (opzionale) = destinatario; se vuoto viene usato `GMAIL_USER`
2. Non committare mai la app password: vive solo nei secret del repo.

## Test manuale

**Actions → "Oroscopo Vergine 06:00" → Run workflow**: lo script ignora la guardia delle 06:00
e invia subito la mail di oggi.

## Disattivazione

Rimuovi le righe `schedule:` dal workflow oppure metti in pausa il workflow dalla pagina Actions.
