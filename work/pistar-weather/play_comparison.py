"""Encode and play the three prepared Silero clips, using the existing relay."""
import json
import subprocess
import sys
import time
from array import array
from pathlib import Path
sys.path.insert(0,'/opt/pistar-weather')
from weather import BASE,STATE,build_call,request

voices=['01-baya','02-kseniya','03-xenia']
for voice in voices:
    wav=STATE/(voice+'.wav')
    if not wav.is_file(): raise RuntimeError('Missing comparison clip '+voice)

# Prepare and validate every voice before transmitting the first one.
for voice in voices:
    raw=STATE/(voice+'.raw'); ambe=STATE/(voice+'.ambe72')
    subprocess.run(['sox',str(STATE/(voice+'.wav')),'-t','raw','-r','8000','-e',
        'signed-integer','-b','16','-c','1','-L',str(raw),
        'gain','-6','highpass','100','lowpass','3400','gain','-n','-3','pad','0.5','0.5'],check=True)
    subprocess.run([str(BASE/'encode'),str(raw),str(ambe)],check=True)
    decoded=STATE/(voice+'-decoded.raw')
    subprocess.run([str(BASE/'encode'),'-d',str(ambe),str(decoded)],check=True)
    samples=array('h'); samples.frombytes(decoded.read_bytes())
    if not samples or not 1000<max(abs(x) for x in samples)<32767:
        raise RuntimeError('Audio level verification failed: '+voice)
    (STATE/(voice+'.dmr55')).write_bytes(build_call(ambe.read_bytes()))
    print('Prepared',voice,'seconds',round(len(samples)/8000,2),flush=True)

for i,voice in enumerate(voices):
    if i: time.sleep(7)
    print('Transmitting',voice,flush=True)
    result=request({'op':'play','file':str(STATE/(voice+'.dmr55'))})
    print(json.dumps(result),flush=True)
    if not result.get('ok'): raise RuntimeError('Transmission stopped: '+voice)
print('All three local private comparison calls completed.',flush=True)
