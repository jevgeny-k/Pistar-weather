"""Small bounded retries for transient data-source failures; no cache fallback."""
import json
import time
import urllib.error
import urllib.request

def get_json(request,label='source',opener=None,sleep=time.sleep):
    opener=opener or urllib.request.urlopen
    delays=(2,5,None)
    for attempt,delay in enumerate(delays,1):
        try:
            with opener(request,timeout=25) as response:return json.load(response)
        except urllib.error.HTTPError as exc:
            if exc.code not in {502,503,504} or delay is None:raise
            reason='HTTP '+str(exc.code)
        except (urllib.error.URLError,TimeoutError):
            if delay is None:raise
            reason='connection error'
        print('Retry',label,'after',reason,'in',delay,'seconds; attempt',attempt+1,'of 3',flush=True)
        sleep(delay)
