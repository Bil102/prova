# Localizzazione video EN → IT

Pipeline a step per adattare video pubblicitari americani al mercato italiano. Ogni step è un
comando separato: puoi fermarti, correggere a mano un file e ripartire.

| # | Step | Comando | Output | Come |
|---|---|---|---|---|
| 1 | Ricezione video | `init video.mp4 --nome spot01` | `progetti/spot01/originale.mp4` | copia + `progetto.toml` |
| 2 | Rimozione sottotitoli | `pulisci` | `video_clean.mp4` | manuale (Vmake web) o ffmpeg sfoca/delogo/ritaglia |
| 3 | Trascrizione | `trascrivi` | `transcript_en.txt` (+ `.json`) | Whisper: API OpenAI o locale |
| 4 | Adattamento | `traduci` → `verifica` | `script_it.txt`, `note_adattamento.md` | Claude + [regole](regole_adattamento.md) + controllo automatico |
| 5 | Voce | `voce` | `voiceover_it.mp3` (+ `voce/NN_speaker.mp3`) | API ElevenLabs |
| – | Grafiche | `grafica NOME "TESTO"` | `overlay_NOME.png` | Pillow |
| 6–7 | Montaggio + B-roll | `monta` | `montaggio.mp4` | ffmpeg |
| 8 | Musica | `musica` | `con_musica.mp4` | ffmpeg, con ducking sotto la voce |
| 9 | Export | `esporta` | `video_finale_it.mp4` | ffmpeg (H.264/AAC, loudness −14 LUFS) |

**Divisione attuale del lavoro:** gli step 2–5 (sottotitoli, trascrizione, adattamento, voce)
sono automatizzati; montaggio, B-roll, musica ed export (6–9) si fanno a mano in CapCut partendo
da `video_clean.mp4` + `voiceover_it.mp3`. Gli step `monta`/`musica`/`esporta` restano disponibili
se in futuro si vuole automatizzare anche quella parte.

`stato` mostra cosa è già fatto; `tutto` esegue gli step 2→5 in sequenza e si ferma al primo
intoppo (`--da voce` per riprendere da lì, `--a esporta` per proseguire fino all'export ffmpeg).

## Setup

```bash
# ffmpeg: brew install ffmpeg  (macOS)  |  sudo apt install ffmpeg  (Linux)
pip install -r requirements.txt
cp .env.example .env      # e inserisci le chiavi API
```

Prerequisiti da verificare:
- **ElevenLabs** — chiave in Settings → API Keys; il `voice_id` di ogni voce si copia dalla Voice Library.
- **Whisper** — `backend = "openai"` (default: serve `OPENAI_API_KEY`, veloce, a pagamento) oppure
  `backend = "locale"` (`pip install faster-whisper`, gratis, lento senza GPU).
- **Claude** — `ANTHROPIC_API_KEY` per lo step `traduci`. In alternativa puoi tradurre in sessione con
  Claude Code: le regole sono già caricate tramite `CLAUDE.md`.
- **Vmake** — SDK ufficiale incluso in `vendor/` (installato da `requirements.txt`). Chiavi
  `MT_AK`/`MT_SK` da vmake.ai/developers; poi `[pulizia] metodo = "vmake"`. Il task predefinito è
  `videoscreenclear` (rimozione testo dal video); l'elenco dei task disponibili si vede con
  `action-api-sdk catalog --media-type video`. Ogni esecuzione consuma quota Vmake; se il polling
  si interrompe, rilanciando `pulisci` si riprende lo stesso lavoro senza ricaricare il video.
  Senza chiavi: `metodo = "manuale"` (video pulito scaricato dal sito e salvato come `video_clean.mp4`).

## Flusso tipico

```bash
python3 localizza.py init ~/Downloads/spot_usa.mp4 --nome spot01
# modifica progetti/spot01/progetto.toml: [narratore] genere, [voce.speaker], [pulizia]...

python3 localizza.py pulisci   progetti/spot01
python3 localizza.py trascrivi progetti/spot01
python3 localizza.py traduci   progetti/spot01
```

Se Claude introduce un nome italiano non ancora scelto (o ha dubbi), lo step si ferma: il testo
va in `script_it.bozza.txt` e le sostituzioni in `note_adattamento.md`. Per proseguire aggiungi il
nome in `[nomi]` (es. `Rick = "Marco"`) e rilancia, oppure `traduci --accetta` per usare la bozza.
Rileggi sempre `script_it.txt`: puoi modificarlo a mano e poi `verifica` lo ricontrolla.

```bash
python3 localizza.py voce    progetti/spot01          # rigenera solo i blocchi modificati
python3 localizza.py voce    progetti/spot01 --solo 3 # rigenera il blocco 3 (es. intonazione sbagliata)
python3 localizza.py grafica progetti/spot01 offerta "COMPRA 2,\nPRENDINE 2 GRATIS" --sfondo "#E63946E6"
python3 localizza.py monta   progetti/spot01
python3 localizza.py musica  progetti/spot01
python3 localizza.py esporta progetti/spot01
```

### Più speaker
In `script_it.txt` apri ogni blocco con una riga `[Nome]` e assegna una voce a ogni nome:

```
[Marco]
Non ci credevo neanche io.

[Giulia]
E invece funziona davvero.
```
```toml
[voce.speaker]
Marco = "voice_id_1"
Giulia = "voice_id_2"
```

### Sostituzione scene (B-roll IT)
La scelta della clip resta umana; posizionamento, scala e sync sono automatici:

```toml
[[montaggio.broll]]
clip = "broll/supermercato_italiano.mp4"
inizio = 12.0     # secondi sulla timeline finale
fine = 15.5
```

### Sincronizzazione voce/video
Con `adattamento = "auto"`: se la voce italiana è più lunga del video viene accelerata
leggermente (max `max_velocita`, default ×1.08) e l'eventuale eccesso è coperto congelando
l'ultimo fotogramma; se è più corta il video viene tagliato a fine voce + `coda`.

## Limiti rispetto a CapCut
Transizioni, color grading ed editing creativo fine restano manuali: in quel caso usa
`montaggio.mp4` o `voiceover_it.mp3` come materiale per CapCut e salta gli step successivi.

## Test
```bash
pip install pytest && python3 -m pytest -q tests
```
Usano video sintetici generati con ffmpeg e API simulate: nessun costo, nessuna chiave richiesta.
