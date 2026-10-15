"""Step 3 — trascrizione audio inglese con Whisper → transcript_en.txt (+ .json con i segmenti)

Backend ([trascrizione] backend):
  openai  API OpenAI (whisper-1): veloce, zero setup, a pagamento. Serve OPENAI_API_KEY.
  locale  faster-whisper (consigliato) o openai-whisper installati in locale. Gratis, lento su CPU.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

from . import ff
from .config import ORIGINALE, TRASCRIZIONE, TRASCRIZIONE_JSON, ErroreConfig, Progetto, richiedi_env

OPENAI_URL = "https://api.openai.com/v1/audio/transcriptions"


def esegui(p: Progetto, verbose: bool = False) -> None:
    cfg = p.sezione("trascrizione")
    backend = cfg.get("backend", "openai")
    lingua = cfg.get("lingua", "en")
    src = p.richiedi(ORIGINALE)  # l'audio dell'originale è identico a quello del video pulito

    with tempfile.TemporaryDirectory() as tmp:
        audio = Path(tmp) / "audio.mp3"
        # mono 16 kHz: è ciò che Whisper usa internamente, e resta sotto i 25 MB dell'API
        ff.esegui(["-i", src, "-vn", "-ac", "1", "-ar", "16000", "-b:a", "64k", audio], verbose)
        if backend == "openai":
            segmenti = _openai(audio, lingua)
        elif backend == "locale":
            segmenti = _locale(audio, lingua, cfg.get("modello_locale", "large-v3"))
        else:
            raise ErroreConfig(f"[trascrizione] backend sconosciuto: {backend!r}")

    p.file(TRASCRIZIONE_JSON).write_text(json.dumps(segmenti, ensure_ascii=False, indent=2), encoding="utf-8")
    p.file(TRASCRIZIONE).write_text(formatta(segmenti), encoding="utf-8")
    print(f"✓ {p.file(TRASCRIZIONE)} ({len(segmenti)} segmenti)")


def formatta(segmenti: list[dict]) -> str:
    return "".join(f"[{_ts(s['start'])} → {_ts(s['end'])}] {s['text'].strip()}\n" for s in segmenti)


def _ts(sec: float) -> str:
    m, s = divmod(sec, 60)
    return f"{int(m):02d}:{s:04.1f}"


def _openai(audio: Path, lingua: str) -> list[dict]:
    import requests

    key = richiedi_env("OPENAI_API_KEY")
    with audio.open("rb") as fh:
        r = requests.post(
            OPENAI_URL,
            headers={"Authorization": f"Bearer {key}"},
            files={"file": (audio.name, fh, "audio/mpeg")},
            data={"model": os.environ.get("OPENAI_WHISPER_MODEL", "whisper-1"), "language": lingua,
                  "response_format": "verbose_json", "timestamp_granularities[]": "segment"},
            timeout=600,
        )
    if r.status_code != 200:
        raise ErroreConfig(f"Errore API OpenAI ({r.status_code}): {r.text[:500]}")
    return [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in r.json().get("segments", [])]


def _locale(audio: Path, lingua: str, modello: str) -> list[dict]:
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        WhisperModel = None
    if WhisperModel:
        model = WhisperModel(modello, device="auto", compute_type="auto")
        segs, _ = model.transcribe(str(audio), language=lingua, vad_filter=True)
        return [{"start": s.start, "end": s.end, "text": s.text} for s in segs]
    try:
        import whisper
    except ImportError:
        raise ErroreConfig("Backend 'locale': installa `pip install faster-whisper` (o openai-whisper)")
    res = whisper.load_model(modello).transcribe(str(audio), language=lingua)
    return [{"start": s["start"], "end": s["end"], "text": s["text"]} for s in res["segments"]]
