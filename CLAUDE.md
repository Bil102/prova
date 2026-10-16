# Pipeline di localizzazione video EN → IT

Adattamento di video pubblicitari americani al mercato italiano. Pipeline a step, ognuno
eseguibile da riga di comando con `python3 localizza.py <step> progetti/<nome>`; tra uno step
e l'altro l'utente può intervenire a mano sui file del progetto.

Divisione del lavoro: Claude gestisce gli step 2–5 (pulizia sottotitoli, trascrizione,
adattamento, voce); montaggio, B-roll, musica ed export li fa l'utente in CapCut. Non lanciare
`monta`/`musica`/`esporta` salvo richiesta esplicita.

## Regole di adattamento — SEMPRE valide

Ogni volta che traduci, adatti o correggi un testo italiano per questo progetto (in chat o
modificando `script_it.txt`), applica **tutte** le regole in @regole_adattamento.md senza che
l'utente debba ripeterle. In particolare, prima di procedere:
- se il genere del narratore non è chiaro dal contesto o da `[narratore] genere` in
  `progetto.toml`, chiedilo;
- se sostituisci un nome di persona con uno non già presente in `[nomi]` di `progetto.toml`,
  segnalalo e attendi conferma.

Dopo aver scritto o modificato `script_it.txt`, lancia `python3 localizza.py verifica <progetto>`.

Dopo ogni adattamento proponi sempre all'utente 3-5 titoli grafici per l'hook (vedi "Titoli
grafici" nelle regole) e salvali in `progetti/<nome>/titoli_grafici.md`.

## Struttura
- `localizza.py` — CLI (un sottocomando per step, `tutto` per eseguirli in sequenza)
- `pipeline/` — un modulo per step: `pulisci`, `trascrivi`, `traduci`, `verifica`, `voce`,
  `grafica`, `monta`, `musica`, `esporta`; `config.py` contiene i nomi file standard
- `pipeline/modello_progetto.toml` — modello di configurazione copiato da `init`
- `progetti/<nome>/` — un video per cartella (non versionata): `progetto.toml` + file di lavoro
- Chiavi API in `.env` (vedi `.env.example`), mai nel codice

## Convenzioni
- Codice, messaggi e commenti in italiano; nomi file di output come da specifica
  (`video_clean.mp4`, `transcript_en.txt`, `script_it.txt`, `voiceover_it.mp3`,
  `overlay_*.png`, `video_finale_it.mp4`).
- ffmpeg viene chiamato solo tramite `pipeline/ff.py`.
- Test: `python3 -m pytest -q tests` (media sintetici, API simulate; nessun costo).
