import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

interface MapContainerProps {
  lat: number;
  lon: number;
  onMapClick: (lat: number, lon: number) => void;
  mode: 'ubike' | 'twbus' | 'places' | 'jptrain' | 'weather';
  data: any[];
  selectedItem: any;
  onSelectItem: (item: any) => void;
}

export default function MapContainer({
  lat,
  lon,
  onMapClick,
  mode,
  data,
  selectedItem,
  onSelectItem
}: MapContainerProps) {
  const mapRef = useRef<HTMLDivElement>(null);
  const mapInstance = useRef<L.Map | null>(null);
  const markerGroupRef = useRef<L.LayerGroup | null>(null);
  const centerMarkerRef = useRef<L.Marker | null>(null);

  // Initialize Map
  useEffect(() => {
    if (!mapRef.current || mapInstance.current) return;

    // Create Leaflet Map instance
    const map = L.map(mapRef.current, {
      center: [lat, lon],
      zoom: 15,
      zoomControl: true
    });

    // Dark theme OSM tiles (using CartoDB Dark Matter)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: 'abcd',
      maxZoom: 20
    }).addTo(map);

    // Create marker layer group
    const markerGroup = L.layerGroup().addTo(map);
    markerGroupRef.current = markerGroup;

    // Click handler on map to update active coordinate
    map.on('click', (e: L.LeafletMouseEvent) => {
      onMapClick(e.latlng.lat, e.latlng.lng);
    });

    mapInstance.current = map;

    return () => {
      map.remove();
      mapInstance.current = null;
    };
  }, []);

  // Update map view when coordinate changes
  useEffect(() => {
    const map = mapInstance.current;
    if (!map) return;

    map.setView([lat, lon], map.getZoom());

    // Update center marker
    if (centerMarkerRef.current) {
      centerMarkerRef.current.setLatLng([lat, lon]);
    } else {
      const centerIcon = L.divIcon({
        className: 'center-pin-icon',
        html: `<div style="background-color: #6366f1; width: 18px; height: 18px; border-radius: 50%; border: 3px solid #ffffff; box-shadow: 0 0 12px #6366f1; transform: scale(1.1); transition: transform 0.2s;"></div>`,
        iconSize: [18, 18],
        iconAnchor: [9, 9]
      });

      centerMarkerRef.current = L.marker([lat, lon], { icon: centerIcon, zIndexOffset: 1000 })
        .addTo(map)
        .bindPopup('搜尋中心點 (可拖曳改變位置)', { closeButton: false });
    }
  }, [lat, lon]);

  // Update markers based on current tab data
  useEffect(() => {
    const map = mapInstance.current;
    const markerGroup = markerGroupRef.current;
    if (!map || !markerGroup) return;

    // Clear previous markers
    markerGroup.clearLayers();

    if (!data || data.length === 0) return;

    data.forEach((item) => {
      let itemLat = 0;
      let itemLon = 0;
      let markerColor = '#6366f1'; // Primary default
      let popupContent = '';

      if (mode === 'ubike') {
        itemLat = item.lat;
        itemLon = item.lon;
        
        // Color depending on YouBike status
        if (item.service_status === 0 || item.available_rent_bikes === 0) {
          markerColor = '#ef4444'; // Red
        } else if (item.available_rent_bikes <= 3) {
          markerColor = '#f59e0b'; // Amber
        } else {
          markerColor = '#10b981'; // Green
        }
        
        popupContent = `
          <div style="font-family: sans-serif; color: #f8fafc; font-size: 13px;">
            <b style="font-size: 14px; display:block; margin-bottom:4px;">${item.name}</b>
            <div style="margin-bottom:8px; color: #94a3b8;">${item.address}</div>
            <div style="display:flex; gap:10px;">
              <span>🚲 可借: <b style="color:#10b981">${item.available_rent_bikes}</b></span>
              <span>🅿️ 可還: <b style="color:#6366f1">${item.available_return_bikes}</b></span>
            </div>
          </div>
        `;
      } else if (mode === 'twbus') {
        itemLat = item.lat;
        itemLon = item.lon;
        markerColor = '#3b82f6'; // Blue
        
        const etasHtml = item.etas && item.etas.length > 0
          ? item.etas.map((e: any) => {
              const minutes = e.estimate_time !== undefined && e.estimate_time !== null
                ? Math.floor(e.estimate_time / 60)
                : -1;
              const etaText = minutes >= 0 ? `${minutes} 分` : '未發車';
              return `<div style="display:flex; justify-content:space-between; gap:10px; margin-top:2px;">
                <span>${e.route_name}</span>
                <span style="font-weight:bold; color:#3b82f6">${etaText}</span>
              </div>`;
            }).join('')
          : '<div style="color:#94a3b8">無即時公車路線</div>';

        popupContent = `
          <div style="font-family: sans-serif; color: #f8fafc; font-size: 13px; min-width: 150px;">
            <b style="font-size: 14px; display:block; margin-bottom:4px;">${item.name}</b>
            <div style="border-top:1px solid #1f293d; margin-top:6px; padding-top:6px;">
              ${etasHtml}
            </div>
          </div>
        `;
      } else if (mode === 'places') {
        itemLat = item.lat;
        itemLon = item.lon;
        markerColor = '#f59e0b'; // Amber for restaurants/sights
        popupContent = `
          <div style="font-family: sans-serif; color: #f8fafc; font-size: 13px;">
            <b style="font-size: 14px; display:block; margin-bottom:4px;">${item.name}</b>
            <div style="color: #94a3b8; margin-bottom:4px;">${item.vicinity}</div>
            <div style="color: #f59e0b; font-weight:bold;">★ ${item.rating || '無評分'} (${item.user_ratings_total || 0})</div>
          </div>
        `;
      } else if (mode === 'weather') {
        itemLat = item.lat;
        itemLon = item.lon;
        markerColor = '#06b6d4'; // Cyan for weather pins
        popupContent = `
          <div style="font-family: sans-serif; color: #f8fafc; font-size: 13px;">
            <b style="font-size: 14px; display:block; margin-bottom:4px;">${item.name}</b>
            <div style="color: #94a3b8;">${item.address}</div>
          </div>
        `;
      }

      // Skip invalid coordinates
      if (!itemLat || !itemLon) return;

      const isSelected = selectedItem && selectedItem.uid === item.uid;

      // Create Custom Pin Icon
      const pinIcon = L.divIcon({
        className: `data-pin-icon-${item.uid}`,
        html: `
          <div style="
            background-color: ${markerColor};
            width: ${isSelected ? '16px' : '12px'};
            height: ${isSelected ? '16px' : '12px'};
            border-radius: 50%;
            border: 2px solid #ffffff;
            box-shadow: 0 0 10px ${markerColor};
            transform: scale(${isSelected ? '1.3' : '1'});
            transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
            cursor: pointer;
          "></div>
        `,
        iconSize: isSelected ? [16, 16] : [12, 12],
        iconAnchor: isSelected ? [8, 8] : [6, 6]
      });

      const marker = L.marker([itemLat, itemLon], { icon: pinIcon })
        .addTo(markerGroup)
        .bindPopup(popupContent, { closeButton: false });

      marker.on('click', () => {
        onSelectItem(item);
      });
      
      // Auto open popup if selected
      if (isSelected) {
        marker.openPopup();
      }
    });
  }, [data, mode, selectedItem]);

  return <div ref={mapRef} className="map-viewport" id="map" />;
}
