"""Controllo automatico di script_it.txt contro le regole di adattamento.

Non sostituisce la rilettura umana: intercetta gli errori meccanici (nome prodotto scritto
male, prezzi rimasti, brand concorrenti, timestamp, nomi americani non sostituiti).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .config import SCRIPT_IT, Progetto

BRAND_CONCORRENTI = ["Calgon", "Beckman", "Beckmann", "Afresh", "OxiClean", "Tide"]
# nomi del prodotto negli spot originali: nel testo italiano diventano sempre "Rivàiv Dram"
BRAND_ORIGINALI = ["Uproot", "PrimeDrum", "Prime Drum"]
RIFERIMENTI_USA = ["Walmart", "Target", "Costco", "Home Depot", "Lowe's", "Walgreens", "CVS", "Kroger",
                   "Florida", "Texas", "California", "London", "Londra", "EWG"]


@dataclass
class Problema:
    livello: str  # "ERRORE" | "AVVISO"
    riga: int
    messaggio: str

    def __str__(self) -> str:
        return f"{self.livello:6} riga {self.riga:>3}: {self.messaggio}"


def controlla(testo: str, nomi_originali: list[str] = (), brand_extra: list[str] = ()) -> list[Problema]:
    out: list[Problema] = []

    def cerca(pattern: str, livello: str, msg: str, flags=re.IGNORECASE):
        for n, riga in enumerate(testo.splitlines(), 1):
            for m in re.finditer(pattern, riga, flags):
                out.append(Problema(livello, n, msg.format(m.group(0))))

    cerca(r"revive\s*drum", "ERRORE", "'{}' → nel testo per la voce va scritto 'Rivàiv Dram'")
    cerca(r"Riv[aà]iv\s+Dram\s+(Pro|Ultra|Max|Plus)\b", "AVVISO", "variante prodotto '{}': rimuoverla salvo richiesta")
    cerca(r"\(?\b\d{1,2}:\d{2}(\.\d+)?\)?", "ERRORE", "timestamp '{}' da rimuovere")
    cerca(r"[$£]\s?\d[\d.,]*|\d[\d.,]*\s?(\$|£|dollari|sterline|USD|GBP)", "ERRORE", "prezzo '{}' da rimuovere")
    cerca(r"\d[\d.,]*\s?(€|euro\b)|€\s?\d[\d.,]*", "AVVISO", "cifra '{}': ok solo dentro una testimonianza personale")
    cerca(r"\d+\s?%", "AVVISO", "percentuale '{}': rimuovere se è uno sconto specifico")
    cerca(r"dermatologicamente\s+testat\w", "AVVISO", "'{}': evitare se il prodotto non è cosmetico")
    for b in BRAND_ORIGINALI:
        cerca(rf"\b{re.escape(b)}\b", "ERRORE", "nome prodotto originale '{}' → 'Rivàiv Dram'")
    for b in [*BRAND_CONCORRENTI, *brand_extra]:
        cerca(rf"\b{re.escape(b)}\b", "ERRORE", "brand concorrente '{}' → 'pastiglie del supermercato'")
    for luogo in RIFERIMENTI_USA:
        cerca(rf"\b{re.escape(luogo)}\b", "AVVISO", "riferimento USA/estero '{}': localizzare", flags=0)
    for nome in nomi_originali:
        cerca(rf"\b{re.escape(nome)}\b", "ERRORE", "nome originale '{}' non sostituito", flags=0)

    for n, riga in enumerate(testo.splitlines(), 1):
        r = riga.strip()
        if len(r) > 220 and not r.startswith("["):
            out.append(Problema("AVVISO", n, f"paragrafo lungo ({len(r)} caratteri): spezzarlo per la voce"))
    return sorted(out, key=lambda p: (p.riga, p.livello))


def esegui(p: Progetto, verbose: bool = False) -> bool:
    testo = p.richiedi(SCRIPT_IT).read_text(encoding="utf-8")
    problemi = controlla(
        testo,
        nomi_originali=list(p.sezione("nomi").keys()),
        brand_extra=p.sezione("verifica").get("brand_vietati", []),
    )
    for pr in problemi:
        print(pr)
    errori = sum(pr.livello == "ERRORE" for pr in problemi)
    avvisi = len(problemi) - errori
    print(("✗" if errori else "✓") + f" verifica {SCRIPT_IT}: {errori} errori, {avvisi} avvisi")
    return errori == 0
