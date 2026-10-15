"""Helper minimi attorno a ffmpeg/ffprobe."""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


class ErroreFFmpeg(Exception):
    pass


def verifica_installato() -> None:
    for exe in ("ffmpeg", "ffprobe"):
        if not shutil.which(exe):
            raise ErroreFFmpeg(f"{exe} non trovato nel PATH: installalo (es. `brew install ffmpeg`)")


def esegui(args: list[str], verbose: bool = False) -> None:
    cmd = ["ffmpeg", "-hide_banner", "-y", "-loglevel", "info" if verbose else "error", *map(str, args)]
    if verbose:
        print("$", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=not verbose, text=True)
    if r.returncode != 0:
        raise ErroreFFmpeg(f"ffmpeg ha fallito:\n{(r.stderr or '').strip()}")


def probe(path: Path) -> dict:
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise ErroreFFmpeg(f"ffprobe non riesce a leggere {path}: {r.stderr.strip()}")
    return json.loads(r.stdout)


def durata(path: Path) -> float:
    return float(probe(path)["format"]["duration"])


def dimensioni(path: Path) -> tuple[int, int]:
    for s in probe(path)["streams"]:
        if s.get("codec_type") == "video":
            return int(s["width"]), int(s["height"])
    raise ErroreFFmpeg(f"{path} non contiene una traccia video")


def ha_audio(path: Path) -> bool:
    return any(s.get("codec_type") == "audio" for s in probe(path)["streams"])


# Codifica per i file intermedi: alta qualità, veloce. L'export finale usa i suoi parametri.
ENC_INTERMEDIO = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "16", "-pix_fmt", "yuv420p",
                  "-c:a", "aac", "-b:a", "192k"]
