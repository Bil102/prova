"""Titolo grafico dell'hook: rilevamento nel video originale e banner tradotto nello stesso stile.

  localizza.py titolo progetti/x                      rileva il titolo nell'originale
  localizza.py titolo progetti/x "FRASE" ["FRASE 2"]  crea banner_titolo.png (una frase per riga)

Rilevamento: Vmake toglie dal video sia i sottotitoli sia il titolo, quindi la differenza tra
originale.mp4 e video_clean.mp4 mostra dove c'era testo. Il titolo resta identico per alcuni
secondi, i sottotitoli cambiano di continuo: si tengono le righe dell'immagine in cui il testo
rimosso è fermo. Dal ritaglio si misurano banda (colore, posizione), righe di testo (altezza,
colore) e durata a schermo → titolo_stile.json + titolo_originale.png (da leggere e tradurre).
Il testo del titolo non viene letto in automatico (nessun OCR): lo legge e traduce Claude.
"""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from pathlib import Path

from . import ff
from .config import ORIGINALE, ROOT, VIDEO_CLEAN, ErroreConfig, Progetto

STILE = "titolo_stile.json"
RITAGLIO = "titolo_originale.png"
BANNER = "banner_titolo.png"
FONT = ROOT / "risorse" / "font" / "anton-latin-400-normal.woff"
SCALA_ANALISI = 240        # larghezza dei fotogrammi analizzati
PASSO = 0.5                # secondi tra un fotogramma e l'altro
DURATA_MAX = 15.0          # il titolo dell'hook sta nei primi secondi

# stile predefinito per i video senza titolo nell'originale (approvato: niente box,
# testo bianco con contorno nero, seconda riga gialla)
STILE_DEFAULT = {"banda": None, "contorno": [0, 0, 0], "righe": [
    {"colore": [255, 255, 255]}, {"colore": [250, 228, 0]}]}


def _fotogramma(video: Path, t: float, larghezza: int | None = SCALA_ANALISI):
    import numpy as np

    vf = f"scale={larghezza}:-2" if larghezza else "null"
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", vf, "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True)
    if r.returncode or not r.stdout:
        return None
    from io import BytesIO
    from PIL import Image
    return np.asarray(Image.open(BytesIO(r.stdout)).convert("RGB")).astype(int)


def rileva(p: Progetto) -> dict | None:
    """Cerca un titolo fermo nei primi secondi; salva stile e ritaglio. None se non c'è."""
    import numpy as np

    orig, clean = p.richiedi(ORIGINALE), p.richiedi(VIDEO_CLEAN)
    tempi = [i * PASSO for i in range(int(min(DURATA_MAX, ff.durata(orig)) / PASSO))]
    maschere, frames = [], []
    for t in tempi:
        o, c = _fotogramma(orig, t), _fotogramma(clean, t)
        if o is None or c is None or o.shape != c.shape:
            break
        maschere.append(np.abs(o - c).sum(axis=2) > 90)   # testo rimosso da Vmake
        frames.append(o)
    if len(frames) < 4:
        return None
    h, w = maschere[0].shape

    salto = int(2 / PASSO)  # il titolo resta identico per almeno 2 secondi, i sottotitoli no

    def righe_ferme(i: int, j: int) -> np.ndarray:
        """Righe con testo rimosso identico nei fotogrammi i e j."""
        m = maschere[i] & maschere[j]
        fermo = (np.abs(frames[i] - frames[j]).sum(axis=2) < 40) & m
        quanti = m.sum(axis=1)
        return (quanti > w * 0.04) & (fermo.sum(axis=1) > quanti * 0.97)

    if len(frames) <= salto + 1:
        return None
    base = righe_ferme(0, salto) & righe_ferme(1, salto + 1)
    blocchi, inizio = [], None
    for y, v in enumerate([*base, False]):
        if v and inizio is None:
            inizio = y
        elif not v and inizio is not None:
            blocchi.append((inizio, y))
            inizio = None
    blocchi = [b for b in blocchi if b[1] - b[0] >= h * 0.02]
    if not blocchi:
        return None
    y0, y1 = max(blocchi, key=lambda b: b[1] - b[0])
    # unisce blocchi vicini (due righe di testo separate da poco spazio)
    for a, b in sorted(blocchi):
        if a < y0 and y0 - b < h * 0.02:
            y0 = a
        if b > y1 and a - y1 < h * 0.02:
            y1 = b

    fine = tempi[0]
    for i in range(len(maschere)):
        if maschere[i][y0:y1].sum() < maschere[0][y0:y1].sum() * 0.5:
            break
        fine = tempi[i] + PASSO
    stile = _misura(orig, y0 / h, y1 / h)
    stile["fine"] = round(fine, 1)
    p.file(STILE).write_text(json.dumps(stile, indent=2), encoding="utf-8")
    return stile


def _misura(orig: Path, fy0: float, fy1: float) -> dict:
    """Misura banda e righe di testo sul fotogramma a piena risoluzione."""
    import numpy as np
    from PIL import Image

    full = _fotogramma(orig, 1.0, None)
    H, W, _ = full.shape
    y0, y1 = max(int(fy0 * H) - 2, 0), min(int(fy1 * H) + 2, H)
    zona = full[y0:y1]
    Image.fromarray(zona.astype("uint8")).save(Path(orig).parent / RITAGLIO)

    q = (zona // 24) * 24 + 12
    conta = Counter(map(tuple, q.reshape(-1, 3)))
    fondo, n = conta.most_common(1)[0]
    banda = n > zona.shape[0] * W * 0.4
    if banda:  # la banda può essere più alta/bassa del testo: si estende finché il colore è uguale
        vicino = lambda riga: (np.abs(riga - np.array(fondo)).sum(axis=1) < 60).mean() > 0.6
        while y0 > 0 and vicino(full[y0 - 1]):
            y0 -= 1
        while y1 < H and vicino(full[y1]):
            y1 += 1
        zona = full[y0:y1]
        colore_fondo = [int(x) for x in np.median(zona[np.abs(zona - np.array(fondo)).sum(axis=2) < 60], axis=0)]
    # pixel di testo: non scuri (no contorno) e lontani dal colore del fondo
    lum = zona.mean(axis=2)
    testo = (lum > 120) & (np.abs(zona - np.array(fondo)).sum(axis=2) > 200)
    profilo = testo.sum(axis=1) > 3
    righe, inizio = [], None
    for y, v in enumerate([*profilo, False]):
        if v and inizio is None:
            inizio = y
        elif not v and inizio is not None:
            if y - inizio >= 6:
                pix = zona[inizio:y][testo[inizio:y]]
                righe.append({"centro": round((y0 + (inizio + y) / 2) / H, 4),
                              "altezza": round((y - inizio) / H, 4),
                              # colore più frequente (la media si sporca con i bordi sfumati)
                              "colore": [int(x) for x in Counter(map(tuple, (pix // 8) * 8 + 4)).most_common(1)[0][0]]})
            inizio = None
    return {"larghezza_video": W, "altezza_video": H,
            "banda": {"y0": round(y0 / H, 4), "y1": round(y1 / H, 4), "colore": colore_fondo} if banda else None,
            "contorno": [60, 0, 0] if banda else [0, 0, 0], "righe": righe}


def banner(p: Progetto, frasi: list[str], scala: int = 2) -> Path:
    """Crea banner_titolo.png nello stile rilevato (o in quello predefinito)."""
    from PIL import Image, ImageDraw, ImageFont

    s = p.file(STILE)
    stile = json.loads(s.read_text()) if s.exists() else None
    W = (stile or {}).get("larghezza_video", 720) * scala
    H = (stile or {}).get("altezza_video", 1280) * scala
    righe_stile = (stile or STILE_DEFAULT)["righe"]
    if len(frasi) != len(righe_stile) and stile:
        print(f"! l'originale ha {len(righe_stile)} righe, ricevute {len(frasi)}: uso lo stile della prima per le extra")
    banda = (stile or {}).get("banda")
    contorno = tuple((stile or STILE_DEFAULT)["contorno"])

    def rendi(testo: str, colore, alt_maiusc: int):
        size = 10
        while True:
            f = ImageFont.truetype(str(FONT), size)
            b = f.getbbox("H")
            if b[3] - b[1] >= alt_maiusc:
                break
            size += 1
        sp, bo = 1, 2 if banda else max(3, alt_maiusc // 10)
        l, t, r, btm = f.getbbox(testo, stroke_width=sp + bo)
        im = Image.new("RGBA", (r - l + 4, btm - t + 4), (0, 0, 0, 0))
        d = ImageDraw.Draw(im)
        d.text((2 - l, 2 - t), testo, font=f, fill=contorno, stroke_width=sp + bo,
               stroke_fill=contorno + ((110,) if banda else (255,)))
        d.text((2 - l, 2 - t), testo, font=f, fill=tuple(colore), stroke_width=sp, stroke_fill=tuple(colore))
        return im.resize((int(im.width * 1.12), im.height), Image.LANCZOS)

    if banda:
        top, bot = int(banda["y0"] * H), int(banda["y1"] * H)
    else:
        top, bot = 0, int(H * 0.2)
    out = Image.new("RGBA", (W, bot - top), tuple(banda["colore"]) + (255,) if banda else (0, 0, 0, 0))
    immagini, centri = [], []
    for i, frase in enumerate(frasi):
        rs = righe_stile[min(i, len(righe_stile) - 1)]
        alt = rs.get("altezza", 0.032) * H * 0.97  # altezza riga misurata ≈ maiuscole + bordo
        immagini.append(rendi(frase, rs["colore"], int(alt)))
        if "centro" in rs and i < len(righe_stile):
            centri.append(rs["centro"] * H - top)
        else:  # stile predefinito: righe una sotto l'altra, interlinea stretta
            centri.append(immagini[0].height * (0.6 + 1.05 * i))
    k = min(1.0, *((W * 0.94) / im.width for im in immagini))
    for im, cy in zip(immagini, centri):
        im = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
        out.alpha_composite(im, ((W - im.width) // 2, int(cy - im.height / 2)))
    if not banda:
        out = out.crop(out.getbbox() or (0, 0, W, bot - top))
    dest = p.file(BANNER)
    out.save(dest)
    return dest
