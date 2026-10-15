"""Step 4 — traduzione/adattamento con Claude → script_it.txt + note_adattamento.md

Le regole stanno in regole_adattamento.md (system prompt). I dati specifici del video
(genere del narratore, nomi già scelti, istruzioni extra) vengono da progetto.toml.

Se Claude introduce un nome italiano non ancora deciso, o ha dubbi, il testo NON diventa
script_it.txt: viene salvato come script_it.bozza.txt e lo step si ferma per conferma
(regola "segnalare sempre la sostituzione prima di procedere").
"""

from __future__ import annotations

import json

from .config import NOTE, REGOLE, SCRIPT_IT, TRASCRIZIONE, ErroreConfig, Progetto
from . import verifica

BOZZA = "script_it.bozza.txt"
GENERI = ("uomo", "donna")

SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["script_it", "sostituzioni", "domande"],
    "properties": {
        "script_it": {
            "type": "string",
            "description": "Testo italiano finale per la voce: paragrafi brevi separati da una riga vuota, "
                           "nessun timestamp. Con più speaker, ogni blocco inizia con una riga [NomeSpeaker].",
        },
        "sostituzioni": {
            "type": "array",
            "description": "Ogni adattamento non letterale applicato per le regole (nomi, brand, prezzi, luoghi...).",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["tipo", "originale", "sostituto"],
                "properties": {
                    "tipo": {"type": "string", "enum": [
                        "nome_persona", "brand_concorrente", "prezzo_rimosso", "luogo", "negozio",
                        "certificazione", "prodotto", "offerta", "altro"]},
                    "originale": {"type": "string"},
                    "sostituto": {"type": "string"},
                },
            },
        },
        "domande": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Dubbi che richiedono una decisione umana prima di usare il testo (vuoto se nessuno).",
        },
    },
}

ISTRUZIONI_OUTPUT = """
Sei l'adattatore italiano di video pubblicitari americani. Applica SEMPRE tutte le regole
qui sopra. Ricevi la trascrizione inglese (con timestamp, solo come riferimento) e i dati
del progetto. Rispondi con il JSON richiesto:
- script_it: il testo italiano pronto per ElevenLabs.
- sostituzioni: elenca ogni nome di persona sostituito (tipo nome_persona), ogni brand,
  prezzo, luogo, negozio o certificazione adattati.
- domande: solo dubbi reali che impediscono di usare il testo così com'è.
""".strip()


def esegui(p: Progetto, accetta: bool = False, verbose: bool = False) -> int:
    import anthropic

    cfg = p.sezione("traduzione")
    narr = p.sezione("narratore")
    genere = str(narr.get("genere", "")).strip().lower()
    if genere not in GENERI:
        raise ErroreConfig(
            "Genere del narratore non impostato: in progetto.toml metti [narratore] genere = \"uomo\" o "
            "\"donna\" (serve per accordare verbi e participi)."
        )
    nomi: dict = p.sezione("nomi")
    trascrizione = p.richiedi(TRASCRIZIONE).read_text(encoding="utf-8")

    dati = [f"Genere del narratore: {genere}"]
    if narr.get("nome"):
        dati.append(f"Nome italiano del narratore: {narr['nome']}")
    if nomi:
        dati.append("Sostituzioni di nomi già decise (usale sempre, non cambiarle):\n"
                    + "\n".join(f"- {k} → {v}" for k, v in nomi.items()))
    if cfg.get("istruzioni_extra"):
        dati.append(f"Istruzioni specifiche per questo video: {cfg['istruzioni_extra']}")
    utente = "## Dati del progetto\n" + "\n".join(dati) + "\n\n## Trascrizione inglese\n" + trascrizione

    client = anthropic.Anthropic()
    try:
        r = client.beta.messages.create(
            model=cfg.get("modello", "claude-opus-5-5"),
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            thinking={"type": "adaptive"},
            output_config={"effort": cfg.get("effort", "high"),
                           "format": {"type": "json_schema", "schema": SCHEMA}},
            system=REGOLE.read_text(encoding="utf-8") + "\n\n" + ISTRUZIONI_OUTPUT,
            messages=[{"role": "user", "content": utente}],
        )
    except anthropic.AuthenticationError:
        raise ErroreConfig("Chiave Anthropic non valida o mancante: imposta ANTHROPIC_API_KEY nel .env")
    except anthropic.RateLimitError:
        raise ErroreConfig("Limite di richieste Anthropic raggiunto: riprova tra poco")
    except anthropic.APIStatusError as e:
        raise ErroreConfig(f"Errore API Anthropic ({e.status_code}): {e.message}")
    except anthropic.APIConnectionError:
        raise ErroreConfig("Impossibile contattare l'API Anthropic: controlla la connessione")

    if r.stop_reason == "refusal":
        raise ErroreConfig("Claude ha rifiutato la richiesta; riprova o traduci in sessione con Claude Code")
    if r.stop_reason == "max_tokens":
        raise ErroreConfig("Risposta troncata (max_tokens): il video è insolitamente lungo, dividi la trascrizione")
    testo = next(b.text for b in r.content if b.type == "text")
    res = json.loads(testo)

    nuovi_nomi = [s for s in res["sostituzioni"]
                  if s["tipo"] == "nome_persona" and nomi.get(s["originale"]) != s["sostituto"]]
    _scrivi_note(p, res, nuovi_nomi)

    script = res["script_it"].strip() + "\n"
    if (nuovi_nomi or res["domande"]) and not accetta:
        p.file(BOZZA).write_text(script, encoding="utf-8")
        print(f"! Serve una conferma prima di procedere (dettagli in {NOTE}):")
        for s in nuovi_nomi:
            print(f"  - nome nuovo: {s['originale']} → {s['sostituto']}")
        for d in res["domande"]:
            print(f"  - domanda: {d}")
        print(f"  Bozza salvata in {BOZZA}. Per confermare: aggiungi i nomi in [nomi] di progetto.toml\n"
              f"  e rilancia, oppure rilancia con --accetta per usare la bozza così com'è.")
        return 2

    p.file(SCRIPT_IT).write_text(script, encoding="utf-8")
    p.file(BOZZA).unlink(missing_ok=True)
    print(f"✓ {p.file(SCRIPT_IT)}")
    return 0 if verifica.esegui(p) else 1


def accetta_bozza(p: Progetto) -> bool:
    """`traduci --accetta` con una bozza già presente: la promuove senza richiamare l'API."""
    bozza = p.file(BOZZA)
    if not bozza.exists():
        return False
    bozza.replace(p.file(SCRIPT_IT))
    print(f"✓ bozza confermata → {p.file(SCRIPT_IT)}")
    verifica.esegui(p)
    return True


def _scrivi_note(p: Progetto, res: dict, nuovi_nomi: list[dict]) -> None:
    righe = ["# Note di adattamento", ""]
    if nuovi_nomi:
        righe += ["## ⚠ Nomi nuovi da confermare", *[f"- {s['originale']} → **{s['sostituto']}**" for s in nuovi_nomi], ""]
    if res["domande"]:
        righe += ["## ⚠ Domande", *[f"- {d}" for d in res["domande"]], ""]
    righe += ["## Sostituzioni applicate"]
    righe += [f"- [{s['tipo']}] {s['originale']} → {s['sostituto']}" for s in res["sostituzioni"]] or ["- nessuna"]
    p.file(NOTE).write_text("\n".join(righe) + "\n", encoding="utf-8")
