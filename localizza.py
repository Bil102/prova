#!/usr/bin/env python3
"""Pipeline di localizzazione video EN → IT, eseguibile step by step.

  localizza.py init video.mp4 --nome spot01      crea progetti/spot01/
  localizza.py stato progetti/spot01             cosa è fatto e cosa manca
  localizza.py pulisci    progetti/spot01        2. rimozione sottotitoli → video_clean.mp4
  localizza.py trascrivi  progetti/spot01        3. Whisper → transcript_en.txt
  localizza.py traduci    progetti/spot01        4. Claude → script_it.txt
  localizza.py verifica   progetti/spot01           controllo regole su script_it.txt
  localizza.py voce       progetti/spot01        5. ElevenLabs → voiceover_it.mp3
  localizza.py grafica    progetti/spot01 NOME "TESTO"   overlay_NOME.png
  localizza.py monta      progetti/spot01        6-7. → montaggio.mp4
  localizza.py musica     progetti/spot01        8. → con_musica.mp4
  localizza.py esporta    progetti/spot01        9. → video_finale_it.mp4
  localizza.py tutto      progetti/spot01        esegue in sequenza, si ferma al primo intoppo
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

from pipeline import config as C
from pipeline import esporta, ff, grafica, monta, musica, pulisci, traduci, trascrivi, verifica, voce
from pipeline.config import ErroreConfig, Progetto

STEP = ["pulisci", "trascrivi", "traduci", "voce", "monta", "musica", "esporta"]
OUTPUT = [
    ("originale", C.ORIGINALE), ("pulisci", C.VIDEO_CLEAN), ("trascrivi", C.TRASCRIZIONE),
    ("traduci", C.SCRIPT_IT), ("voce", C.VOICEOVER), ("monta", C.MONTAGGIO),
    ("musica", C.CON_MUSICA), ("esporta", C.FINALE),
]


def cmd_init(a) -> int:
    src = Path(a.video)
    if not src.exists():
        raise ErroreConfig(f"Video non trovato: {src}")
    nome = a.nome or re.sub(r"[^\w-]+", "_", src.stem)
    d = Path(a.cartella) / nome
    if (d / "progetto.toml").exists():
        raise ErroreConfig(f"Il progetto {d} esiste già")
    d.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src, d / C.ORIGINALE)
    shutil.copyfile(Path(__file__).parent / "pipeline" / "modello_progetto.toml", d / "progetto.toml")
    print(f"✓ creato {d}\n  → apri {d / 'progetto.toml'} e imposta almeno [narratore] genere e [voce.speaker]")
    return 0


def cmd_stato(p: Progetto) -> int:
    for step, f in OUTPUT:
        path = p.file(f)
        print(f"  {'✓' if path.exists() else '·'} {step:10} {f}")
    if p.file(traduci.BOZZA).exists():
        print(f"  ! bozza in attesa di conferma: {traduci.BOZZA} (vedi {C.NOTE})")
    for png in sorted(p.dir.glob("overlay_*.png")):
        print(f"  ✓ overlay    {png.name}")
    return 0


def esegui_step(nome: str, p: Progetto, a) -> int:
    v = a.verbose
    if nome == "pulisci":
        pulisci.esegui(p, v)
    elif nome == "trascrivi":
        trascrivi.esegui(p, v)
    elif nome == "traduci":
        if getattr(a, "accetta", False) and traduci.accetta_bozza(p):
            return 0
        return traduci.esegui(p, accetta=getattr(a, "accetta", False), verbose=v)
    elif nome == "verifica":
        return 0 if verifica.esegui(p, v) else 1
    elif nome == "voce":
        voce.esegui(p, solo=getattr(a, "solo", None), forza=getattr(a, "forza", False), verbose=v)
    elif nome == "monta":
        monta.esegui(p, v)
    elif nome == "musica":
        musica.esegui(p, v)
    elif nome == "esporta":
        esporta.esegui(p, v)
    return 0


def cmd_tutto(p: Progetto, a) -> int:
    i0 = STEP.index(a.da) if a.da else 0
    i1 = STEP.index(a.a) + 1 if a.a else len(STEP)
    for nome in STEP[i0:i1]:
        if nome == "musica" and not p.sezione("musica").get("file"):
            print("· musica: nessun file configurato, step saltato")
            continue
        print(f"── {nome}")
        rc = esegui_step(nome, p, a)
        if rc != 0:
            print(f"Pipeline fermata a '{nome}'. Correggi e riprendi con: tutto {p.dir} --da {nome}")
            return rc
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-v", "--verbose", action="store_true", help="mostra i comandi ffmpeg")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("init", help="crea un progetto da un video originale")
    s.add_argument("video")
    s.add_argument("--nome")
    s.add_argument("--cartella", default="progetti")

    for nome in ["stato", "verifica", *STEP]:
        s = sub.add_parser(nome)
        s.add_argument("progetto")
        if nome == "traduci":
            s.add_argument("--accetta", action="store_true",
                           help="conferma la bozza (nomi nuovi/domande) senza richiamare l'API")
        if nome == "voce":
            s.add_argument("--solo", type=int, help="rigenera solo il blocco N")
            s.add_argument("--forza", action="store_true", help="rigenera tutti i blocchi")

    s = sub.add_parser("tutto", help="esegue gli step in sequenza")
    s.add_argument("progetto")
    s.add_argument("--da", choices=STEP)
    s.add_argument("--a", choices=STEP)

    s = sub.add_parser("grafica", help="crea overlay_NOME.png da un testo (\\n per andare a capo)")
    s.add_argument("progetto")
    s.add_argument("nome")
    s.add_argument("testo")
    s.add_argument("--larghezza", type=int, default=900)
    s.add_argument("--dim-font", type=int, default=72)
    s.add_argument("--colore", default="#FFFFFF")
    s.add_argument("--sfondo", default="#000000B3", help="colore box (RRGGBBAA) o 'nessuno'")
    s.add_argument("--font", help="percorso di un file .ttf")

    a = ap.parse_args(argv)
    C.carica_env()
    try:
        if a.cmd == "init":
            return cmd_init(a)
        p = Progetto.apri(a.progetto)
        if a.cmd == "stato":
            return cmd_stato(p)
        if a.cmd == "grafica":
            grafica.crea(p, a.nome, a.testo, a.larghezza, a.dim_font, a.colore,
                         None if a.sfondo == "nessuno" else a.sfondo, a.font)
            return 0
        ff.verifica_installato()
        if a.cmd == "tutto":
            return cmd_tutto(p, a)
        return esegui_step(a.cmd, p, a)
    except (ErroreConfig, ff.ErroreFFmpeg) as e:
        print(f"✗ {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
