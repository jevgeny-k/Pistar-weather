"""Wait for the local relay and master after startup, without transmitting."""
import time

def wait_for_ready(request,timeout=90,sleep=time.sleep,clock=time.monotonic):
    deadline=clock()+timeout
    while True:
        try:
            status=request({'op':'status'},timeout=3)
            if status.get('connected') and status.get('host'):return
        except (OSError,ValueError):pass
        remaining=deadline-clock()
        if remaining<=0:raise RuntimeError('Master not ready after startup wait')
        sleep(min(2,remaining))
