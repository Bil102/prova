"""Step 8 — musica di sottofondo → con_musica.mp4

[musica]
file = "musica/sottofondo.mp3"  # va in loop se più corta del video
volume = 0.15                   # volume della musica (1.0 = originale)
fade_in = 1.0
fade_out = 2.0
inizio = 0.0                    # da che secondo della traccia partire
ducking = true                  # abbassa automaticamente la musica quando parla la voce
"""

from __future__ import annotations

from . import ff
from .config import CON_MUSICA, MONTAGGIO, ErroreConfig, Progetto


def esegui(p: Progetto, verbose: bool = False) -> None:
    cfg = p.sezione("musica")
    if not cfg.get("file"):
        raise ErroreConfig("Nessuna musica configurata: imposta [musica] file in progetto.toml (o salta questo step)")
    traccia = p.percorso(cfg["file"])
    if not traccia.exists():
        raise ErroreConfig(f"File musica non trovato: {traccia}")
    src = p.richiedi(MONTAGGIO)
    D = ff.durata(src)
    fi, fo = float(cfg.get("fade_in", 1.0)), float(cfg.get("fade_out", 2.0))

    mus = (f"[1:a]aresample=48000,aformat=channel_layouts=stereo,atrim=0:{D},asetpts=PTS-STARTPTS,"
           f"volume={float(cfg.get('volume', 0.15))}")
    if fi > 0:
        mus += f",afade=t=in:st=0:d={fi}"
    if fo > 0:
        mus += f",afade=t=out:st={max(0.0, D - fo)}:d={fo}"
    filtri = [mus + "[mus]", "[0:a]aresample=48000,aformat=channel_layouts=stereo,asplit=2[voce][sc]"]
    if cfg.get("ducking", True):
        filtri.append("[mus][sc]sidechaincompress=threshold=0.02:ratio=6:attack=40:release=500[musd]")
    else:
        filtri.append("[sc]anullsink;[mus]anull[musd]")
    filtri.append("[voce][musd]amix=inputs=2:duration=first:normalize=0[a]")

    out = p.file(CON_MUSICA)
    ff.esegui(["-i", src, "-stream_loop", "-1", "-ss", str(cfg.get("inizio", 0)), "-i", traccia,
               "-filter_complex", ";".join(filtri), "-map", "0:v", "-map", "[a]",
               "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-t", str(D), out], verbose)
    print(f"✓ {out}")
