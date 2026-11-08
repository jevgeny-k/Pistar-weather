from pathlib import Path
import concurrent.futures
import datetime as dt
import json
import urllib.parse
import urllib.request
from site_settings import load_site

ROOT=Path(__file__).resolve().parents[2]
WORK=ROOT/'work'/'bulletin'
WORK.mkdir(exist_ok=True)
params=dict(latitude='56.95',longitude='24.10',timezone='Europe/Riga',wind_speed_unit='ms',forecast_days='2',
    current='temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,cloud_cover,pressure_msl,wind_speed_10m,wind_direction_10m,wind_gusts_10m',
    hourly='temperature_2m,precipitation_probability,precipitation,weather_code,visibility,wind_gusts_10m',
    daily='temperature_2m_max,temperature_2m_min,precipitation_probability_max,sunrise,sunset')
params.update({key: value for key, value in load_site().items() if key in ('latitude', 'longitude', 'timezone') and value is not None})
URLS={
 'weather':'https://api.open-meteo.com/v1/forecast?'+urllib.parse.urlencode(params),
 'kp_observed':'https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json',
 'kp_forecast':'https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json',
 'aurora':'https://services.swpc.noaa.gov/json/ovation_aurora_latest.json',
 'scales':'https://services.swpc.noaa.gov/products/noaa-scales.json',
}

def fetch(item):
    key,url=item
    try:
        req=urllib.request.Request(url,headers={'User-Agent':'Pi-Star weather bulletin/1.0'})
        with urllib.request.urlopen(req,timeout=30) as r:data=json.load(r)
        result=dict(url=url,retrieved_utc=dt.datetime.now(dt.timezone.utc).isoformat(),data=data)
        (WORK/(key+'.json')).write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
        if key=='weather': summary=dict(current=data['current'],daily=data['daily'])
        elif key=='aurora':
            points=data['coordinates']; nearby=min(points,key=lambda p:(p[0]-24.10)**2+(p[1]-56.95)**2)
            north=[p for p in points if 15<=p[0]<=35 and 57<=p[1]<=65]
            summary=dict(observed=data.get('Observation Time'),forecast=data.get('Forecast Time'),
                         nearest_grid_point=nearby,northern_region_max=max(p[2] for p in north))
        elif key.startswith('kp_'):summary=dict(columns=data[0],last_rows=data[-5:])
        else:summary=data
        return key,summary
    except Exception as e:return key,dict(error=str(e))

if __name__=='__main__':
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for key,data in pool.map(fetch,URLS.items()):print(key,json.dumps(data,ensure_ascii=False),flush=True)
