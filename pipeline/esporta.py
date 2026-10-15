"""Step 9 — export finale → video_finale_it.mp4

[export]
larghezza = 1080
altezza = 1920        # 1080x1920 verticale (Reels/TikTok); 1920x1080 orizzontale; 1080x1080 quadrato
adatta = "pad"        # pad = bande nere se il formato non coincide; crop = riempie tagliando; nessuno
fps = 30
crf = 20              # qualità x264 (più basso = migliore/più pesante)
preset = "medium"
audio_kbps = 192
loudnorm = -14        # LUFS target (standard social); false per disattivare
"""

from __future__ import annotations

from . import ff
from .config import CON_MUSICA, FINALE, MONTAGGIO, ErroreConfig, Progetto


def esegui(p: Progetto, verbose: bool = False) -> None:
    cfg = p.sezione("export")
    # usa la versione con musica se esiste ed è più recente del montaggio
    mont, mus = p.file(MONTAGGIO), p.file(CON_MUSICA)
    if mus.exists() and (not mont.exists() or mus.stat().st_mtime >= mont.stat().st_mtime):
        src = mus
    else:
        src = p.richiedi(MONTAGGIO)

    W, H = int(cfg.get("larghezza", 1080)), int(cfg.get("altezza", 1920))
    adatta = cfg.get("adatta", "pad")
    if adatta == "pad":
        v = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2:color=black"
    elif adatta == "crop":
        v = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H}"
    elif adatta == "nessuno":
        v = "scale=trunc(iw/2)*2:trunc(ih/2)*2"
    else:
        raise ErroreConfig(f"[export] adatta sconosciuto: {adatta!r}")
    v += f",setsar=1,fps={int(cfg.get('fps', 30))},format=yuv420p"

    a = "aresample=48000"
    lufs = cfg.get("loudnorm", -14)
    if lufs is not False:
        a = f"loudnorm=I={float(lufs)}:TP=-1.5:LRA=11," + a

    out = p.file(FINALE)
    ff.esegui(["-i", src, "-vf", v, "-af", a,
               "-c:v", "libx264", "-preset", cfg.get("preset", "medium"), "-crf", str(cfg.get("crf", 20)),
               "-c:a", "aac", "-b:a", f"{int(cfg.get('audio_kbps', 192))}k",
               "-movflags", "+faststart", out], verbose)
    print(f"✓ {out} (da {src.name}, {W}x{H})")
