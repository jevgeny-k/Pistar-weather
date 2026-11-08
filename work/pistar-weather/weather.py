#!/opt/pistar-weather/venv/bin/python
"""Fetch current Riga weather, synthesize Russian speech, create a private DMR call.

Default operation prepares audio only. Transmission requires the explicit `now`
argument; no periodic timer is installed.
"""
import argparse
import datetime
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import urllib.request
import urllib.parse
from zoneinfo import ZoneInfo
from bitarray import bitarray
from dmr_utils3 import bptc, golay, qr
from proxy import RADIO_ID, validate_packets
from site_settings import load_site, require_radio_id

BASE = Path('/opt/pistar-weather')
STATE = Path('/run/pistar-weather')
SITE = load_site()
WEATHER_URL = 'https://api.open-meteo.com/v1/forecast?' + urllib.parse.urlencode({
    'latitude': SITE.get('latitude', 56.95), 'longitude': SITE.get('longitude', 24.10),
    'current': 'temperature_2m,weather_code,wind_speed_10m',
    'wind_speed_unit': 'ms', 'timezone': SITE.get('timezone', 'Europe/Riga'),
})


def bits(data):
    result = bitarray(endian='big'); result.frombytes(data); return result


def number_bits(value, length):
    return bitarray(format(value, '0%db' % length), endian='big')


def build_call(ambe72):
    require_radio_id(RADIO_ID)
    if not ambe72 or len(ambe72) % 9: raise ValueError('Invalid AMBE72 file')
    if len(ambe72) > 9*50*55: raise ValueError('Speech longer than 55 seconds')
    # Private, unencrypted, owner source and destination IDs. Slot 1, CC 1.
    lc = b'\x03\x00\x00' + RADIO_ID.to_bytes(3,'big')*2
    embedded = bptc.encode_emblc(lc)
    stream = secrets.token_bytes(4)
    seq = 0
    packets = []

    def packet(payload, flags):
        nonlocal seq
        p = (b'DMRD'+bytes([seq % 256])+RADIO_ID.to_bytes(3,'big')*2+
             RADIO_ID.to_bytes(4,'big')+bytes([0x40 | flags])+stream+
             payload.tobytes()+b'\x00\x00')
        assert len(p) == 55
        packets.append(p); seq += 1

    def lc_payload(terminator=False):
        dt = 2 if terminator else 1
        encoded = bptc.encode_terminator_lc(lc) if terminator else bptc.encode_header_lc(lc)
        slot = number_bits(golay.encode_2087(bytes([(1 << 4) | dt])),20)
        sync = number_bits(0xDFF57D75DF5D,48) # base-station data sync
        return encoded[:98]+slot[:10]+sync+slot[10:]+encoded[98:]

    for _ in range(3): packet(lc_payload(),0x21)
    frames = [ambe72[i:i+9] for i in range(0,len(ambe72),9)]
    silence = bytes.fromhex('b9e881526173002a6b')
    while len(frames) % 18: frames.append(silence)
    for i in range(0,len(frames),3):
        n = (i//3) % 6
        voice = bits(b''.join(frames[i:i+3]))
        if n == 0:
            center = number_bits(0x755FD7DF75F7,48) # base-station audio sync
        else:
            lcss = {1:1,2:3,3:3,4:2,5:0}[n]
            emb = bits(bytes(qr.encode(bytearray([((1 << 3) | lcss) << 1,0]))))
            center = emb[:8]+(embedded[n] if n in embedded else number_bits(0,32))+emb[8:]
        packet(voice[:108]+center+voice[108:],0x10 if n == 0 else n)
    for _ in range(3): packet(lc_payload(True),0x22)
    raw=b''.join(packets); validate_packets(raw); return raw


def inflect(n, forms):
    n=abs(n)
    return forms[2] if 11<=n%100<=14 else forms[0] if n%10==1 else forms[1] if 2<=n%10<=4 else forms[2]


def get_report():
    req=urllib.request.Request(WEATHER_URL,headers={'User-Agent':'Pi-Star local Riga weather/1.0'})
    with urllib.request.urlopen(req,timeout=20) as r: data=json.load(r)
    c=data['current']
    obs=datetime.datetime.fromisoformat(c['time']).replace(tzinfo=ZoneInfo('Europe/Riga'))
    now=datetime.datetime.now(ZoneInfo('Europe/Riga'))
    if abs((now-obs).total_seconds())>5400: raise ValueError('Weather timestamp is stale')
    temp=round(float(c['temperature_2m'])); wind=round(float(c['wind_speed_10m']))
    if not (-50<=temp<=50 and 0<=wind<=80): raise ValueError('Implausible weather data')
    code=int(c['weather_code'])
    if code==0: condition='ясно'
    elif code in (1,2): condition='переменная облачность'
    elif code==3: condition='пасмурно'
    elif code in (45,48): condition='туман'
    elif code in (51,53,55,56,57): condition='морось'
    elif code in (61,63,65,66,67,80,81,82): condition='дождь'
    elif code in (71,73,75,77,85,86): condition='снег'
    elif code in (95,96,99): condition='гроза'
    else: condition=''
    sign='минус' if temp<0 else 'плюс' if temp>0 else ''
    text=(f'Погода в Риге. Сейчас {now.hour} {inflect(now.hour,("час","часа","часов"))} '
          f'{now.minute} {inflect(now.minute,("минута","минуты","минут"))}. '
          f'Температура {sign} {abs(temp)} {inflect(temp,("градус","градуса","градусов"))}. '
          f'{condition}. Ветер {wind} {inflect(wind,("метр","метра","метров"))} в секунду.')
    return text, {'source':WEATHER_URL,'observed':obs.isoformat(),'generated':now.isoformat(),
                  'temperature_c':temp,'wind_ms':wind,'weather_code':code}


def request(data,timeout=200):
    with socket.socket(socket.AF_UNIX,socket.SOCK_STREAM) as s:
        s.settimeout(timeout); s.connect(str(STATE/'control.sock'))
        s.sendall(json.dumps(data).encode()); response=s.recv(4096)
    return json.loads(response)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['prepare','now','status'],default='prepare',nargs='?')
    args=parser.parse_args()
    if args.command=='status': print(json.dumps(request({'op':'status'}))); return
    STATE.mkdir(exist_ok=True)
    text,meta=get_report()
    (STATE/'weather.txt').write_text(text,encoding='utf-8')
    (STATE/'weather.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf-8')
    subprocess.run(['nice','-n','10',str(BASE/'tts/piper/piper'),
                    '--model',str(BASE/'models/ru_RU-irina-medium.onnx'),
                    '--length_scale','1.12','--sentence_silence','0.35',
                    '--output_file',str(STATE/'speech.wav')],
                    input=(text+'\n').encode('utf-8'),check=True,timeout=90,
                    env=dict(os.environ,OMP_NUM_THREADS='2',OPENBLAS_NUM_THREADS='2'))
    subprocess.run(['sox',str(STATE/'speech.wav'),'-t','raw','-r','8000','-e','signed-integer',
                    '-b','16','-c','1','-L',str(STATE/'speech.raw'),
                    'gain','-6','highpass','100','lowpass','3400','gain','-n','-3',
                    'pad','0.5','0.5'],check=True)
    subprocess.run([str(BASE/'encode'),str(STATE/'speech.raw'),str(STATE/'speech.ambe72')],check=True)
    raw=build_call((STATE/'speech.ambe72').read_bytes())
    packetfile=STATE/'weather.dmr55'; packetfile.write_bytes(raw)
    print(text,flush=True)
    print('Prepared %.1f seconds; PRIVATE ID %d / TS1 / CC1; source Open-Meteo' %
          (len(raw)/55*.06,RADIO_ID),flush=True)
    if args.command=='now':
        result=request({'op':'play','file':str(packetfile)})
        print(json.dumps(result),flush=True)
        if not result.get('ok'): sys.exit(1)


if __name__=='__main__': main()
