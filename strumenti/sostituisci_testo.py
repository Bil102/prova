"""Sostituisce scritte in un tratto di video seguendo il movimento della camera.
Le modifiche si disegnano su un fotogramma di riferimento (quadrilateri riempiti col colore di fondo +
testo nuovo), poi per ogni fotogramma si stima l'omografia rif->fotogramma (SIFT + RANSAC) e la toppa
viene deformata e incollata.
uso: python3 strumenti/sostituisci_testo.py spec.json   (vedi chiavi in main)"""
import json, os, sys, subprocess
import cv2, numpy as np
from PIL import Image, ImageDraw, ImageFont

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "risorse", "font", "montserrat-latin-{}-normal.woff")


def colore(img, quad, c):
    if c != "auto":
        return tuple(c)
    m = np.zeros(img.shape[:2], np.uint8)
    cv2.fillConvexPoly(m, np.int32(quad), 255)
    bordo = cv2.dilate(m, np.ones((7, 7), np.uint8)) - m
    return tuple(int(v) for v in np.median(img[bordo > 0], axis=0)[::-1])  # BGR -> RGB


def toppa(ref, edits):
    H, W = ref.shape[:2]
    over = ref.copy(); mask = np.zeros((H, W), np.float32)
    for e in edits:
        q = np.float32(e["quad"])
        w = int(np.linalg.norm(q[1] - q[0])); h = int(np.linalg.norm(q[3] - q[0]))
        sc = 4
        R = np.float32([[0, 0], [w * sc, 0], [w * sc, h * sc], [0, h * sc]])
        if e.get("fondo") == "inpaint":
            # toglie la scritta vecchia ricostruendo lo sfondo (gradienti e riflessi compresi)
            m0 = np.zeros(ref.shape[:2], np.uint8); cv2.fillConvexPoly(m0, np.int32(q), 255)
            g = cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY).astype(np.int16)
            fondo = cv2.medianBlur(ref, 31); gf = cv2.cvtColor(fondo, cv2.COLOR_BGR2GRAY).astype(np.int16)
            soglia = e.get("soglia", 25)
            tm = ((np.abs(g - gf) > soglia) & (m0 > 0)).astype(np.uint8) * 255
            tm = cv2.dilate(tm, np.ones((5, 5), np.uint8), iterations=2) & m0
            pulito = cv2.inpaint(ref, tm, 7, cv2.INPAINT_TELEA)
            Mi = cv2.getPerspectiveTransform(q, R)
            can = Image.fromarray(cv2.cvtColor(cv2.warpPerspective(pulito, Mi, (w * sc, h * sc), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE), cv2.COLOR_BGR2RGB))
        else:
            can = Image.new("RGB", (w * sc, h * sc), colore(ref, q, e.get("fondo", "auto")))
        d = ImageDraw.Draw(can)
        righe = e["righe"]; tot = sum(r.get("dim", 20) * r.get("interlinea", 1.25) for r in righe)
        y = (h - tot) / 2 if e.get("valign", "center") == "center" else e.get("pad", 0)
        for r in righe:
            fn = ImageFont.truetype(FONT.format(r.get("peso", 600)), int(r.get("dim", 20) * sc))
            parti = r["testo"] if isinstance(r["testo"], list) else [[r["testo"], r.get("colore", [20, 20, 20])]]
            tw = sum(fn.getlength(p[0]) for p in parti); al = r.get("allinea", e.get("allinea", "left"))
            x = {"left": e.get("pad", 0) * sc, "center": (w * sc - tw) / 2, "right": w * sc - tw - e.get("pad", 0) * sc}[al]
            for t, col in parti:
                d.text((x, y * sc), t, font=fn, fill=tuple(col)); x += fn.getlength(t)
            y += r.get("dim", 20) * r.get("interlinea", 1.25)
        can = cv2.cvtColor(np.array(can.resize((w * 2, h * 2), Image.LANCZOS)), cv2.COLOR_RGB2BGR)
        M = cv2.getPerspectiveTransform(np.float32([[0, 0], [w * 2, 0], [w * 2, h * 2], [0, h * 2]]), q)
        warped = cv2.warpPerspective(can, M, (W, H), flags=cv2.INTER_AREA, borderMode=cv2.BORDER_REPLICATE)
        m = np.zeros((H, W), np.float32); cv2.fillConvexPoly(m, np.int32(q), 1.0)
        over[m > 0] = warped[m > 0]; mask = np.maximum(mask, m)
    return over, cv2.GaussianBlur(mask, (9, 9), 0)


def main():
    s = json.load(open(sys.argv[1]))
    cap = cv2.VideoCapture(s["video"]); fps = cap.get(5)
    cap.set(1, s["rif"]); ok, ref = cap.read()
    over, mask = toppa(ref, s["modifiche"])
    if s.get("anteprima"):
        out = (ref * (1 - mask[..., None]) + over * mask[..., None]).astype(np.uint8); cv2.imwrite(s["anteprima"], out)
        if s.get("solo_anteprima"): return
    sift = cv2.SIFT_create(4000)
    roi = np.zeros(ref.shape[:2], np.uint8); x0, y0, x1, y1 = s["roi"]; roi[y0:y1, x0:x1] = 255
    kr, dr = sift.detectAndCompute(cv2.cvtColor(ref, cv2.COLOR_BGR2GRAY), roi)
    bf = cv2.BFMatcher(); cap.set(1, s["inizio"]); Hs = []; frames = []
    for n in range(s["inizio"], s["fine"]):
        ok, fr = cap.read()
        if not ok: break
        kf, df = sift.detectAndCompute(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), None)
        good = [m for m, n2 in bf.knnMatch(dr, df, k=2) if m.distance < 0.75 * n2.distance]
        Hm = None
        if len(good) >= 12:
            Hm, _ = cv2.findHomography(np.float32([kr[m.queryIdx].pt for m in good]), np.float32([kf[m.trainIdx].pt for m in good]), cv2.RANSAC, 3.0)
        Hs.append(Hm if Hm is not None else (Hs[-1] if Hs else np.eye(3))); frames.append(fr)
    # smussa le omografie (media mobile su 3 fotogrammi) per togliere il tremolio
    Hs = [np.mean([Hs[j] / Hs[j][2, 2] for j in range(max(0, i - 1), min(len(Hs), i + 2))], axis=0) for i in range(len(Hs))]
    h, w = ref.shape[:2]
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-",
                          "-vf", f"setpts=PTS/{s.get('velocita', 1.0)}", "-r", "30", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", s["uscita"]], stdin=subprocess.PIPE)
    for fr, Hm in zip(frames, Hs):
        o = cv2.warpPerspective(over, Hm, (w, h)).astype(np.float32); mk = cv2.warpPerspective(mask, Hm, (w, h))[..., None]
        # corregge luminosita/colore della toppa sul fotogramma corrente (anello intorno alla toppa)
        rr = cv2.warpPerspective(ref, Hm, (w, h)).astype(np.float32)
        anello = (cv2.dilate((mk[..., 0] > 0.01).astype(np.uint8), np.ones((15, 15), np.uint8)) > 0) & (mk[..., 0] < 0.01)
        if anello.sum() > 50:
            k = (fr[anello].astype(np.float32).mean(0) + 1) / (rr[anello].mean(0) + 1); o = np.clip(o * k, 0, 255)
        p.stdin.write((fr * (1 - mk) + o * mk).astype(np.uint8).tobytes())
    p.stdin.close(); p.wait(); print("ok", s["uscita"], len(frames), "fotogrammi")


if __name__ == "__main__":
    main()
