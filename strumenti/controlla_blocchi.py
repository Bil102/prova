"""Controllo Whisper blocco per blocco: rigenera (fino a 6 volte) i blocchi che saltano o inventano parole.
uso: python3 strumenti/controlla_blocchi.py progetti/<nome>"""
import sys, re, difflib, subprocess, glob, json
from faster_whisper import WhisperModel
P=sys.argv[1]; m=WhisperModel("large-v3",compute_type="int8")
def n(x):
    x=x.lower().replace("rivàiv dram","revivedrum").replace("revive drum","revivedrum")
    for a,b in (("à","a"),("ì","i"),("è","e"),("é","e"),("ò","o"),("ù","u")): x=x.replace(a,b)
    return re.sub(r"[^a-z ]"," ",x).split()
def bad(f):
    t=" ".join(s.text for s in m.transcribe(f,language="it")[0]); a=n(json.load(open(f[:-4]+".json"))["testo"]); b=n(t)
    return [(op," ".join(a[i1:i2])," ".join(b[j1:j2])) for op,i1,i2,j1,j2 in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes() if op!="equal" and (i2-i1)+(j2-j1)>2]
for f in sorted(glob.glob(P+"/voce/*_narratore.mp3")):
    k=int(f.split("/")[-1][:2])
    for tent in range(6):
        e=bad(f); print(k,tent,e,flush=True)
        if not e: break
        subprocess.run(["python3","localizza.py","voce",P,"--solo",str(k)],capture_output=True)
