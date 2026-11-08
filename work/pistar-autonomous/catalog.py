"""Offline data preparation, separate from the preserved working implementation."""
from pathlib import Path
import datetime as dt
import hashlib
import json
import math
import sys
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'work/pistar-weather'))
from weather_bulletin import num,num_gen,form

OUT=ROOT/'outputs/pi-only-preparation'
PROFILE=dict(engine='silero',model='v5_6_ru',speaker='xenia',rate=1.08,pitch=1.15)
CONDITIONS={0:'Ясно.',1:'Преимущественно ясно.',2:'Переменная облачность.',3:'Пасмурно.',45:'Туман.',48:'Изморозь и туман.',
 51:'Слабая морось.',53:'Морось.',55:'Сильная морось.',56:'Переохлаждённая морось.',57:'Переохлаждённая морось.',
 61:'Небольшой дождь.',63:'Дождь.',65:'Сильный дождь.',66:'Ледяной дождь.',67:'Ледяной дождь.',
 71:'Небольшой снег.',73:'Снег.',75:'Сильный снег.',77:'Снежные зёрна.',80:'Ливень.',81:'Ливень.',82:'Сильный ливень.',
 85:'Снегопад.',86:'Сильный снегопад.',95:'Гроза.',96:'Гроза с градом.',99:'Гроза с градом.'}


def value_key(value):
    # Quantization is explicit: nearest half degree, ties away from zero.
    n=int(math.floor(abs(float(value))*2+.5))*(1 if value>=0 else -1)
    return ('m' if n<0 else 'p')+str(abs(n)).zfill(3)


def temperature(n):
    sign='минус ' if n<0 else 'плюс ' if n>0 else ''
    n=abs(n)
    if n==0:return 'ноль градусов'
    if n==1:return sign+'полградуса'
    if n==3:return sign+'полтора градуса'
    whole=n//2
    if n%2:return sign+num(whole)+' с половиной '+form(whole,('градус','градуса','градусов'))
    return sign+num(whole)+' '+form(whole,('градус','градуса','градусов'))


def make_catalog():
    entries={}
    def add(key,text,group,pause_ms=140):
        if key in entries:raise ValueError('Duplicate phrase '+key)
        entries[key]=dict(id=key,text=text,group=group,pause_ms=pause_ms,
                          wav='bank/'+key+'.wav',text_sha256=hashlib.sha256(text.encode()).hexdigest())
    static={
      'pilot_notice':'Проверка автономного банка фраз.',
      'riga_intro':'Погода в Риге.',
      'forecast_intro':'Ближайшие шесть часов.',
      'tomorrow_intro':'Погода на завтра.',
      'space_intro':'Космическая погода.',
      'phenomenon_thunder':'Возможна гроза.',
      'phenomenon_freezing':'Возможны переохлаждённые осадки.',
      'phenomenon_snow':'Возможен снег.',
      'phenomenon_rain':'Возможен дождь.',
      'phenomenon_drizzle':'Возможна морось.',
      'phenomenon_fog':'Возможно ухудшение видимости из-за тумана.',
      'phenomenon_none':'Выраженных осадков и тумана модель не показывает.',
      'forecast_not_observation':'Это прогноз, а не наблюдаемая сейчас буря.',
      'aurora_low':'Краткосрочная модель не показывает яркого сияния прямо над Ригой.',
      'aurora_active':'В краткосрочной модели есть авроральная активность вблизи Риги.',
      'aurora_horizon':'Сияние на северном горизонте может быть видно и вдали от центра аврорального овала.',
      'aurora_clouds':'Плотная облачность сильно мешает наблюдению.',
      'aurora_daylight':'При дневном свете наблюдать северное сияние нельзя.',
      'missing_weather':'Свежие погодные данные недоступны.',
      'missing_condition':'Характер погоды сейчас не определён.',
      'missing_scales':'Свежая текущая оценка геомагнитной бури недоступна.',
      'missing_kp_forecast':'Свежий прогноз геомагнитной активности недоступен.',
      'missing_aurora':'Свежий краткосрочный прогноз северного сияния недоступен.',
      'outside_bank':'Этот числовой показатель сейчас не удаётся озвучить.',
    }
    for key,text in static.items():add(key,text,'static')
    for code,text in CONDITIONS.items():add('condition_'+str(code),text,'weather-condition')
    for n in range(24):
        add('hour_'+str(n),'Сейчас '+num(n)+' '+form(n,('час','часа','часов'))+',','clock',30)
        add('sunrise_hour_'+str(n),'Восход солнца завтра в '+num(n)+' '+form(n,('час','часа','часов'))+',','clock',30)
    for n in range(60):add('minute_'+str(n),num(n,True)+' '+form(n,('минута','минуты','минут'))+'.','clock')
    for prefix,label,low,high in [
        ('temperature','Температура ',-50,50),('feels','Ощущается как ',-60,60),
        ('minimum','Минимальная температура ',-50,50),('maximum','Максимальная температура ',-50,50)]:
        for half in range(low*2,high*2+1):
            key=('m' if half<0 else 'p')+str(abs(half)).zfill(3)
            add(prefix+'_'+key,label+temperature(half)+'.','temperature')
    dirs=['северный','северо-восточный','восточный','юго-восточный','южный','юго-западный','западный','северо-западный']
    for n,name in enumerate(dirs):add('wind_direction_'+str(n),'Ветер '+name+'.','wind')
    for n in range(71):add('wind_speed_'+str(n),'Скорость ветра '+num(n)+' '+form(n,('метр','метра','метров'))+' в секунду.','wind')
    for n in range(91):add('wind_gust_'+str(n),'Порывы до '+num_gen(n)+' '+('метра' if n%10==1 and n%100!=11 else 'метров')+' в секунду.','wind')
    for n in range(101):
        add('humidity_'+str(n),'Влажность '+num(n)+' '+form(n,('процент','процента','процентов'))+'.','humidity')
        add('precip_probability_'+str(n),'Почасовая вероятность осадков достигает '+num_gen(n)+' '+('процента' if n%10==1 and n%100!=11 else 'процентов')+'.','precipitation')
    for n in range(900,1101):add('pressure_'+str(n),'Давление на уровне моря '+num(n)+' '+form(n,('гектопаскаль','гектопаскаля','гектопаскалей'))+'.','pressure')
    for g in range(6):
        label=['','слабая','умеренная','сильная','очень сильная','экстремальная'][g]
        add('geomagnetic_current_'+str(g),'По текущей оценке НОАА геомагнитной бури нет.' if g==0 else 'НОАА отмечает геомагнитную бурю уровня джи '+num(g)+'.','space-weather')
        add('geomagnetic_forecast_'+str(g),'В ближайшие двенадцать часов прогноз не показывает уровня магнитной бури.' if g==0 else 'В прогнозе на ближайшие двенадцать часов возможна '+label+' буря уровня джи '+num(g)+'.','space-weather')
    for n in range(10):add('kp_'+str(n),'Последний завершённый трёхчасовой индекс ка пэ около '+num_gen(n)+'.','space-weather')
    for n in range(1,6):add('radio_blackout_'+str(n),'НОАА отмечает нарушение коротковолновой связи уровня эр '+num(n)+' на дневной стороне Земли.','space-weather')
    return dict(schema=1,profile=PROFILE,format=dict(sample_rate=8000,channels=1,sample_width=2),
                ranges=dict(temperature_c=[-50,50],apparent_c=[-60,60],temperature_step_c=.5,
                            wind_ms=[0,70],gust_ms=[0,90],humidity_pct=[0,100],pressure_hpa=[900,1100]),
                entries=entries)


def pilot_plan(data,now):
    # First pilot deliberately covers just current weather and the most sensitive
    # joins (hours/minutes); the complete forecast/NOAA planner follows later.
    w=data['current'];local=now.astimezone(ZoneInfo('Europe/Riga'))
    obs=dt.datetime.fromisoformat(w['time']).replace(tzinfo=ZoneInfo('Europe/Riga'))
    if abs((local-obs).total_seconds())>5400:raise ValueError('Pilot weather data are stale')
    def rounded(n):return int(math.floor(float(n)+.5))
    ids=['pilot_notice','riga_intro','hour_'+str(local.hour),'minute_'+str(local.minute),
         'condition_'+str(w['weather_code']),'temperature_'+value_key(w['temperature_2m']),
         'feels_'+value_key(w['apparent_temperature']),
         'wind_direction_'+str(int((w['wind_direction_10m']+22.5)//45)%8),
         'wind_speed_'+str(rounded(w['wind_speed_10m'])),
         'wind_gust_'+str(rounded(w['wind_gusts_10m'])),
         'humidity_'+str(rounded(w['relative_humidity_2m'])),
         'pressure_'+str(rounded(w['pressure_msl']))]
    return dict(generated_utc=now.isoformat(),kind='pilot-current-weather-only',ids=ids)


def main():
    OUT.mkdir(exist_ok=True)
    catalog=make_catalog()
    from fetch_bulletin import fetch,WORK as SOURCE
    name,summary=fetch(('weather',__import__('fetch_bulletin').URLS['weather']))
    if 'error' in summary:raise RuntimeError(summary['error'])
    weather=json.loads((SOURCE/'weather.json').read_text(encoding='utf-8'))['data']
    plan=pilot_plan(weather,dt.datetime.now(dt.timezone.utc))
    missing=[key for key in plan['ids'] if key not in catalog['entries']]
    if missing:raise RuntimeError('Pilot needs phrases outside catalogue: '+str(missing))
    # Include a few critical fallback/space phrases in the seed bank as data preparation.
    seed=list(dict.fromkeys(plan['ids']+['space_intro','geomagnetic_current_0','geomagnetic_forecast_1',
        'forecast_not_observation','aurora_low','aurora_clouds','missing_weather','missing_aurora']))
    catalog['pilot_seed_ids']=seed
    (OUT/'catalog.json').write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'pilot-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'pilot-text.txt').write_text('\n'.join(catalog['entries'][key]['text'] for key in plan['ids']),encoding='utf-8')
    print('CATALOG_ENTRIES',len(catalog['entries']),'PILOT_SEED',len(seed),flush=True)
    print((OUT/'pilot-text.txt').read_text(encoding='utf-8'),flush=True)


if __name__=='__main__':main()
