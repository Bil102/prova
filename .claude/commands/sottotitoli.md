---
description: Mette i sottotitoli stile TikTok (riquadro bianco, testo nero) su uno o più video della cartella corrente
argument-hint: <video.mp4> [altri video]
---
Metti i sottotitoli ai video indicati: $ARGUMENTS

1. Se mancano, installa ffmpeg e i pacchetti Python `faster-whisper pillow numpy` (chiedi conferma solo la prima volta).
2. Per ogni video esegui, dalla cartella in cui si trova il video:
   `python <percorso del repository>/strumenti/sottotitoli.py "<video>" "<nome senza estensione>_sottotitoli.mp4"`
3. Controlla 3 fotogrammi del risultato (inizio, metà, fine): sottotitoli leggibili, nomi propri e "Revive Drum" con la maiuscola.
4. Rispondi in italiano, breve: nome del file creato, durata, numero di sottotitoli.
