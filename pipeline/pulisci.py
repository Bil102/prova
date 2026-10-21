"""Step 2 — rimozione sottotitoli originali → video_clean.mp4

Metodi (progetto.toml, [pulizia] metodo):
  manuale  carichi tu il video su Vmake e salvi il risultato come video_clean.mp4 (default)
  vmake    via API Vmake (SDK ufficiale in vendor/, chiavi MT_AK/MT_SK). Task: [pulizia] vmake_task
           (default "SKM0005" = AI Remover Pro; elenco completo: `action-api-sdk catalog --media-type video`)
  sfoca    sfocatura di una fascia fissa (area = [x, y, w, h] in pixel)
  delogo   interpolazione ffmpeg della fascia (spesso più pulita della sfocatura su sfondi semplici)
  ritaglia taglia via la fascia in basso (area = [0, y, w, h]: tiene solo la parte sopra y)
  nessuno  il video originale non ha sottotitoli: viene solo copiato
"""

from __future__ import annotations

import json
import os
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
        _vmake(p, src, out, cfg.get("vmake_task", "SKM0005"))
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


def _vmake(p: Progetto, src, out, task: str) -> None:
    """Upload → elaborazione → download con l'SDK Vmake (action_api_sdk).

    Il task_id viene salvato in .vmake_task.json appena il lavoro è inviato: se il polling si
    interrompe, rilanciando `pulisci` si riprende quel lavoro senza ricaricare né consumare quota.
    """
    import requests

    try:
        from action_api_sdk import SkillClient
    except ImportError:
        raise ErroreConfig("SDK Vmake non installato: pip install vendor/action_api_sdk-2.0.1-py3-none-any.whl")
    if not (os.environ.get("MT_AK") and os.environ.get("MT_SK")):
        raise ErroreConfig("Chiavi Vmake mancanti: imposta MT_AK e MT_SK nell'ambiente (o nel .env)")

    stato = p.file(".vmake_task.json")
    client = SkillClient()
    try:
        if stato.exists():
            tid = json.loads(stato.read_text())["task_id"]
            print(f"  → riprendo il lavoro Vmake già inviato ({tid})")
            res = _poll_con_ritenti(client, tid)
        else:
            print(f"  → upload su Vmake e avvio '{task}' (consuma quota)")
            salva = lambda tid: stato.write_text(json.dumps({"task_id": tid, "task": task}))
            try:
                res = client.run_task(task, str(src), on_async_submitted=salva)
            except Exception as e:  # timeout durante il polling: il lavoro è già inviato, si riprende
                if not stato.exists() or "timeout" not in type(e).__name__.lower():
                    raise
                print(f"  ! {type(e).__name__} durante l'attesa, riprendo il polling")
                res = _poll_con_ritenti(client, json.loads(stato.read_text())["task_id"])
    except ErroreConfig:
        raise
    except Exception as e:  # l'SDK solleva eccezioni proprie per quota, config e rete
        raise ErroreConfig(f"Errore Vmake: {type(e).__name__}: {e}")

    url = _url_video(res)
    if not url:
        dettaglio = json.dumps(res, ensure_ascii=False)[:800] if res else "nessuna risposta (timeout)"
        msg = "rilancia `pulisci` per riprendere il polling" if stato.exists() else "nessun lavoro inviato"
        raise ErroreConfig(f"Vmake non ha restituito il video ({msg}). Risposta: {dettaglio}")

    r = requests.get(url, stream=True, timeout=600)
    r.raise_for_status()
    with out.open("wb") as fh:
        for blocco in r.iter_content(1 << 20):
            fh.write(blocco)
    stato.unlink(missing_ok=True)


def _poll_con_ritenti(client, tid: str, tentativi: int = 10):
    """L'SDK aspetta il server solo 3 s: sui timeout di rete si riprova invece di fermarsi."""
    import time

    for i in range(tentativi):
        try:
            return client.poll_task_status(tid)
        except Exception as e:
            if "timeout" not in type(e).__name__.lower() or i == tentativi - 1:
                raise
            print(f"  ! {type(e).__name__}, nuovo tentativo ({i + 2}/{tentativi})")
            time.sleep(5)


def _url_video(res) -> str | None:
    """Trova l'URL del risultato: prima output_urls, poi qualunque URL http nella risposta."""
    if not isinstance(res, dict) or res.get("error") or res.get("skill_status") == "failed":
        return None
    urls = res.get("output_urls") or []
    if not urls:
        def cerca(x):
            if isinstance(x, dict):
                for v in x.values():
                    yield from cerca(v)
            elif isinstance(x, list):
                for v in x:
                    yield from cerca(v)
            elif isinstance(x, str) and x.startswith("http"):
                yield x
        urls = list(cerca(res.get("data", res)))
    urls = [u["url"] if isinstance(u, dict) else u for u in urls]
    video = [u for u in urls if u.split("?")[0].lower().endswith((".mp4", ".mov", ".webm"))]
    return (video or urls or [None])[0]
