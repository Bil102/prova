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
        if isinstance(a, (int, float)): tempi.append(float(a)); continue
        q = norm(a).split()
        for k in range(da, len(pw)):
            if pw[k:k + len(q)] == q: tempi.append(parole[k][0]); da = k + 1; break
        else: raise SystemExit(f"ancora non trovata: {a}")
    blocchi = sorted(glob.glob(P + "/voce/[0-9][0-9]_*.mp3"))
    assert len(blocchi) == len(tempi), (len(blocchi), len(tempi))
    traccia = np.zeros(int((durata + 5) * SR), np.float32); fine_prec = 0.0
    for i, f in enumerate(blocchi):
        x = taglia(leggi(f)); d = len(x) / SR
        t0 = max(tempi[i], fine_prec + 0.12)
        spazio = (tempi[i + 1] if i + 1 < len(tempi) else durata) - t0 - 0.12
        if d > spazio and spazio > 0.5:
            f2 = min(d / spazio, 1.25); x = atempo(x, f2); d = len(x) / SR
            segs = [(0.0, x)]; s = 1.0
        else:
            segs = pezzi(x); s = min(spazio * 0.95 / d, 1.8) if d > 0 and len(segs) > 1 else 1.0
        for off, seg in segs:
            st = int((t0 + off * s) * SR); traccia[st:st + len(seg)] += seg[:len(traccia) - st]
            fine_prec = max(fine_prec, t0 + off * s + len(seg) / SR)
        print(f"{i+1:02d} ancora {tempi[i]:6.1f}  parte {t0:6.1f}  dura {d:5.1f}  spazio {spazio:5.1f}  pezzi {len(segs)}")
    traccia = traccia[:int(durata * SR)]
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", out], input=np.clip(traccia, -1, 1).tobytes())


if __name__ == "__main__":
    main()
