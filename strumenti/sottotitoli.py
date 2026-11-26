"""Sottotitoli "stile TikTok" (riquadro bianco arrotondato, testo nero minuscolo) impressi nel video.
I tempi vengono dalle parole di Whisper sulla voce del video (o su un file di parole già pronto).
uso: python3 strumenti/sottotitoli.py video_in.mp4 video_out.mp4 [parole.json] [--testo script_it.txt] [--y 0.68] [--offset s]"""
import sys, os, json, re, subprocess, os, tempfile
from PIL import Image, ImageDraw, ImageFont

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "risorse", "font", "montserrat-latin-600-normal.woff")
MAXC = 40          # caratteri massimi per sottotitolo (su due righe)
NOMI = {"Revive", "Luca", "Rosa", "Marco", "Lisa", "Giorgio", "Martina", "Daniele"}
CORREZIONI = [(r"cìclo", "ciclo"), (r"proteàsi", "proteasi"), (r"lipàsi", "lipasi"), (r"amilàsi", "amilasi"), (r"(\d) ?\. ?(\d{3})", r"\1.\2"), (r"\bha maggior ragione\b", "a maggior ragione"), (r"\btoilettatrice\b", "toelettatrice"), (r"\bla milasi\b", "l'amilasi"), (r"\bl alipasi\b", "la lipasi"), (r"\bin credula\b", "incredula"), (r"\bri[vb][aà]iv\s*dr[ua]m\b", "Revive Drum"), (r"\brevive\s*drum\b", "Revive Drum"), (r"\brevivedrum\b", "Revive Drum")]


def parole_da_video(video):
    from faster_whisper import WhisperModel
    m = WhisperModel("large-v3", compute_type="int8")
    segs, _ = m.transcribe(video, language="it", word_timestamps=True, initial_prompt="Revive Drum")
    return [(x.start, x.end, x.word.strip()) for s in segs for x in s.words]


def unisci_apostrofi(parole):
    """Whisper a volte spezza "l'offerta" in "l" + "'offerta": riunisce le due parti."""
    out = []
    for s, e, w in parole:
        if out and (w.startswith("'") or out[-1][2].endswith("'")):
            ps, pe, pw = out[-1]; out[-1] = (ps, e, pw + w)
        else: out.append((s, e, w))
    return out


def allinea_testo(testo, parole):
    """Parole dello script con i tempi delle parole di Whisper (allineamento per sequenza)."""
    import difflib
    testo = re.sub(r"^\[.*?\]\s*$", "", testo, flags=re.M).replace("Rivàiv Dram", "Revive Drum")
    sw = testo.split()
    norm = lambda w: re.sub(r"[^a-z0-9àèéìòù]", "", w.lower().replace("rivàiv", "revive"))
    a = [norm(w) for w in sw]; b = [norm(w[2]) for w in parole]
    tempi = [None] * len(sw)
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal":
            for k in range(i2 - i1): tempi[i1 + k] = (parole[j1 + k][0], parole[j1 + k][1])
        elif op == "replace" and j2 > j1:
            t0, t1 = parole[j1][0], parole[j2 - 1][1]; n = i2 - i1
            for k in range(n): tempi[i1 + k] = (t0 + (t1 - t0) * k / n, t0 + (t1 - t0) * (k + 1) / n)
    # parole senza tempo: interpola tra le vicine
    for i in range(len(sw)):
        if tempi[i] is None:
            prev = next((tempi[j][1] for j in range(i - 1, -1, -1) if tempi[j]), 0.0)
            nxt = next((tempi[j][0] for j in range(i + 1, len(sw)) if tempi[j]), prev + 0.3)
            tempi[i] = (prev, max(prev + 0.05, min(nxt, prev + 0.3)))
    return [(t[0], t[1], w) for t, w in zip(tempi, sw)]


def blocchi(parole):
    parole = unisci_apostrofi(parole)
    out, cur = [], []
    for i, (a, b, w) in enumerate(parole):
        cur.append((a, b, w))
        testo = " ".join(x[2] for x in cur)
        fine_frase = re.search(r"[.?!:]$", w)
        pausa = i + 1 < len(parole) and parole[i + 1][0] - b > 0.35
        prossimo = len(testo) + 1 + (len(parole[i + 1][2]) if i + 1 < len(parole) else 0)
        if fine_frase or (pausa and len(testo) > 8) or prossimo > MAXC or (re.search(r",$", w) and len(testo) > 18):
            out.append(cur); cur = []
    if cur: out.append(cur)
    res = []
    for k, c in enumerate(out):
        t = " ".join(x[2] for x in c)
        for a, b in CORREZIONI: t = re.sub(a, b, t, flags=re.I)
        t = re.sub(r"[.,;:!]+$", "", t).strip()
        for n in NOMI: t = re.sub(r"\b" + n.lower() + r"\b", n, t) if n != "Revive" else t
        t = t[0].lower() + t[1:] if t and t.split()[0].strip(",") not in NOMI else t
        inizio = c[0][0]; fine = out[k + 1][0][0] if k + 1 < len(out) else c[-1][1] + 0.3
        fine = min(fine, c[-1][1] + 0.6)
        res.append((inizio, fine, t))
    return res


def png(testo, W, path):
    fn = ImageFont.truetype(FONT, int(W * 0.05)); maxw = W * 0.70
    righe, cur = [], ""
    for p in testo.split():
        t = (cur + " " + p).strip()
        if fn.getlength(t) <= maxw: cur = t
        else: righe.append(cur); cur = p
    righe.append(cur)
    lh = int(fn.size * 1.22); pad = int(fn.size * 0.55); bb = fn.getbbox("Ag")
    w = max(fn.getlength(r) for r in righe) + 2 * pad; h = lh * len(righe) + pad * 1.2
    im = Image.new("RGBA", (int(w) + 4, int(h) + 4), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, w, h], int(fn.size * 0.45), fill=(255, 255, 255, 255))
    for i, r in enumerate(righe):
        d.text(((w - fn.getlength(r)) / 2 + 2, 2 + pad * 0.6 + i * lh - bb[1] + (lh - (bb[3] - bb[1])) / 2), r, font=fn, fill=(15, 15, 15))
    im.save(path); return im.size


def main():
    a = sys.argv[1:]; vin, vout = a[0], a[1]
    yrel = float(a[a.index("--y") + 1]) if "--y" in a else 0.68
    off = float(a[a.index("--offset") + 1]) if "--offset" in a else 0.0
    pj = next((x for x in a[2:] if x.endswith(".json")), None)
    parole = [tuple(x) for x in json.load(open(pj))] if pj else parole_da_video(vin)
    if not pj: json.dump([list(map(lambda v: v if isinstance(v, str) else float(v), x)) for x in parole], open(vout + ".parole.json", "w"), ensure_ascii=False)
    if "--testo" in a:  # usa il testo dello script (punteggiatura e parole giuste) con i tempi di Whisper
        parole = allinea_testo(open(a[a.index("--testo") + 1]).read(), parole)
    parole = [(s + off, e + off, w) for s, e, w in parole]
    W, H = map(int, subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width,height", "-of", "csv=p=0", vin], capture_output=True, text=True).stdout.split(",")[:2])
    tmp = tempfile.mkdtemp(); ins = ["-i", vin]; fc = []; prev = "0:v"
    subs = blocchi(parole)
    for k, (s, e, t) in enumerate(subs):
        p = os.path.join(tmp, f"{k:04d}.png"); w, h = png(t, W, p); ins += ["-i", p]
        fc.append(f"[{prev}][{k+1}:v]overlay=x=(W-w)/2:y={int(H*yrel)}-h/2:enable='between(t,{s:.3f},{e:.3f})'[v{k}]"); prev = f"v{k}"
    script = os.path.join(tmp, "fc.txt"); open(script, "w").write(";".join(fc))
    subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex_script", script, "-map", f"[{prev}]", "-map", "0:a?",
                    "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-c:a", "copy", vout], check=True)
    json.dump(subs, open(vout + ".sottotitoli.json", "w"), ensure_ascii=False, indent=0)
    print("ok", vout, len(subs), "sottotitoli")


if __name__ == "__main__":
    main()
