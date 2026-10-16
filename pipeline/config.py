"""Caricamento configurazione: chiavi API (.env) e progetto.toml di ogni video."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REGOLE = ROOT / "regole_adattamento.md"

# Nomi file standard di un progetto (uno per video)
ORIGINALE = "originale.mp4"
VIDEO_CLEAN = "video_clean.mp4"
TRASCRIZIONE = "transcript_en.txt"
TRASCRIZIONE_JSON = "transcript_en.json"
SCRIPT_IT = "script_it.txt"
NOTE = "note_adattamento.md"
VOICEOVER = "voiceover_it.mp3"
VIDEO_ADATTATO = "video_adattato.mp4"
VOCE_ADATTATA = "voiceover_adattato.mp3"
MONTAGGIO = "montaggio.mp4"
CON_MUSICA = "con_musica.mp4"
FINALE = "video_finale_it.mp4"


class ErroreConfig(Exception):
    pass


def carica_env(path: Path | None = None) -> None:
    """Legge un file .env minimale (CHIAVE=valore) senza sovrascrivere l'ambiente."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for riga in path.read_text(encoding="utf-8").splitlines():
        riga = riga.strip()
        if not riga or riga.startswith("#") or "=" not in riga:
            continue
        k, v = riga.split("=", 1)
        v = v.split(" #", 1)[0].strip().strip('"').strip("'")
        if v:
            os.environ.setdefault(k.strip(), v)


def richiedi_env(nome: str) -> str:
    val = os.environ.get(nome, "").strip()
    if not val:
        raise ErroreConfig(f"Variabile {nome} mancante: aggiungila al file .env (vedi .env.example)")
    return val


@dataclass
class Progetto:
    dir: Path
    cfg: dict

    @classmethod
    def apri(cls, dir: str | Path) -> "Progetto":
        d = Path(dir).resolve()
        f = d / "progetto.toml"
        if not f.exists():
            raise ErroreConfig(f"{f} non trovato: crea il progetto con `localizza.py init`")
        with f.open("rb") as fh:
            return cls(d, tomllib.load(fh))

    def file(self, nome: str) -> Path:
        return self.dir / nome

    def sezione(self, nome: str) -> dict:
        return self.cfg.get(nome, {}) or {}

    def percorso(self, rel: str) -> Path:
        """Percorso relativo alla cartella progetto (o assoluto)."""
        p = Path(rel)
        return p if p.is_absolute() else self.dir / p

    def richiedi(self, nome: str) -> Path:
        p = self.file(nome)
        if not p.exists():
            raise ErroreConfig(f"{p.name} mancante in {self.dir}: esegui prima lo step precedente")
        return p

    def sorgente_video(self) -> Path:
        """Video pulito se esiste, altrimenti errore esplicito (non si monta sull'originale per sbaglio)."""
        clean = self.file(VIDEO_CLEAN)
        if clean.exists():
            return clean
        raise ErroreConfig(
            f"{VIDEO_CLEAN} mancante: esegui `localizza.py pulisci` "
            f"(o copia lì il video senza sottotitoli scaricato da Vmake)"
        )
