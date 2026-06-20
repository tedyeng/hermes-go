import { useState, useEffect } from 'react';
import './App.css';
import Sidebar from './components/Sidebar';
import MapContainer from './components/MapContainer';

type Mode = 'ubike' | 'twbus' | 'places' | 'jptrain';

// Helper to determine the API endpoint based on development vs production mode
const getApiUrl = (path: string) => {
  const hostname = (window as any).__MOCK_HOSTNAME__ || window.location.hostname;
  const port = (window as any).__MOCK_PORT__ || window.location.port;
  const isDev = hostname === 'localhost' || hostname === '127.0.0.1';
  // If running on Vite dev server (usually 5173), target the FastAPI backend at 8000
  if (isDev && port !== '8000' && port !== '') {
    return `http://localhost:8000${path}`;
  }
  return path;
};

export default function App() {
  // Coordinates default to Taipei City Hall
  const [mode, setMode] = useState<Mode>('ubike');
  const [lat, setLat] = useState(25.0338);
  const [lon, setLon] = useState(121.5298);
  const [radius, setRadius] = useState(500);
  
  const [data, setData] = useState<any[]>([]);
  const [selectedItem, setSelectedItem] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Taiwan Bus dynamic inputs & results
  const [busDest, setBusDest] = useState('');
  const [busRoutes, setBusRoutes] = useState<any[]>([]);
  const [isRoutingBus, setIsRoutingBus] = useState(false);

  // Places filters
  const [placesType, setPlacesType] = useState('全部');

  // Japan Train list & routing
  const [jpAreas, setJpAreas] = useState<any[]>([]);
  const [selectedJpArea, setSelectedJpArea] = useState('');
  const [jpRoutes, setJpRoutes] = useState<any[]>([]);
  const [jpFromStation, setJpFromStation] = useState('');
  const [jpToStation, setJpToStation] = useState('');
  const [isRoutingJp, setIsRoutingJp] = useState(false);

  // 1. Fetch Japan Train areas on initial load
  useEffect(() => {
    const fetchJpAreas = async () => {
      try {
        const res = await fetch(getApiUrl('/api/jptrain/areas'));
        const json = await res.json();
        if (json.status === 'success') {
          setJpAreas(json.data);
          if (json.data.length > 0 && !selectedJpArea) {
            setSelectedJpArea(json.data[0].code);
          }
        }
      } catch (err) {
        console.error('Failed to load Japan train areas:', err);
      }
    };
    fetchJpAreas();
  }, []);

  // 2. Fetch data automatically based on coordinates and filters
  useEffect(() => {
    // Reset selected items and transient routing results
    setSelectedItem(null);
    setBusRoutes([]);
    setJpRoutes([]);
    setError(null);

    // Japan Train handles status fetch independently (it uses areas, not lat/lon)
    if (mode === 'jptrain') {
      if (selectedJpArea) {
        fetchJpStatus();
      } else {
        setData([]);
      }
      return;
    }

    const fetchData = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        let endpoint = '';
        if (mode === 'ubike') {
          endpoint = `/api/ubike/nearby?lat=${lat}&lon=${lon}&radius=${radius}`;
        } else if (mode === 'twbus') {
          endpoint = `/api/twbus/nearby?lat=${lat}&lon=${lon}&radius=${radius}`;
        } else { // mode === 'places'
          const typeParam = placesType !== '全部' ? `&type=${encodeURIComponent(placesType)}` : '';
          endpoint = `/api/places/nearby?lat=${lat}&lon=${lon}&radius=${radius}${typeParam}`;
        }

        const res = await fetch(getApiUrl(endpoint));
        if (!res.ok) {
          throw new Error(`伺服器連線失敗 (HTTP ${res.status})`);
        }
        
        const json = await res.json();
        if (json.status === 'success') {
          setData(json.data);
        } else {
          setError(json.message || '查詢時發生未知錯誤。');
        }
      } catch (err: any) {
        setError(err.message || '無法連線至 Hermes API 後端。請確認後端是否正在運作。');
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [mode, lat, lon, radius, placesType]);

  // Fetch Japan train delay warning list
  const fetchJpStatus = async () => {
    if (!selectedJpArea) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(getApiUrl(`/api/jptrain/status?area_code=${selectedJpArea}`));
      const json = await res.json();
      if (json.status === 'success') {
        setData(json.data);
      } else {
        setError('無法獲取鐵路運行狀態');
      }
    } catch (err: any) {
      setError('連線至後端失敗');
    } finally {
      setIsLoading(false);
    }
  };

  // Trigger Japan status fetch again on area switch
  useEffect(() => {
    if (mode === 'jptrain' && selectedJpArea) {
      fetchJpStatus();
    }
  }, [selectedJpArea]);

  // Handler for address/GPS search box
  const handleSearchSubmit = async (text: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(getApiUrl('/api/utils/parse-gps'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text })
      });
      const json = await res.json();
      if (json.status === 'success') {
        setLat(json.lat);
        setLon(json.lon);
      } else {
        alert(json.message || '無法解析輸入的經緯度或地址');
      }
    } catch (err) {
      alert('連線至後端 API 解析失敗');
    } finally {
      setIsLoading(false);
    }
  };

  // Bus route planner search
  const handleBusRouteSearch = async () => {
    if (!busDest) return;
    setIsRoutingBus(true);
    setBusRoutes([]);
    try {
      const res = await fetch(getApiUrl(`/api/twbus/route?start_lat=${lat}&start_lon=${lon}&dest=${encodeURIComponent(busDest)}&radius=${radius}`));
      const json = await res.json();
      if (json.status === 'success') {
        setBusRoutes(json.data);
        // Pan map center to coordinates of resolved destination
        if (json.dest_coords) {
          // Keep search center, just show route data
        }
      } else {
        alert(json.message || '搜尋路線失敗');
      }
    } catch (err) {
      alert('計算公車直達路線失敗，請確認 API 狀態。');
    } finally {
      setIsRoutingBus(false);
    }
  };

  // Japan train journey route planner
  const handleJpRouteSearch = async () => {
    if (!jpFromStation || !jpToStation) return;
    setIsRoutingJp(true);
    setJpRoutes([]);
    try {
      const res = await fetch(getApiUrl(`/api/jptrain/route?from_station=${encodeURIComponent(jpFromStation)}&to_station=${encodeURIComponent(jpToStation)}`));
      const json = await res.json();
      if (json.status === 'success') {
        setJpRoutes(json.data);
      } else {
        alert(json.message || '查詢路線失敗');
      }
    } catch (err) {
      alert('計算日本鐵道乘車路線失敗');
    } finally {
      setIsRoutingJp(false);
    }
  };

  return (
    <div className="dashboard-container">
      {/* Sidebar Section */}
      <Sidebar
        mode={mode}
        lat={lat}
        lon={lon}
        radius={radius}
        setRadius={setRadius}
        data={data}
        isLoading={isLoading}
        error={error}
        selectedItem={selectedItem}
        onSelectItem={(item) => setSelectedItem(item)}
        onCoordinatesChange={(newLat, newLon) => {
          setLat(newLat);
          setLon(newLon);
        }}
        onSearchSubmit={handleSearchSubmit}
        busDest={busDest}
        setBusDest={setBusDest}
        busRoutes={busRoutes}
        isRoutingBus={isRoutingBus}
        onBusRouteSearch={handleBusRouteSearch}
        jpAreas={jpAreas}
        selectedJpArea={selectedJpArea}
        setSelectedJpArea={setSelectedJpArea}
        jpRoutes={jpRoutes}
        jpFromStation={jpFromStation}
        setJpFromStation={setJpFromStation}
        jpToStation={jpToStation}
        setJpToStation={setJpToStation}
        onJpRouteSearch={handleJpRouteSearch}
        isRoutingJp={isRoutingJp}
        placesType={placesType}
        setPlacesType={setPlacesType}
      />

      {/* Main Map View Section */}
      <div style={{ flexGrow: 1, height: '100%', position: 'relative', display: 'flex', flexDirection: 'column' }}>
        {/* Navigation Tabs (Floating Card Style) */}
        <div style={{
          position: 'absolute',
          top: '20px',
          left: '20px',
          zIndex: 1000,
          background: 'var(--bg-card)',
          backdropFilter: 'blur(16px)',
          borderRadius: '12px',
          border: '1px solid var(--border-color)',
          boxShadow: 'var(--shadow-lg)'
        }}>
          <div className="tabs-container" style={{ borderBottom: 'none', padding: '0 8px' }}>
            <button
              className={`tab-btn ${mode === 'ubike' ? 'active' : ''}`}
              onClick={() => setMode('ubike')}
            >
              🚲 YouBike 車位
            </button>
            <button
              className={`tab-btn ${mode === 'twbus' ? 'active' : ''}`}
              onClick={() => setMode('twbus')}
            >
              🚌 台灣公車 ETA
            </button>
            <button
              className={`tab-btn ${mode === 'places' ? 'active' : ''}`}
              onClick={() => setMode('places')}
            >
              🗺️ 景點美食
            </button>
            <button
              className={`tab-btn ${mode === 'jptrain' ? 'active' : ''}`}
              onClick={() => setMode('jptrain')}
            >
              🚄 日本鐵道
            </button>
          </div>
        </div>

        {/* Map Instance */}
        <MapContainer
          lat={lat}
          lon={lon}
          mode={mode}
          data={data}
          selectedItem={selectedItem}
          onSelectItem={(item) => setSelectedItem(item)}
          onMapClick={(newLat, newLon) => {
            setLat(newLat);
            setLon(newLon);
          }}
        />
      </div>
    </div>
  );
}
