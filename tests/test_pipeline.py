"""Test end-to-end con media sintetici: nessuna chiamata API reale (ElevenLabs e Claude simulati)."""

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import localizza
from pipeline import ff, monta, traduci, verifica, voce
from pipeline.config import Progetto


def genera(args, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args, str(out)], check=True)
    return out


@pytest.fixture
def progetto(tmp_path):
    src = genera(["-f", "lavfi", "-i", "testsrc2=s=360x640:r=30:d=6", "-f", "lavfi",
                  "-i", "sine=f=300:d=6", "-c:v", "libx264", "-c:a", "aac", "-shortest"], tmp_path / "spot.mp4")
    assert localizza.main(["init", str(src), "--nome", "spot", "--cartella", str(tmp_path / "progetti")]) == 0
    d = tmp_path / "progetti" / "spot"
    genera(["-f", "lavfi", "-i", "smptebars=s=640x360:r=25:d=5"], d / "broll.mp4")
    genera(["-f", "lavfi", "-i", "sine=f=500:d=3"], d / "musica.mp3")
    toml = (d / "progetto.toml").read_text()
    toml = toml.replace('genere = ""', 'genere = "uomo"').replace('narratore = "VOICE_ID"', 'narratore = "v1"')
    toml = toml.replace('metodo = "vmake"', 'metodo = "delogo"\narea = [0, 520, 360, 100]', 1)
    toml = toml.replace('file = ""', 'file = "musica.mp3"')
    toml = toml.replace("larghezza = 1080\naltezza = 1920", "larghezza = 540\naltezza = 960")
    toml = toml.replace("# Tim = \"Marco\"", 'Tim = "Marco"')
    toml += """
[[montaggio.broll]]
clip = "broll.mp4"
inizio = 1.0
fine = 2.5

[[montaggio.overlay]]
immagine = "overlay_offerta.png"
inizio = 3.0
fine = 5.0
y = "H*0.7"
dissolvenza = 0.3
"""
    (d / "progetto.toml").write_text(toml)
    return d


def finto_elevenlabs(tmp_path, durata):
    mp3 = genera(["-f", "lavfi", "-i", f"sine=f=440:d={durata}", "-ac", "1"], tmp_path / "tts.mp3")
    chiamate = []

    def post(url, **kw):
        chiamate.append(kw["json"])
        return SimpleNamespace(status_code=200, content=mp3.read_bytes(), text="")
    return post, chiamate


def test_pipeline_completa(progetto, tmp_path, monkeypatch):
    d = progetto
    (d / "script_it.txt").write_text("Ciao, sono Marco.\n\nHo provato Rivàiv Dram.\n")
    monkeypatch.setenv("ELEVENLABS_API_KEY", "x")
    post, chiamate = finto_elevenlabs(tmp_path, 7.0)  # voce più lunga del video (6s)
    monkeypatch.setattr("requests.post", post)

    assert localizza.main(["grafica", str(d), "offerta", "COMPRA 2, PRENDINE 2 GRATIS", "--larghezza", "300",
                           "--dim-font", "28"]) == 0
    # trascrivi/traduci richiedono API reali: qui si parte da uno script_it.txt già pronto
    for step in ["pulisci", "voce", "monta", "musica", "esporta"]:
        assert localizza.main([step, str(d)]) == 0, step

    assert len(chiamate) == 1
    D, vel, fermo = monta.calcola_tempi(6.0, 7.0, "auto", 1.08, 0.5)
    assert abs(ff.durata(d / "montaggio.mp4") - D) < 0.15
    fin = d / "video_finale_it.mp4"
    assert ff.dimensioni(fin) == (540, 960)
    assert ff.ha_audio(fin)
    assert abs(ff.durata(fin) - D) < 0.15

    # seconda esecuzione: blocco invariato → nessuna nuova chiamata
    assert localizza.main(["voce", str(d)]) == 0
    assert len(chiamate) == 1


def test_calcola_tempi():
    assert monta.calcola_tempi(10, 8, "auto", 1.08, 0.5) == (8.5, 1.0, 0.0)
    D, v, f = monta.calcola_tempi(10, 10.5, "auto", 1.08, 0.5)
    assert v == pytest.approx(1.05) and f == pytest.approx(0.5, abs=0.01)
    D, v, f = monta.calcola_tempi(10, 13, "auto", 1.08, 0.0)
    assert v == 1.08 and f == pytest.approx(13 / 1.08 - 10, abs=0.01)
    assert monta.calcola_tempi(10, 13, "congela", 1.08, 0.0) == (13, 1.0, 3)
    assert monta.calcola_tempi(10, 13, "nessuno", 1.08, 0.5) == (10, 1.0, 0.0)


def test_dividi_speaker():
    b = voce.dividi("[Marco]\nCiao.\n\nCome va?\n# nota interna\n[Giulia]\nBene!\n")
    assert [(x.speaker, x.testo) for x in b] == [("Marco", "Ciao.\n\nCome va?"), ("Giulia", "Bene!")]
    assert voce.dividi("Solo testo.")[0].speaker == "narratore"


def test_verifica_regole():
    testo = ("Ho provato ReviveDrum (0:05).\nCosta $9.99 a scatola, meglio di Tide.\n"
             "Tim lo adora.\nHo speso 120€ prima di scoprirlo.\nRivàiv Dram Pro è fantastico.\n")
    pr = verifica.controlla(testo, nomi_originali=["Tim"])
    errori = {(p.riga, p.messaggio.split("'")[1]) for p in pr if p.livello == "ERRORE"}
    assert (1, "ReviveDrum") in errori and (1, "(0:05)") in errori
    assert (2, "$9.99") in errori and (2, "Tide") in errori and (3, "Tim") in errori
    avvisi = {p.riga for p in pr if p.livello == "AVVISO"}
    assert {4, 5} <= avvisi
    assert verifica.controlla("Ciao, sono Marco.\n\nRivàiv Dram funziona davvero.\n") == []


def finto_claude(monkeypatch, risposta):
    import anthropic

    class Msgs:
        def create(self, **kw):
            Msgs.kw = kw
            return SimpleNamespace(stop_reason="end_turn",
                                   content=[SimpleNamespace(type="text", text=json.dumps(risposta))])

    monkeypatch.setattr(anthropic, "Anthropic", lambda: SimpleNamespace(beta=SimpleNamespace(messages=Msgs())))
    return Msgs


def test_traduci_nome_nuovo_richiede_conferma(progetto, monkeypatch):
    d = progetto
    (d / "transcript_en.txt").write_text("[00:00.0 → 00:02.0] Hi, I'm Rick and I love ReviveDrum.\n")
    finto_claude(monkeypatch, {"script_it": "Ciao, sono Luca.\n\nAdoro Rivàiv Dram.",
                               "sostituzioni": [{"tipo": "nome_persona", "originale": "Rick", "sostituto": "Luca"}],
                               "domande": []})
    assert localizza.main(["traduci", str(d)]) == 2
    assert (d / "script_it.bozza.txt").exists() and not (d / "script_it.txt").exists()
    assert "Rick → **Luca**" in (d / "note_adattamento.md").read_text()
    assert localizza.main(["traduci", str(d), "--accetta"]) == 0
    assert (d / "script_it.txt").read_text().startswith("Ciao, sono Luca.")


def test_traduci_passa_regole_e_dati(progetto, monkeypatch):
    d = progetto
    (d / "transcript_en.txt").write_text("[00:00.0 → 00:02.0] Hi, I'm Tim.\n")
    M = finto_claude(monkeypatch, {"script_it": "Ciao, sono Marco.",
                                   "sostituzioni": [{"tipo": "nome_persona", "originale": "Tim", "sostituto": "Marco"}],
                                   "domande": []})
    assert localizza.main(["traduci", str(d)]) == 0
    assert "Rivàiv Dram" in M.kw["system"]
    utente = M.kw["messages"][0]["content"]
    assert "Genere del narratore: uomo" in utente and "Tim → Marco" in utente


def test_traduci_senza_genere(progetto):
    t = (progetto / "progetto.toml").read_text().replace('genere = "uomo"', 'genere = ""')
    (progetto / "progetto.toml").write_text(t)
    (progetto / "transcript_en.txt").write_text("x")
    assert localizza.main(["traduci", str(progetto)]) == 1


def test_pulisci_vmake_sdk(progetto, tmp_path, monkeypatch):
    import action_api_sdk
    d = progetto
    t = (d / "progetto.toml").read_text().replace('metodo = "delogo"', 'metodo = "vmake"')
    (d / "progetto.toml").write_text(t)
    monkeypatch.setenv("MT_AK", "ak")
    monkeypatch.setenv("MT_SK", "sk")
    risultato = genera(["-f", "lavfi", "-i", "testsrc2=s=360x640:r=30:d=2"], tmp_path / "pulito.mp4")
    chiamate = []

    class FintoClient:
        def run_task(self, task, path, on_async_submitted=None):
            chiamate.append((task, path))
            on_async_submitted("T123")
            assert json.loads((d / ".vmake_task.json").read_text())["task_id"] == "T123"
            return {"skill_status": "completed", "output_urls": ["https://cdn.example/out.mp4?sig=1"]}

    def get(url, **kw):
        assert url.startswith("https://cdn.example/out.mp4")
        dati = risultato.read_bytes()
        return SimpleNamespace(raise_for_status=lambda: None, iter_content=lambda n: [dati])

    monkeypatch.setattr(action_api_sdk, "SkillClient", FintoClient)
    monkeypatch.setattr("requests.get", get)
    assert localizza.main(["pulisci", str(d)]) == 0
    assert chiamate == [("SKM0005", str(d / "originale.mp4"))]
    assert ff.durata(d / "video_clean.mp4") == pytest.approx(2, abs=0.1)
    assert not (d / ".vmake_task.json").exists()


def test_pulisci_vmake_senza_chiavi(progetto, monkeypatch):
    t = (progetto / "progetto.toml").read_text().replace('metodo = "delogo"', 'metodo = "vmake"')
    (progetto / "progetto.toml").write_text(t)
    monkeypatch.delenv("MT_AK", raising=False)
    monkeypatch.delenv("MT_SK", raising=False)
    assert localizza.main(["pulisci", str(progetto)]) == 1
