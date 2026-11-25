"""Porta ogni blocco della voce (progetti/<p>/voce/NN_*.mp3) allo stesso volume (-19 LUFS, picco -1.5 dB),
poi ricostruisce voiceover_it.mp3 con `localizza.py voce` (i blocchi invariati non vengono rigenerati).
uso: python3 strumenti/normalizza_blocchi.py progetti/<nome>"""
import sys, glob, subprocess, os, json, re
P = sys.argv[1]
for f in sorted(glob.glob(P + "/voce/[0-9][0-9]_*.mp3")):
    st = subprocess.run(["ffmpeg", "-hide_banner", "-i", f, "-af", "loudnorm=I=-19:TP=-1.5:LRA=7:print_format=json", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(st[st.rindex("{"):st.rindex("}") + 1])
    flt = f"loudnorm=I=-19:TP=-1.5:LRA=7:measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", f, "-af", flt, "-ar", "44100", "-b:a", "192k", f + ".n.mp3"], check=True)
    os.replace(f + ".n.mp3", f); print(os.path.basename(f), "da", m["input_i"], "LUFS")
subprocess.run(["python3", "localizza.py", "voce", P], check=True)
