"""Generazione overlay testuali → overlay_<nome>.png (fondo trasparente, box arrotondato opzionale).

Esempio:
  localizza.py grafica progetti/video1 offerta "COMPRA 2, PRENDINE 2 GRATIS" --sfondo "#E63946"
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from .config import ErroreConfig, Progetto

FONT_CANDIDATI = [
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _font(percorso: str | None, dim: int):
    from PIL import ImageFont

    for f in [percorso] if percorso else FONT_CANDIDATI:
        if f and Path(f).exists():
            return ImageFont.truetype(f, dim)
    if percorso:
        raise ErroreConfig(f"Font non trovato: {percorso}")
    return ImageFont.load_default(dim)


def crea(p: Progetto, nome: str, testo: str, larghezza: int = 900, dim_font: int = 72,
         colore: str = "#FFFFFF", sfondo: str | None = "#000000B3", font: str | None = None,
         margine: int = 36) -> Path:
    from PIL import Image, ImageDraw

    f = _font(font, dim_font)
    # a capo automatico in base alla larghezza utile
    car_medio = max(1, f.getlength("abcdefghijklmnopqrstuvwxyz") / 26)
    righe = []
    for par in testo.split("\\n"):
        righe += textwrap.wrap(par, max(4, int((larghezza - 2 * margine) / car_medio))) or [""]
    asc, disc = f.getmetrics()
    alt_riga = int((asc + disc) * 1.15)
    h = alt_riga * len(righe) + 2 * margine

    img = Image.new("RGBA", (larghezza, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if sfondo:
        d.rounded_rectangle([0, 0, larghezza - 1, h - 1], radius=min(40, h // 4), fill=sfondo)
    for i, r in enumerate(righe):
        w = f.getlength(r)
        d.text(((larghezza - w) / 2, margine + i * alt_riga), r, font=f, fill=colore)

    out = p.file(f"overlay_{nome}.png")
    img.save(out)
    print(f"✓ {out} ({larghezza}x{h})")
    return out
