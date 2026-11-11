"""Offline checks of provenance, walking profile, geometry and stop order."""
import json,math
from pathlib import Path
root=Path(__file__).resolve().parents[1]
inputs=json.loads((root/'data/routing-input.json').read_text())
def distance(a,b):
 lat1,lat2=map(math.radians,[a[1],b[1]]);dl=math.radians(b[0]-a[0]);dp=lat2-lat1
 return 6371008.8*2*math.asin(min(1,math.sqrt(math.sin(dp/2)**2+math.cos(lat1)*math.cos(lat2)*math.sin(dl/2)**2)))
results=[]
for r in inputs:
 data=json.loads((root/'data/routes'/f"{r['id']}.geojson").read_text());source=json.loads((root/'data/routes'/f"{r['id']}.source.json").read_text());trip=source['response']['trip'];p=data['properties']
 assert source['request']['costing']=='pedestrian'
 assert p['profile']=='pedestrian' and p['stops']==r['stops']
 assert len(data['features'])==len(r['stops'])-1
 assert p['distanceKm']==trip['summary']['length'] and p['walkingMinutes']==math.ceil(trip['summary']['time']/60)
 assert not trip['summary'].get('has_ferry') and not trip['summary'].get('has_highway') and not trip['summary'].get('has_toll')
 gaps=[];length=0;maxsegment=0
 for i,f in enumerate(data['features']):
  c=f['geometry']['coordinates'];assert f['geometry']['type']=='LineString' and len(c)>2
  assert f['properties']['from']==r['stops'][i] and f['properties']['to']==r['stops'][i+1]
  assert all(m['travel_mode']=='pedestrian' for m in trip['legs'][i]['maneuvers'])
  assert all(-74.05<x<-73.90 and 40.68<y<40.81 for x,y in c)
  for loc,point in [(r['locations'][i],c[0]),(r['locations'][i+1],c[-1])]:gaps.append(round(distance([loc['lon'],loc['lat']],point),1))
  assert max(gaps)<=45,(r['id'],gaps)
  segments=[distance(a,b) for a,b in zip(c,c[1:])];length+=sum(segments);maxsegment=max(maxsegment,max(segments))
  if i:assert distance(data['features'][i-1]['geometry']['coordinates'][-1],c[0])<0.2
 assert abs(length/1000-p['distanceKm'])<0.06,(r['id'],length,p['distanceKm'])
 results.append({'route':r['id'],'distanceKm':p['distanceKm'],'walkingMinutes':p['walkingMinutes'],'visitMinutes':p['visitMinutes'],'geometryLengthMeters':round(length),'maxSegmentMeters':round(maxsegment),'endpointOffsetsMeters':gaps,'result':'Пройдено'})
(root/'reference/route-tests.json').write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(results,ensure_ascii=False,indent=2))
