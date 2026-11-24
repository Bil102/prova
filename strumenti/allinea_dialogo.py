"""Allinea i blocchi della voce italiana (progetti/<p>/voce/NN_*.mp3) ai tempi delle battute del video originale.
Ancore: per ogni blocco le prime parole della battuta inglese corrispondente (cercate in ordine nelle parole di
Whisper dell'originale) oppure un tempo in secondi. Dentro un blocco lungo le frasi vengono distribuite in
proporzione sullo spazio della battuta inglese. Uscita: traccia WAV lunga quanto l'originale.
uso: python3 strumenti/allinea_dialogo.py progetti/<p> ancore.json uscita.wav"""
import sys, json, glob, re, subprocess
import numpy as np

SR = 44100


def leggi(f):
    x = subprocess.run(["ffmpeg", "-v", "error", "-i", f, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"], capture_output=True).stdout
    return np.frombuffer(x, np.float32).copy()


def taglia(x, soglia=0.01):
    e = np.convolve(np.abs(x), np.ones(441) / 441, "same"); idx = np.where(e > soglia)[0]
    return x[max(0, idx[0] - 441):idx[-1] + 2205] if len(idx) else x


def pezzi(x, soglia=0.008, minpausa=0.22):
    """divide alle pause interne: lista di (offset_s, campioni)"""
    e = np.convolve(np.abs(x), np.ones(441) / 441, "same") > soglia
    out, i, n = [], 0, len(x); start = 0; silenzio = 0
    for j in range(0, n, 441):
        if e[j]: 
            if silenzio >= minpausa * SR and j - silenzio > start:
                fine = j - silenzio + 2205; out.append((start / SR, x[start:fine])); start = j - 2205
            silenzio = 0
        else: silenzio += 441
    out.append((start / SR, x[start:])); return out


def atempo(x, f):
    if abs(f - 1) < 0.01: return x
    p = subprocess.run(["ffmpeg", "-v", "error", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", "-af", f"atempo={f:.4f}", "-f", "f32le", "-"], input=x.tobytes(), capture_output=True)
    return np.frombuffer(p.stdout, np.float32).copy()


def main():
    P, anc, out = sys.argv[1:4]
    parole = json.load(open(P + "/parole_en.json")); ancore = json.load(open(anc)); durata = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", P + "/originale.mp4"], capture_output=True, text=True).stdout)
    norm = lambda s: re.sub(r"[^a-z0-9 ]", "", s.lower())
    pw = [norm(w[2]) for w in parole]; tempi = []; da = 0
    for a in ancore:
        if a == "SALTA": tempi.append(None); continue
        if isinstance(a, (int, float)): tempi.append(float(a)); continue
        q = norm(a).split()
        for k in range(da, len(pw)):
            if pw[k:k + len(q)] == q: tempi.append(parole[k][0]); da = k + 1; break
        else: raise SystemExit(f"ancora non trovata: {a}")
    # inizi di frase inglesi: dopo punteggiatura o dopo una pausa (Whisper spesso non mette i punti)
    frasi_en = [parole[0][0]] + [parole[k + 1][0] for k in range(len(parole) - 1) if re.search(r"[.?!]$", parole[k][2]) or parole[k + 1][0] - parole[k][1] > 0.45]
    from faster_whisper import WhisperModel
    wm = WhisperModel("large-v3", compute_type="int8")
    blocchi = sorted(glob.glob(P + "/voce/[0-9][0-9]_*.mp3"))
    assert len(blocchi) == len(tempi), (len(blocchi), len(tempi))
    traccia = np.zeros(int((durata + 5) * SR), np.float32); fine_prec = 0.0
    vivi = [i for i in range(len(blocchi)) if tempi[i] is not None]
    for n_i, i in enumerate(vivi):
        f = blocchi[i]
        x = taglia(leggi(f)); d = len(x) / SR
        prossimo = tempi[vivi[n_i + 1]] if n_i + 1 < len(vivi) else durata
        spazio0 = prossimo - max(tempi[i], fine_prec + 0.1) - 0.15
        if d > spazio0 > 0.5:  # la battuta italiana non ci sta: la accelero un po' (max 1.25)
            x = atempo(x, min(d / spazio0, 1.25)); d = len(x) / SR
        # frasi italiane del blocco (da Whisper) e frasi inglesi nello spazio della battuta
        tmpf = "/tmp/claude-0/-home-user-prova/12bba21e-1c99-5858-a6f5-edb34532672e/scratchpad/_blk.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", tmpf], input=x.tobytes())
        ws = [w for sg in wm.transcribe(tmpf, language="it", word_timestamps=True)[0] for w in sg.words]
        cuts = [0.0] + [ (ws[k].end + ws[k + 1].start) / 2 for k in range(len(ws) - 1) if re.search(r"[.?!]$", ws[k].word.strip())]
        en = [t for t in frasi_en if tempi[i] - 0.05 <= t < prossimo - 0.05] or [tempi[i]]
        if len(cuts) > 1:
            fr = [x[int(cuts[k] * SR):int((cuts[k + 1] if k + 1 < len(cuts) else d) * SR)] for k in range(len(cuts))]
            fine_loc = fine_prec
            for k, seg in enumerate(fr):
                tk = en[min(len(en) - 1, round(k * len(en) / len(fr)))] if len(en) > 1 else None
                st = max(tk if tk is not None else fine_loc + 0.08, fine_loc + 0.08, tempi[i] if k == 0 else 0)
                a_ = int(st * SR); traccia[a_:a_ + len(seg)] += seg[:len(traccia) - a_]; fine_loc = st + len(seg) / SR
            fine_prec = fine_loc
            print(f"{i+1:02d} ancora {tempi[i]:6.1f}  frasi it {len(fr)} en {len(en)}  fine {fine_prec:6.1f}")
            continue
        t0 = max(tempi[i], fine_prec + 0.12)
        spazio = prossimo - t0 - 0.12
        if d > spazio and spazio > 0.5:
            f2 = min(d / spazio, 1.25); x = atempo(x, f2); d = len(x) / SR
            segs = [(0.0, x)]; s = 1.0
        else:
            segs = [(0.0, x)]; s = 1.0  # ritmo naturale: niente pause allungate dentro la battuta
        for off, seg in segs:
            st = int((t0 + off * s) * SR); traccia[st:st + len(seg)] += seg[:len(traccia) - st]
            fine_prec = max(fine_prec, t0 + off * s + len(seg) / SR)
        print(f"{i+1:02d} ancora {tempi[i]:6.1f}  parte {t0:6.1f}  dura {d:5.1f}  spazio {spazio:5.1f}  pezzi {len(segs)}")
    traccia = traccia[:int(durata * SR)]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", out], input=np.clip(traccia, -1, 1).tobytes())


if __name__ == "__main__":
    main()
