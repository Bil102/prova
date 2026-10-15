"""Step 2 — rimozione sottotitoli originali → video_clean.mp4

Metodi (progetto.toml, [pulizia] metodo):
  manuale  carichi tu il video su Vmake e salvi il risultato come video_clean.mp4 (default)
  vmake    via API Vmake — vedi _vmake(): da completare quando hai la documentazione API
  sfoca    sfocatura di una fascia fissa (area = [x, y, w, h] in pixel)
  delogo   interpolazione ffmpeg della fascia (spesso più pulita della sfocatura su sfondi semplici)
  ritaglia taglia via la fascia in basso (area = [0, y, w, h]: tiene solo la parte sopra y)
  nessuno  il video originale non ha sottotitoli: viene solo copiato
"""

from __future__ import annotations

import shutil

from . import ff
from .config import ORIGINALE, VIDEO_CLEAN, ErroreConfig, Progetto


def esegui(p: Progetto, verbose: bool = False) -> None:
    cfg = p.sezione("pulizia")
    metodo = cfg.get("metodo", "manuale")
    src = p.richiedi(ORIGINALE)
    out = p.file(VIDEO_CLEAN)

    if metodo == "manuale":
        if out.exists():
            print(f"✓ {VIDEO_CLEAN} presente (caricato manualmente)")
            return
        raise ErroreConfig(
            f"Metodo 'manuale': carica {src} su Vmake, scarica il risultato e salvalo come\n  {out}\n"
            f"poi passa allo step successivo. (Oppure imposta [pulizia] metodo = 'sfoca'/'delogo'.)"
        )
    if metodo == "nessuno":
        shutil.copyfile(src, out)
    elif metodo == "vmake":
        _vmake(src, out)
    elif metodo in ("sfoca", "delogo", "ritaglia"):
        x, y, w, h = _area(p, cfg)
        if metodo == "sfoca":
            forza = int(cfg.get("forza_sfocatura", 20))
            filtro = (f"[0:v]split[a][b];[b]crop={w}:{h}:{x}:{y},boxblur={forza}:2[s];"
                      f"[a][s]overlay={x}:{y}[v]")
        elif metodo == "delogo":
            filtro = f"[0:v]delogo=x={x}:y={y}:w={w}:h={h}[v]"
        else:
            filtro = f"[0:v]crop=iw:{y}:0:0[v]"
        ff.esegui(["-i", src, "-filter_complex", filtro, "-map", "[v]", "-map", "0:a?",
                   *ff.ENC_INTERMEDIO, out], verbose)
    else:
        raise ErroreConfig(f"[pulizia] metodo sconosciuto: {metodo!r}")
    print(f"✓ {out}")


def _area(p: Progetto, cfg: dict) -> tuple[int, int, int, int]:
    area = cfg.get("area")
    if not area or len(area) != 4:
        raise ErroreConfig("[pulizia] area = [x, y, larghezza, altezza] obbligatoria per sfoca/delogo/ritaglia")
    x, y, w, h = map(int, area)
    vw, vh = ff.dimensioni(p.file(ORIGINALE))
    # delogo vuole l'area strettamente dentro il fotogramma
    x, y = max(1, x), max(1, y)
    w, h = min(w, vw - x - 1), min(h, vh - y - 1)
    if w <= 0 or h <= 0:
        raise ErroreConfig(f"[pulizia] area {area} fuori dal fotogramma {vw}x{vh}")
    return x, y, w, h


def _vmake(src, out) -> None:
    # Vmake non pubblica una documentazione API aperta: le pagine prodotto citano un'integrazione
    # API, ma endpoint, autenticazione e formato dei job vanno presi dal pannello sviluppatore
    # del tuo account. Quando li hai, implementa qui il flusso:
    #   1. upload di `src` (POST, header con VMAKE_API_KEY da .env)  → job_id
    #   2. polling dello stato del job ogni ~5 s finché non è completato o in errore
    #   3. download del video risultante in `out`
    # Fino ad allora usa metodo = "manuale" oppure "sfoca"/"delogo".
    raise ErroreConfig(
        "Integrazione API Vmake non ancora configurata (servono endpoint e chiave dal tuo account Vmake). "
        "Vedi pipeline/pulisci.py::_vmake. Nel frattempo usa [pulizia] metodo = 'manuale'."
    )
