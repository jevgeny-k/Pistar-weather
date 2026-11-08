import copy
import datetime as dt
import json
from pathlib import Path
import unittest
from runtime import build_plans,UTC

ROOT=Path(__file__).resolve().parents[2]

class RuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog=json.loads((ROOT/'outputs/pi-only-preparation/catalog.json').read_text(encoding='utf-8'))
        cls.data={p.stem:json.loads(p.read_text(encoding='utf-8'))['data'] for p in (ROOT/'work/bulletin').glob('*.json')}
        cls.now=dt.datetime.fromisoformat(cls.data['weather']['current']['time']).replace(tzinfo=__import__('zoneinfo').ZoneInfo('Europe/Riga')).astimezone(UTC)+dt.timedelta(minutes=3)

    def test_stale_weather_rejected(self):
        with self.assertRaisesRegex(ValueError,'stale'):build_plans(self.data,self.now+dt.timedelta(days=1),self.catalog)

    def test_future_storm_not_current(self):
        data=copy.deepcopy(self.data)
        data['scales']={'0':{'DateStamp':self.now.date().isoformat(),'TimeStamp':self.now.strftime('%H:%M:%S'),'G':{'Scale':'0'},'R':{'Scale':'0'}}}
        data['kp_forecast']=[{'time_tag':(self.now+dt.timedelta(hours=3)).isoformat(),'kp':'7','noaa_scale':'G3'}]
        plans=build_plans(data,self.now,self.catalog)
        self.assertIn('geomagnetic_current_0',plans[-1]);self.assertNotIn('geomagnetic_current_3',plans[-1])
        self.assertIn('geomagnetic_forecast_3',plans[-1]);self.assertIn('forecast_not_observation',plans[-1])

    def test_missing_space_data_announced(self):
        plans=build_plans({'weather':self.data['weather']},self.now,self.catalog)
        for key in ['missing_scales','missing_kp_forecast','missing_aurora']:self.assertIn(key,plans[-1])

    def test_current_storm_not_denied_by_forecast(self):
        data=copy.deepcopy(self.data)
        data['scales']={'0':{'DateStamp':self.now.date().isoformat(),'TimeStamp':self.now.strftime('%H:%M:%S'),'G':{'Scale':'1'},'R':{'Scale':'0'}}}
        data['kp_forecast']=[{'time_tag':(self.now+dt.timedelta(hours=3)).isoformat(),'kp':'5','noaa_scale':'G1'}]
        space=build_plans(data,self.now,self.catalog)[-1]
        self.assertIn('geomagnetic_current_1',space);self.assertIn('geomagnetic_forecast_1',space)
        self.assertNotIn('forecast_not_observation',space)

    def test_out_of_range_not_clamped(self):
        data=copy.deepcopy(self.data);data['weather']['current']['temperature_2m']=65
        self.assertIn('outside_bank',build_plans(data,self.now,self.catalog)[0])

    def test_incomplete_forecast_rejected(self):
        data=copy.deepcopy(self.data);data['weather']['hourly']['time']=[]
        with self.assertRaisesRegex(ValueError,'Incomplete'):build_plans(data,self.now,self.catalog)

    def test_future_weather_rejected(self):
        with self.assertRaisesRegex(ValueError,'future'):build_plans(self.data,self.now-dt.timedelta(hours=2),self.catalog)

    def test_stale_space_data_not_announced_as_current(self):
        data=copy.deepcopy(self.data);old=self.now-dt.timedelta(days=1)
        data['scales']={'0':{'DateStamp':old.date().isoformat(),'TimeStamp':old.strftime('%H:%M:%S'),'G':{'Scale':'5'},'R':{'Scale':'5'}}}
        data['aurora']={'Observation Time':old.isoformat(),'Forecast Time':old.isoformat(),'coordinates':[[24,57,100]]}
        space=build_plans(data,self.now,self.catalog)[-1]
        self.assertIn('missing_scales',space);self.assertIn('missing_aurora',space)
        self.assertNotIn('geomagnetic_current_5',space);self.assertNotIn('radio_blackout_5',space)

if __name__=='__main__':unittest.main()
