"""Step 6+7 — montaggio: video pulito + voce IT + B-roll + overlay → montaggio.mp4

Sincronizzazione ([montaggio] adattamento):
  auto     voce più lunga del video → la voce viene accelerata fino a max_velocita (imp. 1.08),
           l'eventuale eccesso è coperto congelando l'ultimo fotogramma; voce più corta →
           il video viene tagliato alla fine della voce + `coda` secondi.
  congela  come auto ma senza mai accelerare la voce.
  nessuno  durata = video; la voce viene troncata o completata col silenzio.

B-roll (sostituzione scene non adatte all'Italia) — le clip le scegli tu, qui le posizioni:
  [[montaggio.broll]]
  clip = "broll/supermercato.mp4"   # relativo alla cartella del progetto
  inizio = 12.0                      # secondi sulla timeline finale
  fine = 15.5
  da = 0.0                           # (opz.) da che secondo della clip partire

Overlay PNG (titoli, offerte, loghi; generabili con `localizza.py grafica`):
  [[montaggio.overlay]]
  immagine = "overlay_offerta.png"
  inizio = 20.0
  fine = 26.0
  x = "(W-w)/2"           # espressioni ffmpeg: W,H = video, w,h = immagine
  y = "H*0.72"
  larghezza = 900         # (opz.) ridimensiona l'immagine in pixel
  dissolvenza = 0.3       # (opz.) fade in/out in secondi
"""

from __future__ import annotations

from . import ff
from .config import MONTAGGIO, VOICEOVER, ErroreConfig, Progetto


def calcola_tempi(durata_video: float, durata_voce: float, modo: str, max_velocita: float,
                  coda: float) -> tuple[float, float, float]:
    """→ (durata_finale, velocità_voce, secondi_di_fermo_immagine_finale)"""
    if modo == "nessuno":
        return durata_video, 1.0, 0.0
    if modo not in ("auto", "congela"):
        raise ErroreConfig(f"[montaggio] adattamento sconosciuto: {modo!r}")
    velocita = 1.0
    if durata_voce > durata_video and modo == "auto":
        velocita = min(durata_voce / durata_video, max_velocita)
    voce = durata_voce / velocita
    finale = voce + coda
    fermo = max(0.0, finale - durata_video)
    return round(finale, 3), round(velocita, 4), round(fermo, 3)


def esegui(p: Progetto, verbose: bool = False) -> None:
    cfg = p.sezione("montaggio")
    video = p.sorgente_video()
    voce = p.richiedi(VOICEOVER)
    W, H = ff.dimensioni(video)
    dv, da = ff.durata(video), ff.durata(voce)
    D, vel, fermo = calcola_tempi(dv, da, cfg.get("adattamento", "auto"),
                                  float(cfg.get("max_velocita", 1.08)), float(cfg.get("coda", 0.5)))

    args = ["-i", video, "-i", voce]
    filtri: list[str] = []
    n_in = 2

    # --- video base: eventuale fermo immagine finale
    v = "[0:v]setsar=1"
    if fermo > 0:
        v += f",tpad=stop_mode=clone:stop_duration={fermo}"
    filtri.append(v + "[v0]")
    cur = "v0"

    # --- B-roll
    for i, b in enumerate(cfg.get("broll", [])):
        clip = p.percorso(b["clip"])
        if not clip.exists():
            raise ErroreConfig(f"Clip B-roll non trovata: {clip}")
        t0, t1 = float(b["inizio"]), float(b["fine"])
        if not 0 <= t0 < t1:
            raise ErroreConfig(f"B-roll {clip.name}: inizio/fine non validi ({t0}–{t1})")
        dur_clip = ff.durata(clip) - float(b.get("da", 0))
        if dur_clip < (t1 - t0) - 0.05:
            print(f"  ! {clip.name} dura {dur_clip:.1f}s ma copre {t1 - t0:.1f}s: l'ultimo fotogramma resterà fermo")
        args += ["-ss", str(b.get("da", 0)), "-t", str(t1 - t0), "-i", clip]
        filtri.append(f"[{n_in}:v]scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,"
                      f"tpad=stop_mode=clone:stop_duration={t1 - t0},trim=duration={t1 - t0},"
                      f"setpts=PTS-STARTPTS+{t0}/TB[b{i}]")
        filtri.append(f"[{cur}][b{i}]overlay=0:0:enable='between(t,{t0},{t1})':eof_action=pass[vb{i}]")
        cur = f"vb{i}"
        n_in += 1

    # --- overlay PNG
    for i, o in enumerate(cfg.get("overlay", [])):
        img = p.percorso(o["immagine"])
        if not img.exists():
            raise ErroreConfig(f"Overlay non trovato: {img}")
        t0, t1 = float(o["inizio"]), float(o["fine"])
        args += ["-loop", "1", "-t", str(D), "-i", img]
        catena = f"[{n_in}:v]format=rgba"
        if o.get("larghezza"):
            catena += f",scale={int(o['larghezza'])}:-1"
        fd = float(o.get("dissolvenza", 0))
        if fd > 0:
            catena += f",fade=t=in:st={t0}:d={fd}:alpha=1,fade=t=out:st={t1 - fd}:d={fd}:alpha=1"
        filtri.append(catena + f"[o{i}]")
        x, y = o.get("x", "(W-w)/2"), o.get("y", "(H-h)/2")
        filtri.append(f"[{cur}][o{i}]overlay=x='{x}':y='{y}':enable='between(t,{t0},{t1})'[vo{i}]")
        cur = f"vo{i}"
        n_in += 1

    # --- audio: voce IT (eventualmente accelerata) + audio originale opzionale (ambiente)
    a = "[1:a]aresample=48000"
    if vel != 1.0:
        a += f",atempo={vel}"
    filtri.append(a + f",apad,atrim=0:{D}[voce]")
    vol_orig = float(cfg.get("volume_audio_originale", 0))
    if vol_orig > 0 and ff.ha_audio(video):
        filtri.append(f"[0:a]aresample=48000,volume={vol_orig},apad,atrim=0:{D}[orig]")
        filtri.append("[voce][orig]amix=inputs=2:duration=first:normalize=0[aout]")
        a_out = "aout"
    else:
        a_out = "voce"

    out = p.file(MONTAGGIO)
    ff.esegui([*args, "-filter_complex", ";".join(filtri), "-map", f"[{cur}]", "-map", f"[{a_out}]",
               "-t", str(D), *ff.ENC_INTERMEDIO, out], verbose)
    info = f"video {dv:.1f}s, voce {da:.1f}s → {D:.1f}s"
    if vel != 1.0:
        info += f", voce accelerata x{vel}"
    if fermo > 0:
        info += f", fermo immagine finale {fermo:.1f}s"
    print(f"✓ {out} ({info})")
