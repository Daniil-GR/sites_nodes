"""Inspect current OSM access tags of graph ways. Does not change geometry."""
import json,urllib.request,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
edges=[]
for p in (root/'data/routes').glob('*.leg*.edges.json'):edges+=json.loads(p.read_text())['edges']
ids=sorted(set(e['way_id'] for e in edges if e['way_id']));out={}
path=root/'data/route-way-sources.json'
if path.exists():out={k:v for k,v in json.loads(path.read_text())['ways'].items() if k in set(map(str,ids))}
for i in range(0,len(ids),50):
 batch=[n for n in ids[i:i+50] if str(n) not in out]
 if not batch:continue
 u='https://api.openstreetmap.org/api/0.6/ways.json?ways='+','.join(map(str,batch))
 r=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'CityGuideTemplate-data-review/1.0'}),timeout=30))
 out.update({str(e['id']):{'version':e['version'],'visible':e.get('visible',True),'timestamp':e['timestamp'],'tags':e.get('tags',{}),'nodes':e.get('nodes',[])} for e in r['elements']})
 path.write_text(json.dumps({'source':'https://api.openstreetmap.org/api/0.6/ways.json','retrievedAt':'2026-11-11','license':'ODbL-1.0','ways':out},indent=2)+'\n');time.sleep(1.1)
path.write_text(json.dumps({'source':'https://api.openstreetmap.org/api/0.6/ways.json','retrievedAt':'2026-11-11','license':'ODbL-1.0','ways':out},indent=2)+'\n')
print('Ways',len(out))
for id,v in out.items():
 t=v['tags']
 if not v['visible'] or t.get('foot') in ['no','private'] or t.get('access') in ['no','private'] or t.get('highway') in ['construction','proposed','motorway'] or 'construction' in t:print('REVIEW',id,t,v['visible'])
print('Roads',[(id,v['tags']) for id,v in out.items() if v['tags'].get('highway') not in ['footway','path','steps','pedestrian','cycleway'] and v['visible']])
