# Sottotitoli dal PC (sessione Claude Code locale)

Nella cartella dei video (es. Desktop\Sottotitoli video) apri il terminale e lancia `claude`, poi incolla:

> Clona https://github.com/Bil102/prova (branch `claude/pipeline-localizzazione-it`) in una sottocartella `prova`.
> Installa se mancano: ffmpeg, Python 3 e `pip install faster-whisper pillow numpy`.
> Per ogni video che ti indico in questa cartella esegui
> `python prova/strumenti/sottotitoli.py "<video>" "<nome>_sottotitoli.mp4"`
> e lascia il risultato nella stessa cartella.

Stile: riquadro bianco arrotondato, testo nero minuscolo (Montserrat, incluso in `risorse/font/`),
1-2 righe, al 68% dell'altezza; tempi presi da Whisper sull'audio del video.
