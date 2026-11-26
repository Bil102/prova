"""Usa il video pulito da WaveSpeed solo in alcune fasce (sottotitoli sempre, titoli in certi intervalli):
fuori dalle fasce rimette l'originale, così scatole ed etichette restano intatte.
uso: python3 strumenti/pulisci_solo_fasce.py originale.mp4 pulito.mp4 uscita.mp4 "y0-y1" ["y0-y1@t0-t1" ...]"""
import sys, subprocess
import cv2, numpy as np

orig, pul, out = sys.argv[1:4]; fasce = []
for a in sys.argv[4:]:
    zona, _, tempo = a.partition("@"); y0, y1 = map(int, zona.split("-"))
    t0, t1 = map(float, tempo.split("-")) if tempo else (0, 1e9); fasce.append((y0, y1, t0, t1))
o = cv2.VideoCapture(orig); c = cv2.VideoCapture(pul); fps = o.get(5); W, H = int(o.get(3)), int(o.get(4))
def maschera(t):
    m = np.zeros((H, W), np.float32)
    for y0, y1, t0, t1 in fasce:
        if t0 <= t <= t1: m[max(0, y0):min(H, y1)] = 1
    return cv2.GaussianBlur(m, (1, 31), 0)[..., None]
p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
                      "-i", orig, "-map", "0:v", "-map", "1:a?", "-c:v", "libx264", "-crf", "17", "-pix_fmt", "yuv420p", "-c:a", "copy", "-shortest", out], stdin=subprocess.PIPE)
i = 0
while True:
    ok, a = o.read(); ok2, b = c.read()
    if not ok or not ok2: break
    if b.shape[:2] != (H, W): b = cv2.resize(b, (W, H))
    m = maschera(i / fps); p.stdin.write((a * (1 - m) + b * m).astype(np.uint8).tobytes()); i += 1
p.stdin.close(); p.wait(); print("ok", out, i, "fotogrammi")
