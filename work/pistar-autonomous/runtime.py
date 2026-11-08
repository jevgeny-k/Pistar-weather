"""Riga phrase-bank bulletin. Python standard library; no laptop or neural TTS."""
import argparse
import concurrent.futures
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import time
import urllib.parse
import urllib.request
import wave
from zoneinfo import ZoneInfo
from assemble import assemble
from retry_http import get_json
from site_settings import load_site

SITE=load_site()
TZ=ZoneInfo(SITE.get('timezone', 'Europe/Riga'))
UTC=dt.timezone.utc
class WeatherUnavailable(ValueError):pass
PARAMS=dict(latitude='56.95',longitude='24.10',timezone='Europe/Riga',wind_speed_unit='ms',forecast_days='2',
 current='temperature_2m,relative_humidity_2m,apparent_temperature,is_day,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m',
 hourly='temperature_2m,precipitation_probability,weather_code,visibility',
 daily='temperature_2m_max,temperature_2m_min,sunrise,sunset')
PARAMS.update({key: SITE[key] for key in ('latitude', 'longitude', 'timezone') if SITE.get(key) is not None})
URLS={'weather':'https://api.open-meteo.com/v1/forecast?'+urllib.parse.urlencode(PARAMS),
 'kp_observed':'https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json',
 'kp_forecast':'https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json',
 'aurora':'https://services.swpc.noaa.gov/json/ovation_aurora_latest.json',
 'scales':'https://services.swpc.noaa.gov/products/noaa-scales.json'}

def utc(s):
    value=dt.datetime.fromisoformat(str(s).replace('Z','+00:00'))
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)

def finite(value):
    n=float(value)
    if not math.isfinite(n):raise ValueError('Non-finite measurement')
    return n

def nearest(n):return int(math.floor(finite(n)+.5))

def rows(data):
    if not data:return []
    if isinstance(data[0],dict):return [{k.lower():v for k,v in row.items()} for row in data]
    return [dict(zip([str(k).lower() for k in data[0]],row)) for row in data[1:]]

def build_plans(data,now,catalog):
    entries=catalog['entries']
    def key(prefix,value):
        result=prefix+'_'+str(nearest(value))
        return result if result in entries else 'outside_bank'
    def temp(prefix,value):
        n=finite(value);half=int(math.floor(abs(n)*2+.5))
        result=prefix+'_'+('m' if n<0 and half else 'p')+str(half).zfill(3)
        return result if result in entries else 'outside_bank'
    local=now.astimezone(TZ)
    w=data.get('weather')
    if not w:raise WeatherUnavailable('Fresh weather unavailable')
    c=w['current'];observed=dt.datetime.fromisoformat(c['time']).replace(tzinfo=TZ)
    if not -300<=(local-observed).total_seconds()<=5400:raise WeatherUnavailable('Weather data stale or from future')
    current=['riga_intro','hour_'+str(local.hour),'minute_'+str(local.minute),
             'condition_'+str(int(c['weather_code'])) if 'condition_'+str(int(c['weather_code'])) in entries else 'missing_condition',
             temp('temperature',c['temperature_2m']),temp('feels',c['apparent_temperature']),
             'wind_direction_'+str(int((finite(c['wind_direction_10m'])+22.5)//45)%8),
             key('wind_speed',c['wind_speed_10m']),key('wind_gust',c['wind_gusts_10m']),
             key('humidity',c['relative_humidity_2m']),key('pressure',c['pressure_msl'])]
    h=w['hourly'];idx=[i for i,t in enumerate(h['time']) if local<dt.datetime.fromisoformat(t).replace(tzinfo=TZ)<=local+dt.timedelta(hours=6)]
    if len(idx)<5:raise WeatherUnavailable('Incomplete six-hour forecast')
    codes={int(h['weather_code'][i]) for i in idx}
    forecast=['forecast_intro'];phenomena=[]
    if codes&{95,96,99}:phenomena.append('phenomenon_thunder')
    for group,name in [({56,57,66,67},'freezing'),({71,73,75,77,85,86},'snow'),({61,63,65,80,81,82},'rain'),({51,53,55},'drizzle')]:
        if codes&group:phenomena.append('phenomenon_'+name)
    if codes&{45,48} or any(v is not None and finite(v)<1000 for v in [h['visibility'][i] for i in idx]):phenomena.append('phenomenon_fog')
    forecast+=phenomena or ['phenomenon_none']
    probs=[finite(h['precipitation_probability'][i]) for i in idx if h['precipitation_probability'][i] is not None]
    if probs:forecast.append(key('precip_probability',max(probs)))
    temps=[finite(h['temperature_2m'][i]) for i in idx]
    forecast += [temp('minimum',min(temps)),temp('maximum',max(temps))]
    d=w['daily'];tomorrow=(local.date()+dt.timedelta(days=1)).isoformat()
    if tomorrow not in d['time']:raise WeatherUnavailable('Tomorrow forecast unavailable')
    j=d['time'].index(tomorrow);sun=dt.datetime.fromisoformat(d['sunrise'][j])
    tomorrow_plan=['tomorrow_intro',temp('minimum',d['temperature_2m_min'][j]),temp('maximum',d['temperature_2m_max'][j]),'sunrise_hour_'+str(sun.hour),'minute_'+str(sun.minute)]
    space=['space_intro'];scales=data.get('scales',{}).get('0',{})
    try:
        fresh=-300<=(now-utc(scales['DateStamp']+'T'+scales['TimeStamp'])).total_seconds()<=10800
        g=int(scales['G']['Scale']);r=int(scales['R']['Scale'])
        if not fresh or not 0<=g<=5 or not 0<=r<=5:raise ValueError('Invalid scales')
        space.append('geomagnetic_current_'+str(g))
    except (KeyError,ValueError,TypeError):space.append('missing_scales');r=0
    observed=[]
    for row in rows(data.get('kp_observed')):
        try:
            stamp=utc(row['time_tag']);kp=finite(row['kp'])
            # Observation table timestamps are the start of three-hour bins.
            if dt.timedelta(hours=3)<=now-stamp<=dt.timedelta(hours=9) and 0<=kp<=9:observed.append((stamp,kp))
        except (KeyError,ValueError,TypeError):pass
    if observed:space.append(key('kp',max(observed)[1]))
    future=[]
    for row in rows(data.get('kp_forecast')):
        try:
            stamp=utc(row['time_tag']);kp=finite(row['kp'])
            g=int(str(row.get('noaa_scale') or 'G0').replace('G',''))
            if now<stamp<=now+dt.timedelta(hours=12) and 0<=kp<=9 and 0<=g<=5:future.append(g)
        except (KeyError,ValueError,TypeError):pass
    if future:
        g=max(future);space.append('geomagnetic_forecast_'+str(g))
        # This clarification is appropriate only when the observed state is G0.
        # During a real storm it could otherwise sound like a denial of it.
        if g and 'geomagnetic_current_0' in space:space.append('forecast_not_observation')
    else:space.append('missing_kp_forecast')
    a=data.get('aurora')
    try:
        if not a or not -300<=(now-utc(a['Observation Time'])).total_seconds()<=10800 or not -1800<=(utc(a['Forecast Time'])-now).total_seconds()<=7200:raise ValueError('Stale aurora')
        point=min(a['coordinates'],key=lambda p:(p[0]-24.10)**2+(p[1]-56.95)**2)
        if not 0<=finite(point[2])<=100:raise ValueError('Invalid aurora')
        space += ['aurora_low' if point[2]<10 else 'aurora_active','aurora_horizon']
        if finite(c['cloud_cover'])>=80:space.append('aurora_clouds')
        if c['is_day']:space.append('aurora_daylight')
    except (KeyError,ValueError,TypeError):space.append('missing_aurora')
    if r:space.append('radio_blackout_'+str(r))
    plans=[current,forecast,tomorrow_plan,space]
    for ids in plans:
        if any(i not in entries for i in ids):raise ValueError('Unsupported phrase')
    return plans

def fetch(item):
    key,url=item
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Pi-Star weather/2.0'})
        data=get_json(req,label=key)
        return key,data
    except Exception as exc:print('Unavailable:',key,str(exc),flush=True);return key,None

def prepare(base,out):
    base=Path(base);out=Path(out);out.mkdir(parents=True,exist_ok=True)
    catalog=json.loads((base/'catalog.json').read_text(encoding='utf-8'))
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:data={k:v for k,v in pool.map(fetch,URLS.items()) if v is not None}
    now=dt.datetime.now(UTC);plans=build_plans(data,now,catalog)
    (out/'sources.json').write_text(json.dumps(dict(retrieved_utc=now.isoformat(),data=data)),encoding='utf-8')
    # Split long sections only at phrase boundaries; every call stays below 40 s.
    bank=json.loads((base/'bank-manifest.json').read_text(encoding='utf-8'));chunks=[]
    for ids in plans:
        chunk=[];duration=0
        for key in ids:
            seconds=bank['generated'][key]['seconds']+catalog['entries'][key]['pause_ms']/1000
            if seconds>39:raise ValueError('Single phrase too long')
            if chunk and duration+seconds>39:chunks.append(chunk);chunk=[];duration=0
            chunk.append(key);duration+=seconds
        if chunk:chunks.append(chunk)
    clips=[]
    for i,ids in enumerate(chunks,1):
        name='part-'+str(i);plan=out/(name+'.json');wav=out/(name+'.wav')
        plan.write_text(json.dumps(dict(generated_utc=now.isoformat(),ids=ids)),encoding='utf-8')
        seconds=assemble(base,plan,wav)
        clips.append(dict(file=wav.name,sha256=hashlib.sha256(wav.read_bytes()).hexdigest(),seconds=seconds))
    (out/'bulletin.txt').write_text('\n\n'.join(' '.join(catalog['entries'][key]['text'] for key in ids) for ids in chunks),encoding='utf-8')
    (out/'manifest.json').write_text(json.dumps(dict(generated_utc=now.isoformat(),clips=clips),indent=2),encoding='utf-8')
    print('PREPARED',len(clips),'parts',flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('bank');parser.add_argument('output')
    args=parser.parse_args();prepare(args.bank,args.output)
