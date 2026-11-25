"""Toglie sottotitoli/scritte impressi da un video con WaveSpeed (modello video-watermark-remover).
La chiave API la inietta il proxy dell'ambiente su api.wavespeed.ai (header Authorization: Bearer).
Costo indicativo: 0,01 $/s (1 min = 0,60 $).  Video oltre 10 minuti: va diviso prima.
uso: python3 strumenti/pulisci_wavespeed.py video_in.mp4 video_pulito.mp4 [--modello wavespeed-ai/video-eraser --prompt "subtitles"]"""
import sys, time, json, os, subprocess, requests

API = "https://api.wavespeed.ai/api/v3"
H = {"Authorization": "Bearer " + os.environ.get("WAVESPEED_API_KEY", "proxy-injected")}


def carica(path):
    with open(path, "rb") as f:
        r = requests.post(f"{API}/media/upload/binary", headers=H, files={"file": (os.path.basename(path), f, "video/mp4")}, timeout=900)
    r.raise_for_status(); d = r.json().get("data", r.json())
    return d.get("download_url") or d.get("url")


def main():
    a = sys.argv[1:]; vin, vout = a[0], a[1]
    modello = a[a.index("--modello") + 1] if "--modello" in a else "wavespeed-ai/video-watermark-remover"
    corpo = {"video": carica(vin)}
    if "--prompt" in a: corpo["prompt"] = a[a.index("--prompt") + 1]
    print("caricato:", corpo["video"], flush=True)
    r = requests.post(f"{API}/{modello}", headers={**H, "Content-Type": "application/json"}, json=corpo, timeout=120); r.raise_for_status()
    pid = r.json()["data"]["id"]; print("predizione", pid, flush=True)
    t0 = time.time()
    while True:
        time.sleep(10)
        d = requests.get(f"{API}/predictions/{pid}/result", headers=H, timeout=60).json()["data"]
        if d["status"] == "completed": break
        if d["status"] == "failed": raise SystemExit("WaveSpeed: fallito " + json.dumps(d)[:500])
        print(f"  {d['status']} {int(time.time()-t0)}s", flush=True)
    url = d["outputs"][0]; print("scarico", url, flush=True)
    with requests.get(url, stream=True, timeout=900) as g:
        g.raise_for_status()
        with open(vout + ".tmp.mp4", "wb") as f:
            for c in g.iter_content(1 << 20): f.write(c)
    # rimette l'audio originale se il risultato non ce l'ha
    ha_audio = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", vout + ".tmp.mp4"], capture_output=True, text=True).stdout.strip()
    if ha_audio: os.replace(vout + ".tmp.mp4", vout)
    else:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", vout + ".tmp.mp4", "-i", vin, "-map", "0:v", "-map", "1:a?", "-c", "copy", "-shortest", vout], check=True); os.remove(vout + ".tmp.mp4")
    print("ok", vout)


if __name__ == "__main__":
    main()
