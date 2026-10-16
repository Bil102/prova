"""Step 5b — adatta velocità di video e voce per il montaggio in CapCut.

La voce italiana di ElevenLabs a velocità 1.0 risulta lenta, e di solito dura quanto il video
o poco più. Regola (come si faceva a mano in CapCut):
  - se, accelerando il video a `velocita_video` (1.1), la voce resta entro `max_velocita_voce`:
      video ×1.1 e voce accelerata per finire con il nuovo video;
  - altrimenti (voce molto più lunga del video): video invariato, si accelera solo la voce;
    se nemmeno così rientra entro `max_velocita_voce`, si avvisa (meglio accorciare il testo).

Output: video_adattato.mp4 (senza audio originale) + voiceover_adattato.mp3.
I file di partenza (video_clean.mp4, voiceover_it.mp3) restano invariati.
"""

from __future__ import annotations

from dataclasses import dataclass

from . import ff
from .config import VIDEO_ADATTATO, VIDEO_CLEAN, VOCE_ADATTATA, VOICEOVER, Progetto


@dataclass
class Piano:
    video: float   # fattore di velocità del video
    voce: float    # fattore di velocità della voce
    avviso: str = ""


def calcola(durata_video: float, durata_voce: float, velocita_video: float = 1.1,
            max_velocita_voce: float = 1.15, coda: float = 0.5) -> Piano:
    def fattore_voce(v: float) -> float:
        return durata_voce / max(durata_video / v - coda, 0.1)

    if fattore_voce(velocita_video) <= max_velocita_voce:
        return Piano(velocita_video, max(fattore_voce(velocita_video), 1.0))
    voce = max(fattore_voce(1.0), 1.0)
    if voce <= max_velocita_voce:
        return Piano(1.0, voce)
    return Piano(1.0, max_velocita_voce,
                 f"la voce è troppo lunga: anche a ×{max_velocita_voce} supera il video di "
                 f"{durata_voce / max_velocita_voce - durata_video:.1f}s — conviene accorciare il testo")


def esegui(p: Progetto, verbose: bool = False) -> Piano:
    cfg = p.sezione("adattamento")
    video, voce = p.richiedi(VIDEO_CLEAN), p.richiedi(VOICEOVER)
    piano = calcola(ff.durata(video), ff.durata(voce), float(cfg.get("velocita_video", 1.1)),
                    float(cfg.get("max_velocita_voce", 1.15)), float(cfg.get("coda", 0.5)))

    out_video = p.file(VIDEO_ADATTATO)
    if piano.video == 1.0:
        ff.esegui(["-i", video, "-an", "-c:v", "copy", out_video], verbose)
    else:
        ff.esegui(["-i", video, "-an", "-vf", f"setpts=PTS/{piano.video:.4f}",
                   "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                   out_video], verbose)
    out_voce = p.file(VOCE_ADATTATA)
    ff.esegui(["-i", voce, "-filter:a", f"atempo={piano.voce:.4f}",
               "-c:a", "libmp3lame", "-b:a", "192k", out_voce], verbose)

    print(f"✓ video ×{piano.video:.3f} → {out_video} ({ff.durata(out_video):.1f}s)")
    print(f"✓ voce  ×{piano.voce:.3f} → {out_voce} ({ff.durata(out_voce):.1f}s)")
    if piano.avviso:
        print(f"! {piano.avviso}")
    return piano
