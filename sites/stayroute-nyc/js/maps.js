/* Leaflet 1.9.4; local route geometry, no runtime routing API. */
(() => {
'use strict';
const states = new WeakMap();
const escape = value => String(value).replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const config = window.STAYROUTE_MAP_CONFIG || {};
const tileURL = config.tileURL || 'https://tile.openstreetmap.org/{z}/{x}/{y}.png';
function info(p) {
  return `<strong>${escape(p.name)}</strong><p>${escape(p.lead)}</p><a href="place.html?id=${encodeURIComponent(p.id)}">Discover this place ↗</a>`;
}
window.StayrouteMaps = {
  render(container, places, route) {
    if (!window.L) {
      container.textContent = 'The interactive map is unavailable. You can still explore every place using the links below.';
      container.classList.add('map-unavailable');
      return;
    }
    let state = states.get(container);
    if (!state) {
      const map = L.map(container, {scrollWheelZoom:false, zoomControl:true, zoomSnap:0.25, minZoom:10, maxZoom:19}).setView([40.747,-73.983],12);
      map.attributionControl.setPrefix(false);
      container.setAttribute('aria-label', 'Interactive New York map. Use plus and minus to zoom, and drag to move.');
      const markers = L.featureGroup().addTo(map);
      const notice=document.createElement('div');
      notice.className='map-tile-status';
      notice.setAttribute('role','status');
      notice.innerHTML='<span>Loading street map…</span> <button type="button">Retry map</button>';
      container.after(notice);
      let failed = false;
      const tiles = L.tileLayer(tileURL, {
        maxZoom:19, detectRetina:false,
        attribution:config.attribution || '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        errorTileUrl:'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="256" height="256"%3E%3Crect width="256" height="256" fill="%23edf0eb"/%3E%3C/svg%3E'
      });
      tiles.on('loading',()=>{failed=false;});
      tiles.on('tileerror',()=>{
        failed = true; notice.hidden = false;
        notice.querySelector('span').textContent = 'Some street tiles are unavailable. Pins and saved routes remain visible; the background may be blank.';
      });
      tiles.on('load',()=>{if(!failed) notice.hidden=true;});
      notice.querySelector('button').onclick=()=>{notice.querySelector('span').textContent='Loading street map…';tiles.redraw();};
      tiles.addTo(map);
      state = {map,markers,pins:new Map(),routeLayer:null,selected:null,places:[],route:null};
      states.set(container,state);
      const fit = () => {
        const bounds = markers.getBounds();
        if(state.routeLayer) bounds.extend(state.routeLayer.getBounds());
        if(bounds.isValid()) map.fitBounds(bounds,{padding:[35,35],maxZoom:15,animate:false});
      };
      state.fit = fit;
      const overview=L.control({position:'topright'});
      overview.onAdd=()=>{
        const el=L.DomUtil.create('div','leaflet-bar map-fit');
        const button=document.createElement('button');button.type='button';button.textContent='↗↙';button.title='Show all places';button.setAttribute('aria-label','Show all places');button.onclick=fit;el.append(button);L.DomEvent.disableClickPropagation(el);return el;
      };
      overview.addTo(map);
      let resizeFrame;
      const resize=()=>{cancelAnimationFrame(resizeFrame);resizeFrame=requestAnimationFrame(()=>{map.invalidateSize({pan:false});fit();});};
      if(window.ResizeObserver){state.observer=new ResizeObserver(resize);state.observer.observe(container);}else window.addEventListener('resize',resize);
      state.choose = id => {
        const p=state.places.find(p=>p.id===id), pin=state.pins.get(id);
        if(!p||!pin)return;
        state.selected=id;
        state.pins.forEach((marker,key)=>{marker.getElement()?.classList.toggle('selected',key===id);marker.setZIndexOffset(key===id?1000:0);});
        document.querySelectorAll('[data-place-card]').forEach(el=>el.classList.toggle('map-active',el.dataset.placeCard===id));
        const selected=container.closest('.map-panel').querySelector('.map-selected');
        if(selected) selected.innerHTML=`<div>${info(p)}</div>`;
        if(!map.getBounds().contains(pin.getLatLng())) map.panTo(pin.getLatLng());
        pin.openPopup();
      };
      container.addEventListener('stayroute:select',e=>state.choose(e.detail));
    }
    state.places=places;
    state.markers.clearLayers();state.pins.clear();state.selected=null;
    const selected=container.closest('.map-panel').querySelector('.map-selected');
    if(selected) selected.innerHTML=`<div><b>${places.length?'Choose a place on the map':'No matching places'}</b><p>${places.length?'Select a pin or use Show on map on a card.':'Change your search or filters to see places here.'}</p></div>`;
    document.querySelectorAll('[data-place-card]').forEach(el=>el.classList.remove('map-active'));
    places.forEach((p,i)=>{
      const pin=L.marker([p.lat,p.lng], {
        icon:L.divIcon({className:'stayroute-pin',html:`<span>${route?i+1:'•'}</span>`,iconSize:[30,30],iconAnchor:[15,15],popupAnchor:[0,-16]}),
        title:p.name,alt:route?`Stop ${i+1}: ${p.name}`:p.name,keyboard:true
      }).bindPopup(info(p),{maxWidth:245,maxHeight:170,autoPanPaddingTopLeft:[45,95],autoPanPaddingBottomRight:[45,25]}).addTo(state.markers);
      pin.on('click',()=>state.choose(p.id));state.pins.set(p.id,pin);
    });
    state.fit();
    if(route && state.route !== route.id) {
      state.route=route.id;
      const caption=container.closest('.map-panel').querySelector('.map-caption');
      caption.textContent='Loading saved pedestrian route…';
      fetch(`data/routes/${encodeURIComponent(route.id)}.geojson`).then(r=>{if(!r.ok)throw new Error('route');return r.json();}).then(data=>{
        if(state.route!==route.id)return;
        if(data.type!=='FeatureCollection'||data.properties?.profile!=='pedestrian'||JSON.stringify(data.properties.stops)!==JSON.stringify(route.stops)||!data.features.length||data.features.some(f=>f.geometry?.type!=='LineString'||f.geometry.coordinates.length<2||f.geometry.coordinates.some(c=>!Array.isArray(c)||c.length<2||!c.every(Number.isFinite))))throw new Error('geometry');
        state.routeLayer=L.geoJSON(data,{style:{color:'#e96243',weight:5,opacity:0.9,lineCap:'round'}}).addTo(state.map);
        state.routeLayer.bringToBack();state.fit();
        caption.innerHTML='Saved pedestrian route · © <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors · Routing: <a href="https://valhalla.github.io/valhalla/">Valhalla</a> / FOSSGIS. Entrances and seasonal access may change. '+escape(route.mapNote||'');
      }).catch(()=>{caption.textContent='Saved walking route is unavailable. Only place markers are shown; no estimated connecting line is drawn.';});
    }
  },
  select(container,id){container?.dispatchEvent(new CustomEvent('stayroute:select',{detail:id}));}
};
})();
