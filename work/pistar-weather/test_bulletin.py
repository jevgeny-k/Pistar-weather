import copy
import datetime as dt
import json
import unittest
from weather_bulletin import DATA_DIR,URLS,build,kp_periods


class DataSafety(unittest.TestCase):
    def test_future_index_is_not_present_observation(self):
        now=dt.datetime(2026,11,7,19,tzinfo=dt.timezone.utc)
        data=[dict(time_tag='2026-11-07T18:00:00',kp=2,observed='observed'),
              dict(time_tag='2026-11-07T21:00:00',kp=8,observed='estimated',noaa_scale='G4')]
        current,future=kp_periods(data,now)
        self.assertEqual(current[1],2)
        self.assertEqual([x[1] for x in future],[8])

    def test_stale_weather_prevents_report(self):
        record=json.loads((DATA_DIR/'weather.json').read_text(encoding='utf-8'))
        now=dt.datetime.fromisoformat(record['retrieved_utc'])
        data={'weather':copy.deepcopy(record['data'])}
        data['weather']['current']['time']='2000-01-01T00:00'
        with self.assertRaisesRegex(ValueError,'stale'):build(data,now)

    def test_stale_space_weather_is_announced_as_unavailable(self):
        records={key:json.loads((DATA_DIR/(key+'.json')).read_text(encoding='utf-8')) for key in URLS}
        now=dt.datetime.fromisoformat(records['weather']['retrieved_utc'])
        data={key:copy.deepcopy(value['data']) for key,value in records.items()}
        data['scales']['0']['DateStamp']='2000-01-01'
        data['aurora']['Observation Time']='2000-01-01T00:00:00Z'
        data['aurora']['Forecast Time']='2000-01-01T01:00:00Z'
        space=build(data,now)[2][1]
        self.assertIn('текущая оценка геомагнитной бури недоступна',space)
        self.assertIn('прогноз северного сияния недоступен',space)


if __name__=='__main__':unittest.main()
