"""Check polylines against graph edges. Record any fallback map matching explicitly."""
import json,urllib.request,urllib.parse,time
from pathlib import Path
root=Path(__file__).resolve().parents[1]
for source in sorted((root/'data/routes').glob('*.source.json')):
 record=json.loads(source.read_text());out=[]
 for index,leg in enumerate(record['response']['trip']['legs']):
  dest=source.with_name(source.name.replace('.source.json',f'.leg{index+1}.edges.json'))
  if dest.exists():data=json.loads(dest.read_text())
  else:
   req={'encoded_polyline':leg['shape'],'costing':'pedestrian','shape_match':'edge_walk','filters':{'action':'include','attributes':['edge.way_id','edge.names','edge.use','edge.road_class','edge.traversability','edge.bridge','edge.tunnel','edge.length','edge.begin_shape_index','edge.end_shape_index']}}
   u='https://valhalla1.openstreetmap.de/trace_attributes?json='+urllib.parse.quote(json.dumps(req))
   try:data=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'CityGuideTemplate-route-preparation/1.0','X-Client-Id':'city-guide-template'}),timeout=40))
   except urllib.error.HTTPError as e:
    message=e.read().decode()
    if e.code!=400:raise
    req['shape_match']='walk_or_snap'
    req['filters']['attributes']+=['matched.point','matched.type','matched.distance_from_trace_point','shape']
    u='https://valhalla1.openstreetmap.de/trace_attributes?json='+urllib.parse.quote(json.dumps(req))
    time.sleep(1.1)
    data=json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'CityGuideTemplate-route-preparation/1.0','X-Client-Id':'city-guide-template'}),timeout=40))
    data['_audit']={'method':'walk_or_snap','exactMatchFailure':message}
    print(source.name,index+1,'fallback matching',max((p.get('distance_from_trace_point',0) for p in data.get('matched_points',[])),default=None),flush=True)
   assert data.get('edges'),data
   dest.write_text(json.dumps(data,indent=2)+'\n');time.sleep(1.1)
  assert all(e['use'] not in ['ferry','rail_ferry'] and e['traversability']!='none' and e['road_class'] not in ['motorway'] for e in data['edges'])
  out.append({'leg':index+1,'edges':len(data['edges']),'uses':sorted(set(e['use'] for e in data['edges'])),'method':data.get('_audit',{}).get('method','edge_walk'),'roadEdges':[e for e in data['edges'] if e['use']=='road']})
 print(source.stem,json.dumps(out),flush=True)
