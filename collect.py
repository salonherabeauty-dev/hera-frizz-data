#!/usr/bin/env python3
"""Hera - Frizz Hourly collector (GitHub Actions). Fetches NEA RH+temp,
computes the Frizz index, appends one row to data/frizz_hourly.csv.
Index = round(clamp((RH-45)/55*100, 0, 100)). Data: NEA / data.gov.sg (open licence)."""
import json, csv, os, urllib.request, datetime

RH_URL='https://api.data.gov.sg/v1/environment/relative-humidity'
TEMP_URL='https://api.data.gov.sg/v1/environment/air-temperature'
CSV_PATH='data/frizz_hourly.csv'

def get(url, test_env):
    f=os.environ.get(test_env)                       # test hook: local file instead of network
    if f and os.path.exists(f):
        with open(f) as fh: return json.load(fh)
    req=urllib.request.Request(url, headers={'User-Agent':'HeraFrizzHourly/1.0'})
    with urllib.request.urlopen(req, timeout=20) as r: return json.load(r)

def avg(vals):
    v=[x for x in vals if isinstance(x,(int,float))]
    return sum(v)/len(v) if v else None
def frizz(rh): return int(round(max(0.0, min(100.0, (rh-45)/55*100))))
def tier(v): return 'Extreme' if v>=90 else 'High' if v>=75 else 'Elevated' if v>=50 else 'Manageable' if v>=25 else 'Calm'

rh=get(RH_URL,'FRIZZ_RH_FILE')
item=rh['items'][0]
by={r['station_id']:r['value'] for r in item['readings']}
arh=avg(list(by.values()))
if arh is None: raise SystemExit('no RH data')
reading_time=item.get('timestamp')

atemp=None
try:
    t=get(TEMP_URL,'FRIZZ_TEMP_FILE'); atemp=avg([r['value'] for r in t['items'][0]['readings']])
except Exception: pass

idx=frizz(arh); tr=tier(idx)
recorded=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8))).isoformat(timespec='seconds')

os.makedirs('data', exist_ok=True)
new=not os.path.exists(CSV_PATH)
if not new:
    with open(CSV_PATH) as f: rows=f.read().strip().splitlines()
    if rows and reading_time and reading_time in rows[-1]:
        print('duplicate reading, skipped'); raise SystemExit(0)
with open(CSV_PATH,'a',newline='') as f:
    w=csv.writer(f)
    if new: w.writerow(['recorded_at','reading_time_sgt','avg_rh','avg_temp_c','frizz_index','tier','stations_rh_json','source'])
    w.writerow([recorded,reading_time,round(arh,2),round(atemp,2) if atemp is not None else '',idx,tr,json.dumps(by),'NEA'])
print(f'logged {reading_time}  RH {arh:.1f}%  ->  Frizz {idx} ({tr})')
