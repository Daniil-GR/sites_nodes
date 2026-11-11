"""Explicit one-time preparation: Valhalla pedestrian -> local GeoJSON.
No replacement geometry is generated when the provider fails.
Raw responses and exact requests are retained for independent review.
"""
import json,time,urllib.request,urllib.parse,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://valhalla1.openstreetmap.de/route'
def decode_shape(shape):
 if isinstance(shape,dict):return shape
 # Valhalla's default is encoded polyline with six decimal places.
 coords=[];index=0;lat=lon=0
 while index<len(shape):
  values=[]
  for _ in range(2):
   value=shift=0
   while True:
    byte=ord(shape[index])-63;index+=1;value|=(byte&31)<<shift;shift+=5
    if byte<32:break
   values.append(~(value>>1) if value&1 else value>>1)
  lat+=values[0];lon+=values[1];coords.append([lon/1e6,lat/1e6])
 return {'type':'LineString','coordinates':coords}
for r in json.loads((ROOT/'data/routing-input.json').read_text()):
 request={'locations':[{'lat':p['lat'],'lon':p['lon'],'type':'break','radius':30} for p in r['locations']],'costing':'pedestrian','costing_options':{'pedestrian':{'walking_speed':4.8,'use_ferry':0,'walkway_factor':0.1,'sidewalk_factor':0.2}},'units':'kilometers','shape_format':'geojson','language':'en-US'}
 rawfile=ROOT/'data/routes'/f"{r['id']}.source.json"
 if rawfile.exists():
  record=json.loads(rawfile.read_text())
  if record['request']!=request:raise RuntimeError('Changed inputs: remove obsolete source file explicitly before regeneration')
  result=record['response']
 else:
  req=urllib.request.Request(SOURCE+'?json='+urllib.parse.quote(json.dumps(request)),headers={'User-Agent':'CityGuideTemplate-route-preparation/1.0','X-Client-Id':'city-guide-template'})
  result=json.load(urllib.request.urlopen(req,timeout=45))
  if result.get('trip',{}).get('status')!=0:raise RuntimeError(result)
  rawfile.write_text(json.dumps({'provider':SOURCE,'retrievedAt':'2026-11-11','request':request,'response':result},indent=2)+'\n')
 trip=result['trip'];features=[]
 for i,leg in enumerate(trip['legs']):
  geometry=decode_shape(leg['shape']);assert geometry['type']=='LineString'
  assert all(m.get('travel_mode')=='pedestrian' for m in leg['maneuvers'])
  assert not leg['summary'].get('has_ferry')
  features.append({'type':'Feature','properties':{'from':r['stops'][i],'to':r['stops'][i+1],'distanceKm':leg['summary']['length'],'walkingSeconds':leg['summary']['time']},'geometry':geometry})
 props={'id':r['id'],'profile':'pedestrian','stops':r['stops'],'distanceKm':trip['summary']['length'],'walkingMinutes':math.ceil(trip['summary']['time']/60),'visitMinutes':r['visitMinutes'],'source':SOURCE,'retrievedAt':'2026-11-11','license':'ODbL-1.0','attribution':'© OpenStreetMap contributors; routing by Valhalla / FOSSGIS','validation':'Routing graph and maneuvers reviewed; not field surveyed. No guarantee of current access.'}
 (ROOT/'data/routes'/f"{r['id']}.geojson").write_text(json.dumps({'type':'FeatureCollection','properties':props,'features':features},separators=(',',':'))+'\n')
 print(r['id'],props['distanceKm'],props['walkingMinutes'],[(m.get('street_names',[]),m['instruction']) for l in trip['legs'] for m in l['maneuvers']],flush=True)
 time.sleep(1.1)
