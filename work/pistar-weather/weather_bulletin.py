"""Fresh Riga weather/space-weather bulletin with the selected local Silero voice."""
from pathlib import Path
import concurrent.futures
import datetime as dt
import hashlib
import html
import json
import math
import re
import wave
from array import array
from zoneinfo import ZoneInfo
from silero_compare import ROOT, WORK as VOICE_WORK, MODEL, download
from fetch_bulletin import WORK as DATA_DIR, URLS, fetch

OUT=ROOT/'outputs'/'weather-bulletin'
OUT.mkdir(exist_ok=True)
TZ=ZoneInfo('Europe/Riga')
PROFILE={'engine':'silero','model':'v5_6_ru','speaker':'xenia','rate':1.08,'pitch':1.15}


def form(n,forms):
    n=abs(int(n))
    return forms[2] if 11<=n%100<=14 else forms[0] if n%10==1 else forms[1] if 2<=n%10<=4 else forms[2]


def num(n,female=False):
    n=int(n)
    if not 0<=n<10000:raise ValueError('Number outside bulletin vocabulary')
    ones=['ноль','один','два','три','четыре','пять','шесть','семь','восемь','девять']
    if female:ones[1:3]=['одна','две']
    teens=['десять','одиннадцать','двенадцать','тринадцать','четырнадцать','пятнадцать','шестнадцать','семнадцать','восемнадцать','девятнадцать']
    tens=['','','двадцать','тридцать','сорок','пятьдесят','шестьдесят','семьдесят','восемьдесят','девяносто']
    hundreds=['','сто','двести','триста','четыреста','пятьсот','шестьсот','семьсот','восемьсот','девятьсот']
    if n==0:return ones[0]
    parts=[]
    if n>=1000:
        k,n=divmod(n,1000);parts.extend([num(k,True),form(k,('тысяча','тысячи','тысяч'))])
    if n>=100:parts.append(hundreds[n//100]);n%=100
    if 10<=n<20:parts.append(teens[n-10]);n=0
    elif n>=20:parts.append(tens[n//10]);n%=10
    if n:parts.append(ones[n])
    return ' '.join(parts)


def temp(value):
    value=float(value);sign='минус ' if value<0 else 'плюс ' if value>0 else ''
    v=abs(value)
    if abs(v%1-.5)<.05:return sign+num(int(v))+' с половиной градусов'
    n=int(math.floor(v+.5))
    return sign+num(n)+' '+form(n,('градус','градуса','градусов'))


def num_gen(n):
    n=int(n)
    if n==100:return 'ста'
    if not 0<=n<100:raise ValueError('Genitive number outside bulletin vocabulary')
    ones=['нуля','одного','двух','трёх','четырёх','пяти','шести','семи','восьми','девяти']
    teens=['десяти','одиннадцати','двенадцати','тринадцати','четырнадцати','пятнадцати','шестнадцати','семнадцати','восемнадцати','девятнадцати']
    tens=['','','двадцати','тридцати','сорока','пятидесяти','шестидесяти','семидесяти','восьмидесяти','девяноста']
    if n<10:return ones[n]
    if n<20:return teens[n-10]
    return tens[n//10]+(' '+ones[n%10] if n%10 else '')


def clock(value):
    return num(value.hour)+' '+form(value.hour,('час','часа','часов'))+' '+num(value.minute,True)+' '+form(value.minute,('минута','минуты','минут'))


def utc(value):
    return dt.datetime.fromisoformat(str(value).replace('Z','+00:00')).replace(tzinfo=dt.timezone.utc)


def rows(data):
    if not data:return []
    if isinstance(data[0],dict):return [{k.lower():v for k,v in r.items()} for r in data]
    return [dict(zip([str(k).lower() for k in data[0]],r)) for r in data[1:]]


def kp_periods(data,now):
    result=[]
    for r in rows(data):
        try:
            t=utc(r['time_tag']);kp=float(r['kp'])
            if 0<=kp<=9:result.append((t,kp,r))
        except (ValueError,KeyError,TypeError):pass
    observed=[r for r in result if r[0]<=now and r[2].get('observed','observed')=='observed' and now-r[0]<=dt.timedelta(hours=6)]
    future=[r for r in result if now<r[0]<=now+dt.timedelta(hours=12)]
    return max(observed,key=lambda r:r[0]) if observed else None,future


def build(data,now):
    w=data['weather'];c=w['current'];local=now.astimezone(TZ)
    obs=dt.datetime.fromisoformat(c['time']).replace(tzinfo=TZ)
    if abs((local-obs).total_seconds())>5400:raise ValueError('Weather data are stale')
    if not (-60<float(c['temperature_2m'])<60):raise ValueError('Invalid temperature')
    code=int(c['weather_code'])
    conditions={0:'ясно',1:'преимущественно ясно',2:'переменная облачность',3:'пасмурно',45:'туман',48:'изморозь и туман',
        51:'слабая морось',53:'морось',55:'сильная морось',56:'переохлаждённая морось',57:'переохлаждённая морось',
        61:'небольшой дождь',63:'дождь',65:'сильный дождь',66:'ледяной дождь',67:'ледяной дождь',
        71:'небольшой снег',73:'снег',75:'сильный снег',77:'снежные зёрна',80:'ливень',81:'ливень',82:'сильный ливень',
        85:'снегопад',86:'сильный снегопад',95:'гроза',96:'гроза с градом',99:'гроза с градом'}
    wind=int(math.floor(float(c['wind_speed_10m'])+.5));gust=round(float(c['wind_gusts_10m']))
    direction=['северный','северо-восточный','восточный','юго-восточный','южный','юго-западный','западный','северо-западный'][int((float(c['wind_direction_10m'])+22.5)//45)%8]
    humidity=round(c['relative_humidity_2m']);pressure=round(c['pressure_msl'])
    current=(f'Погода в Риге. Сейчас {clock(local)}. {conditions.get(code,"Облачность переменная").capitalize()}. '
        f'Температура {temp(c["temperature_2m"])}. Ощущается как {temp(c["apparent_temperature"])}. '
        f'Ветер {direction}, {num(wind)} {form(wind,("метр","метра","метров"))} в секунду, порывы до {num_gen(gust)} {"метра" if gust==1 else "метров"} в секунду. '
        f'Влажность {num(humidity)} {form(humidity,("процент","процента","процентов"))}. '
        f'Давление на уровне моря {num(pressure)} {form(pressure,("гектопаскаль","гектопаскаля","гектопаскалей"))}.')
    h=w['hourly'];indices=[i for i,t in enumerate(h['time']) if local<dt.datetime.fromisoformat(t).replace(tzinfo=TZ)<=local+dt.timedelta(hours=6)]
    if not indices:raise ValueError('No current hourly forecast')
    probs=[h['precipitation_probability'][i] for i in indices if h['precipitation_probability'][i] is not None]
    maxprob=round(max(probs)) if probs else None
    codes={int(h['weather_code'][i]) for i in indices}
    phenomena=[]
    if codes&{95,96,99}:phenomena.append('возможна гроза')
    if codes&{66,67,56,57}:phenomena.append('возможны переохлаждённые осадки')
    elif codes&{71,73,75,77,85,86}:phenomena.append('возможен снег')
    elif codes&{61,63,65,80,81,82}:phenomena.append('возможен дождь')
    elif codes&{51,53,55}:phenomena.append('возможна морось')
    if codes&{45,48} or min(h['visibility'][i] for i in indices)<1000:phenomena.append('возможно ухудшение видимости из-за тумана')
    if not phenomena:phenomena.append('выраженных осадков и тумана модель не показывает')
    forecast='Ближайшие шесть часов: '+', '.join(phenomena)+'. '
    if maxprob is not None:forecast+=f'Почасовая вероятность осадков достигает {num_gen(maxprob)} {"процента" if maxprob%10==1 and maxprob%100!=11 else "процентов"}. '
    low=min(h['temperature_2m'][i] for i in indices);high=max(h['temperature_2m'][i] for i in indices)
    forecast+=f'Минимальная температура {temp(low)}, максимальная {temp(high)}. '
    d=w['daily'];tomorrow=(local.date()+dt.timedelta(days=1)).isoformat()
    if tomorrow in d['time']:
        j=d['time'].index(tomorrow)
        forecast+=f'Завтра минимум {temp(d["temperature_2m_min"][j])}, максимум {temp(d["temperature_2m_max"][j])}. '
        sun=dt.datetime.fromisoformat(d['sunrise'][j])
        forecast+=f'Восход солнца завтра в {clock(sun)}.'
    space='Космическая погода. '
    s=data.get('scales');s0=s.get('0') if s else None
    scales_fresh=s0 and str(s0.get('G',{}).get('Scale','')) in {'0','1','2','3','4','5'} and abs((now-utc(s0['DateStamp']+'T'+s0['TimeStamp'])).total_seconds())<=10800
    if scales_fresh:
        g=int(s0['G']['Scale'] or 0)
        space+=('По текущей оценке НОАА геомагнитной бури нет. ' if g==0 else f'НОАА отмечает геомагнитную бурю уровня джи {num(g)}. ')
    else:space+='Свежая текущая оценка геомагнитной бури недоступна. '
    observed,_=kp_periods(data.get('kp_observed'),now)
    if observed:space+=f'Последний завершённый трёхчасовой индекс ка пэ около {num_gen(round(observed[1]))}. '
    _,future=kp_periods(data.get('kp_forecast'),now)
    if future:
        maxkp=max(x[1] for x in future)
        gs=[int(str(x[2].get('noaa_scale') or 'G0').replace('G','')) for x in future]
        if max(gs)>0:space+=f'В прогнозе на ближайшие двенадцать часов возможна буря уровня джи {num(max(gs))}. Это прогноз, а не наблюдаемая сейчас буря. '
        else:space+='В ближайшие двенадцать часов прогноз не показывает уровня магнитной бури. '
    else:space+='Свежий прогноз геомагнитной активности недоступен. '
    a=data.get('aurora')
    aurora_fresh=a and abs((now-utc(a['Observation Time'])).total_seconds())<=10800 and -dt.timedelta(minutes=30)<=utc(a['Forecast Time'])-now<=dt.timedelta(hours=2)
    if aurora_fresh:
        point=min(a['coordinates'],key=lambda p:(p[0]-24.10)**2+(p[1]-56.95)**2)
        space+=('Краткосрочная модель не показывает яркого сияния прямо над Ригой. ' if point[2]<10 else 'В краткосрочной модели есть авроральная активность вблизи Риги. ')
        space+='Сияние на северном горизонте может быть видно и вдали от центра аврорального овала. '
        if c['cloud_cover']>=80:space+='Однако нынешняя сплошная облачность сильно мешает наблюдению. '
    else:space+='Свежий краткосрочный прогноз северного сияния недоступен. '
    if scales_fresh and int(s0['R']['Scale'] or 0)>0:
        space+=f'Также НОАА отмечает нарушение коротковолновой связи уровня эр {num(int(s0["R"]["Scale"]))} на дневной стороне Земли.'
    return [('01-current',current),('02-forecast',forecast),('03-space',space)]


def main():
    unavailable=set()
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
        for key,result in pool.map(fetch,URLS.items()):
            if 'error' in result:unavailable.add(key);print('Unavailable:',key,result['error'],flush=True)
    data={key:json.loads((DATA_DIR/(key+'.json')).read_text(encoding='utf-8'))['data'] for key in URLS if key not in unavailable}
    if 'weather' not in data:raise RuntimeError('Fresh weather unavailable; refusing to announce old data')
    now=dt.datetime.now(dt.timezone.utc)
    texts=build(data,now)
    (VOICE_WORK/'selected_voice.json').write_text(json.dumps(PROFILE,indent=2),encoding='utf-8')
    print(json.dumps(dict(profile=PROFILE,generated=now.isoformat()),ensure_ascii=False),flush=True)
    (OUT/'bulletin.txt').write_text('\n\n'.join(t for _,t in texts),encoding='utf-8')
    for name,text in texts:print(name,text,flush=True)
    download()
    import torch
    torch.set_num_threads(2)
    model=torch.package.PackageImporter(str(MODEL)).load_pickle('tts_models','model');model.to(torch.device('cpu'))
    package=model.packages[model.speaker_to_package[PROFILE['speaker']]]
    package.rate2value['fast']=PROFILE['rate'];package.pitch2value['high']=PROFILE['pitch']
    clips=[]
    for name,text in texts:
        # Short sentence pauses; use the same mild lively profile as the approved trial.
        ssml='<speak><prosody rate="fast" pitch="high">'+html.escape(text).replace('. ','.<break time="180ms"/>')+'</prosody></speak>'
        audio=model.apply_tts(ssml_text=ssml,speaker=PROFILE['speaker'],sample_rate=48000,put_accent=True,put_yo=True).detach().cpu().float()
        if not torch.isfinite(audio).all() or float(audio.abs().max())<.001:raise ValueError('Invalid audio')
        audio*=.85/float(audio.abs().max())
        pcm=array('h',(audio*32767).round().clamp(-32767,32767).to(torch.int16).tolist())
        seconds=len(pcm)/48000
        if seconds>53:raise ValueError('Bulletin section too long; split before transmission')
        p=OUT/(name+'.wav')
        with wave.open(str(p),'wb') as wf:
            wf.setnchannels(1);wf.setsampwidth(2);wf.setframerate(48000);wf.writeframes(pcm.tobytes())
        clips.append(dict(name=name,file=p.name,seconds=seconds,sha256=hashlib.sha256(p.read_bytes()).hexdigest(),text=text))
        print('Prepared',name,round(seconds,1),'seconds',flush=True)
    manifest=dict(generated_utc=now.isoformat(),profile=PROFILE,sources=URLS,clips=clips)
    (OUT/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    print('BULLETIN_READY',flush=True)


if __name__=='__main__':main()
