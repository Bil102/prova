"""Step 5 — generazione voce italiana con ElevenLabs → voiceover_it.mp3

script_it.txt può contenere righe `[NomeSpeaker]` che aprono un blocco di battute; senza
intestazioni tutto il testo è dello speaker "narratore". Ogni speaker va mappato a una voce
in progetto.toml:

    [voce.speaker]
    narratore = "VOICE_ID"

Ogni blocco diventa voce/NN_speaker.mp3; poi vengono concatenati in voiceover_it.mp3.
I blocchi il cui testo e impostazioni non sono cambiati non vengono rigenerati (niente
crediti sprecati quando correggi una sola battuta).
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path

from . import ff
from .config import SCRIPT_IT, VOICEOVER, ErroreConfig, Progetto, richiedi_env

API = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
INTESTAZIONE = re.compile(r"^\[([^\]\d:][^\]]*)\]\s*$")


@dataclass
class Blocco:
    speaker: str
    testo: str


def dividi(script: str) -> list[Blocco]:
    blocchi: list[Blocco] = []
    speaker, righe = "narratore", []

    def chiudi():
        testo = re.sub(r"\n{3,}", "\n\n", "\n".join(righe)).strip()
        if testo:
            blocchi.append(Blocco(speaker, testo))

    for riga in script.splitlines():
        m = INTESTAZIONE.match(riga.strip())
        if m:
            chiudi()
            speaker, righe = m.group(1).strip(), []
        elif not riga.lstrip().startswith("#"):  # righe '#' = note, non lette
            righe.append(riga.rstrip())
    chiudi()
    return blocchi


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", s.lower()).strip("_") or "speaker"


def esegui(p: Progetto, solo: int | None = None, forza: bool = False, verbose: bool = False) -> None:
    import requests

    cfg = p.sezione("voce")
    voci: dict = cfg.get("speaker", {})
    blocchi = dividi(p.richiedi(SCRIPT_IT).read_text(encoding="utf-8"))
    if not blocchi:
        raise ErroreConfig(f"{SCRIPT_IT} è vuoto")
    mancanti = sorted({b.speaker for b in blocchi} - voci.keys())
    if mancanti:
        raise ErroreConfig("Voce ElevenLabs non assegnata per: " + ", ".join(mancanti)
                           + "\n  aggiungi in progetto.toml → [voce.speaker] nome = \"VOICE_ID\"")
    vuote = [k for k, v in voci.items() if not v or v == "VOICE_ID"]
    if vuote and any(b.speaker in vuote for b in blocchi):
        raise ErroreConfig(f"Imposta il voice_id reale in [voce.speaker] per: {', '.join(vuote)}")

    key = richiedi_env("ELEVENLABS_API_KEY")
    corpo_base = {
        "model_id": cfg.get("modello", "eleven_multilingual_v2"),
        "voice_settings": {
            "stability": cfg.get("stability", 0.5),
            "similarity_boost": cfg.get("similarity_boost", 0.75),
            "style": cfg.get("style", 0.0),
            "use_speaker_boost": cfg.get("speaker_boost", True),
            "speed": cfg.get("velocita", 1.0),
        },
    }
    if cfg.get("lingua"):
        corpo_base["language_code"] = cfg["lingua"]

    cartella = p.file("voce")
    cartella.mkdir(exist_ok=True)
    parti: list[Path] = []
    for i, b in enumerate(blocchi, 1):
        out = cartella / f"{i:02d}_{_slug(b.speaker)}.mp3"
        parti.append(out)
        corpo = {**corpo_base, "text": b.testo,
                 # contesto per intonazione continua tra blocchi adiacenti
                 "previous_text": blocchi[i - 2].testo[-300:] if i > 1 else None,
                 "next_text": blocchi[i].testo[:300] if i < len(blocchi) else None}
        corpo = {k: v for k, v in corpo.items() if v is not None}
        firma = hashlib.sha256(json.dumps([voci[b.speaker], corpo], sort_keys=True).encode()).hexdigest()
        meta = out.with_suffix(".json")
        if solo is not None and i != solo:
            if not out.exists():
                raise ErroreConfig(f"Blocco {i} mai generato: lancia prima senza --solo")
            continue
        if not forza and solo is None and out.exists() and meta.exists() \
                and json.loads(meta.read_text()).get("firma") == firma:
            print(f"  = blocco {i} ({b.speaker}) invariato")
            continue
        print(f"  → blocco {i} ({b.speaker}, {len(b.testo)} caratteri)")
        r = requests.post(
            API.format(voice_id=voci[b.speaker]),
            params={"output_format": cfg.get("formato", "mp3_44100_128")},
            headers={"xi-api-key": key, "Content-Type": "application/json", "Accept": "audio/mpeg"},
            json=corpo, timeout=300,
        )
        if r.status_code != 200:
            raise ErroreConfig(f"Errore ElevenLabs ({r.status_code}) sul blocco {i}: {r.text[:500]}")
        out.write_bytes(r.content)
        meta.write_text(json.dumps({"firma": firma, "speaker": b.speaker, "testo": b.testo},
                                   ensure_ascii=False, indent=2), encoding="utf-8")

    concatena(parti, p.file(VOICEOVER), float(cfg.get("pausa_blocchi", 0.3)), verbose)
    print(f"✓ {p.file(VOICEOVER)} ({ff.durata(p.file(VOICEOVER)):.1f}s, {len(parti)} blocchi)")


def concatena(parti: list[Path], out: Path, pausa: float, verbose: bool = False) -> None:
    """Concatena i blocchi inserendo `pausa` secondi di silenzio tra uno e l'altro."""
    if len(parti) == 1:
        ff.esegui(["-i", parti[0], "-c:a", "libmp3lame", "-b:a", "192k", out], verbose)
        return
    args, etichette = [], []
    for i, f in enumerate(parti):
        args += ["-i", f]
        lbl = f"a{i}"
        pad = f",apad=pad_dur={pausa}" if pausa > 0 and i < len(parti) - 1 else ""
        etichette.append((f"[{i}:a]aresample=44100,aformat=channel_layouts=mono{pad}[{lbl}]", lbl))
    filtro = ";".join(e for e, _ in etichette) + ";" + "".join(f"[{l}]" for _, l in etichette) \
        + f"concat=n={len(parti)}:v=0:a=1[out]"
    ff.esegui([*args, "-filter_complex", filtro, "-map", "[out]", "-c:a", "libmp3lame", "-b:a", "192k", out],
              verbose)
