import React, { useState } from 'react';
import { getBikesStatusColor, formatEta } from '../utils/helpers';

interface SidebarProps {
  mode: 'ubike' | 'twbus' | 'places' | 'jptrain' | 'weather';
  lat: number;
  lon: number;
  radius: number;
  setRadius: (r: number) => void;
  data: any[];
  isLoading: boolean;
  error: string | null;
  selectedItem: any;
  onSelectItem: (item: any) => void;
  onCoordinatesChange: (lat: number, lon: number) => void;
  onSearchSubmit: (text: string) => Promise<void>;
  
  // Twbus specific inputs
  busDest: string;
  setBusDest: (val: string) => void;
  busRoutes: any[];
  isRoutingBus: boolean;
  onBusRouteSearch: () => void;
  
  // Japan Train specific states & callbacks
  jpAreas: any[];
  selectedJpArea: string;
  setSelectedJpArea: (area: string) => void;
  jpRoutes: any[];
  jpFromStation: string;
  setJpFromStation: (val: string) => void;
  jpToStation: string;
  setJpToStation: (val: string) => void;
  onJpRouteSearch: () => void;
  isRoutingJp: boolean;
  
  // Places specific states
  placesType: string;
  setPlacesType: (t: string) => void;

  // Weather specific states
  weatherSubMode?: 'rain' | 'check' | 'hourly';
  setWeatherSubMode?: (val: 'rain' | 'check' | 'hourly') => void;
  weatherData?: any;
  isHourlyAll?: boolean;
  setIsHourlyAll?: (val: boolean) => void;
}

export default function Sidebar({
  mode,
  lat,
  lon,
  radius,
  setRadius,
  data,
  isLoading,
  error,
  selectedItem,
  onSelectItem,
  onCoordinatesChange,
  onSearchSubmit,
  
  busDest,
  setBusDest,
  busRoutes,
  isRoutingBus,
  onBusRouteSearch,
  
  jpAreas,
  selectedJpArea,
  setSelectedJpArea,
  jpRoutes,
  jpFromStation,
  setJpFromStation,
  jpToStation,
  setJpToStation,
  onJpRouteSearch,
  isRoutingJp,
  
  placesType,
  setPlacesType,
  weatherSubMode,
  setWeatherSubMode,
  weatherData,
  isHourlyAll,
  setIsHourlyAll
}: SidebarProps) {
  const [searchText, setSearchText] = useState('');
  const [isLocating, setIsLocating] = useState(false);
  const [isBusSubMode, setIsBusSubMode] = useState<'nearby' | 'route'>('nearby');
  const [isJpSubMode, setIsJpSubMode] = useState<'status' | 'route'>('status');

  // Trigger search on submit
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchText.trim()) return;
    onSearchSubmit(searchText);
  };

  // Browser geolocation request
  const requestLocation = () => {
    if (!navigator.geolocation) {
      alert('您的瀏覽器不支援定位功能。');
      return;
    }
    
    setIsLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        onCoordinatesChange(pos.coords.latitude, pos.coords.longitude);
        setIsLocating(false);
      },
      (err) => {
        console.error(err);
        alert('無法取得您的位置，請確認定位權限。');
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 5000 }
    );
  };

  return (
    <aside className="sidebar">
      {/* Search Header */}
      <div className="sidebar-header">
        <div className="brand">
          <span className="brand-icon">⚡</span>
          <h1 className="brand-title">Hermes Go Dashboard</h1>
        </div>
        
        <form onSubmit={handleSearch} className="search-container">
          <input
            type="text"
            className="search-input"
            placeholder="搜尋經緯度, 地址或 Google Map..."
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
          />
          <button type="submit" className="btn-icon" title="搜尋">
            🔍
          </button>
          <button
            type="button"
            className={`btn-icon ${isLocating ? 'active' : ''}`}
            onClick={requestLocation}
            title="使用我的目前位置"
          >
            {isLocating ? '⌛' : '📍'}
          </button>
        </form>
        
        <div style={{ fontSize: '11px', color: 'var(--text-muted)', marginTop: '8px', textAlign: 'right' }}>
          座標: {lat.toFixed(4)}, {lon.toFixed(4)}
        </div>
      </div>

      {/* Sidebar Content Panel */}
      <div className="sidebar-content">
        {/* Radius control (for nearby searches) */}
        {mode !== 'jptrain' && (mode !== 'twbus' || isBusSubMode === 'nearby') && (
          <div className="radius-slider-container">
            <span className="filter-title">搜尋半徑</span>
            <input
              type="range"
              className="radius-slider"
              min="100"
              max="2000"
              step="100"
              value={radius}
              onChange={(e) => setRadius(parseInt(e.target.value))}
            />
            <span className="radius-value">{radius}m</span>
          </div>
        )}

        {/* --- YouBike Mode --- */}
        {mode === 'ubike' && (
          <>
            <div className="filter-row">
              <span className="filter-title">附近的 YouBike 站點</span>
            </div>
            
            {isLoading && (
              <div className="loading-indicator">
                <div className="spinner"></div> 載入中...
              </div>
            )}
            
            {error && <div className="error-message">{error}</div>}
            
            {!isLoading && !error && data.length === 0 && (
              <div className="empty-state">此範圍內沒有 YouBike 站點。</div>
            )}
            
            {!isLoading && !error && data.map((item) => {
              const statusColor = getBikesStatusColor(item.available_rent_bikes, item.capacity, item.service_status);
              const isSelected = selectedItem && selectedItem.uid === item.uid;
              
              return (
                <div
                  key={item.uid}
                  className={`list-card glass ${isSelected ? 'selected' : ''}`}
                  onClick={() => onSelectItem(item)}
                >
                  <div className="card-title">{item.name}</div>
                  <div className="card-subtitle">{item.address}</div>
                  <div className="ubike-stats-grid">
                    <div className="ubike-stat-box">
                      <div className="ubike-stat-val available">{item.available_rent_bikes}</div>
                      <div className="ubike-stat-lbl">可借車輛</div>
                    </div>
                    <div className="ubike-stat-box">
                      <div className="ubike-stat-val return">{item.available_return_bikes}</div>
                      <div className="ubike-stat-lbl">可還空位</div>
                    </div>
                  </div>
                  <div className="card-meta">
                    <span
                      className="badge-status success"
                      style={{ backgroundColor: statusColor + '1A', color: statusColor }}
                    >
                      ● {item.service_status === 1 ? '營運中' : '暫停營運'}
                    </span>
                    <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      總車位: {item.capacity}
                    </span>
                  </div>
                </div>
              );
            })}
          </>
        )}

        {/* --- Taiwan Bus Mode --- */}
        {mode === 'twbus' && (
          <>
            {/* Bus submodes switches */}
            <div className="places-chips-container">
              <button
                className={`chip-filter ${isBusSubMode === 'nearby' ? 'active' : ''}`}
                onClick={() => setIsBusSubMode('nearby')}
              >
                附近公車站牌
              </button>
              <button
                className={`chip-filter ${isBusSubMode === 'route' ? 'active' : ''}`}
                onClick={() => setIsBusSubMode('route')}
              >
                直達路線規劃
              </button>
            </div>

            {isBusSubMode === 'nearby' ? (
              <>
                <div className="filter-row">
                  <span className="filter-title">附近的公車站牌 (即時到站)</span>
                </div>
                
                {isLoading && (
                  <div className="loading-indicator">
                    <div className="spinner"></div> 載入站牌與 ETA...
                  </div>
                )}
                
                {error && <div className="error-message">{error}</div>}
                
                {!isLoading && !error && data.length === 0 && (
                  <div className="empty-state">此範圍內沒有公車站牌。</div>
                )}
                
                {!isLoading && !error && data.map((stop) => {
                  const isSelected = selectedItem && selectedItem.uid === stop.uid;
                  return (
                    <div
                      key={stop.uid}
                      className={`list-card glass ${isSelected ? 'selected' : ''}`}
                      onClick={() => onSelectItem(stop)}
                    >
                      <div className="card-title">🚌 {stop.name}</div>
                      <div className="card-subtitle">{stop.address || '無地址資訊'}</div>
                      <div className="bus-etas-list">
                        {stop.etas && stop.etas.length > 0 ? (
                          stop.etas.slice(0, 5).map((e: any, idx: number) => {
                            const isIncoming = e.estimate_time !== undefined && e.estimate_time !== null && e.estimate_time <= 60;
                            return (
                              <div key={idx} className="bus-eta-item">
                                <span className="bus-eta-route">{e.route_name}</span>
                                <span className={`bus-eta-time ${isIncoming ? 'active' : 'normal'}`}>
                                  {formatEta(e.estimate_time, e.status)}
                                </span>
                              </div>
                            );
                          })
                        ) : (
                          <div style={{ fontSize: '12px', color: 'var(--text-muted)' }}>暫無公車動態資訊</div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </>
            ) : (
              <>
                <div className="filter-row">
                  <span className="filter-title">直達公車路網規劃</span>
                </div>
                
                <div className="route-planner-box glass">
                  <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>目的地地址/地標</label>
                  <input
                    type="text"
                    className="route-planner-input"
                    placeholder="例如：台北車站、台北101"
                    value={busDest}
                    onChange={(e) => setBusDest(e.target.value)}
                  />
                  <button
                    className="btn-primary"
                    onClick={onBusRouteSearch}
                    disabled={isRoutingBus || !busDest}
                  >
                    {isRoutingBus ? '規劃中...' : '開始規劃'}
                  </button>
                </div>

                {isRoutingBus && (
                  <div className="loading-indicator">
                    <div className="spinner"></div> 計算直達公車路線中...
                  </div>
                )}

                {busRoutes && busRoutes.length > 0 ? (
                  busRoutes.map((r: any, idx: number) => (
                    <div key={idx} className="list-card glass">
                      <div className="card-title" style={{ color: 'var(--color-primary)' }}>
                        公車路線 {r.route_name}
                      </div>
                      <div style={{ fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                        <div>起點上車站：<b>{r.start_stop}</b></div>
                        <div>目的地終點：<b>{r.dest_stop}</b></div>
                        <div>乘坐站數：<b>{r.stops_count} 站</b></div>
                      </div>
                      <div className="card-meta">
                        <span className="badge-status success">
                          ● 直達路線
                        </span>
                        <span style={{ fontSize: '13px', fontWeight: 'bold', color: 'var(--color-success)' }}>
                          ETA: {formatEta(r.eta)}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  !isRoutingBus && busRoutes && <div className="empty-state">查無此目的地之直達公車方案。</div>
                )}
              </>
            )}
          </>
        )}

        {/* --- Places Mode --- */}
        {mode === 'places' && (
          <>
            <div className="filter-row">
              <span className="filter-title">周邊美食與觀光景點</span>
            </div>

            {/* Places filters chips */}
            <div className="places-chips-container">
              {['全部', '餐廳', '咖啡廳', '酒吧', '景點'].map((t) => (
                <button
                  key={t}
                  className={`chip-filter ${placesType === t ? 'active' : ''}`}
                  onClick={() => setPlacesType(t)}
                >
                  {t}
                </button>
              ))}
            </div>

            {isLoading && (
              <div className="loading-indicator">
                <div className="spinner"></div> 載入美食景點...
              </div>
            )}
            
            {error && <div className="error-message">{error}</div>}
            
            {!isLoading && !error && data.length === 0 && (
              <div className="empty-state">此範圍內查無美食景點。</div>
            )}

            {!isLoading && !error && data.map((item) => {
              const isSelected = selectedItem && selectedItem.uid === item.uid;
              return (
                <div
                  key={item.uid}
                  className={`list-card glass ${isSelected ? 'selected' : ''}`}
                  onClick={() => onSelectItem(item)}
                >
                  <div className="card-title">{item.name}</div>
                  <div className="card-subtitle">{item.vicinity}</div>
                  
                  <div className="card-meta">
                    <div className="places-rating">
                      <span className="places-rating-stars">★</span>
                      <span>{item.rating ? `${item.rating} (${item.user_ratings_total} 評價)` : '暫無評價'}</span>
                    </div>
                    {item.open_now !== null && (
                      <span className={`badge-status ${item.open_now ? 'success' : 'danger'}`}>
                        {item.open_now ? '營業中' : '休息中'}
                      </span>
                    )}
                  </div>
                </div>
              );
            })}
          </>
        )}

        {/* --- Japan Train Mode --- */}
        {mode === 'jptrain' && (
          <>
            <div className="places-chips-container">
              <button
                className={`chip-filter ${isJpSubMode === 'status' ? 'active' : ''}`}
                onClick={() => setIsJpSubMode('status')}
              >
                運行警報概況
              </button>
              <button
                className={`chip-filter ${isJpSubMode === 'route' ? 'active' : ''}`}
                onClick={() => setIsJpSubMode('route')}
              >
                鐵道轉乘規劃
              </button>
            </div>

            {isJpSubMode === 'status' ? (
              <>
                <div className="filter-row">
                  <span className="filter-title">選擇日本區域</span>
                </div>
                
                <select
                  value={selectedJpArea}
                  onChange={(e) => setSelectedJpArea(e.target.value)}
                  style={{
                    backgroundColor: 'var(--bg-input)',
                    border: '1px solid var(--border-color)',
                    color: 'var(--text-primary)',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    outline: 'none',
                    fontFamily: 'var(--font-primary)'
                  }}
                >
                  <option value="">-- 請選擇地區 --</option>
                  {jpAreas.map((area: any) => (
                    <option key={area.code} value={area.code}>
                      {area.name} ({area.code})
                    </option>
                  ))}
                </select>

                {isLoading && (
                  <div className="loading-indicator">
                    <div className="spinner"></div> 載入運行狀態中...
                  </div>
                )}

                {error && <div className="error-message">{error}</div>}

                {!isLoading && !error && data.length > 0 && (
                  data.map((line: any, idx: number) => {
                    const isDelay = line.status_type !== 'normal';
                    return (
                      <div key={idx} className="list-card glass">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{line.company}</span>
                          <span className={`badge-status ${isDelay ? 'danger' : 'success'}`}>
                            {line.status}
                          </span>
                        </div>
                        <div className="card-title" style={{ marginTop: '-4px' }}>
                          🚄 {line.name}
                        </div>
                        {line.detail_info && (
                          <div style={{
                            fontSize: '12px',
                            color: 'var(--color-warning)',
                            backgroundColor: 'rgba(245, 158, 11, 0.05)',
                            padding: '8px',
                            borderRadius: '6px',
                            lineHeight: '1.4',
                            border: '1px solid rgba(245, 158, 11, 0.15)'
                          }}>
                            {line.detail_info}
                          </div>
                        )}
                        {line.update_time && (
                          <div style={{ fontSize: '10px', color: 'var(--text-muted)', textAlign: 'right' }}>
                            更新時間: {line.update_time}
                          </div>
                        )}
                      </div>
                    );
                  })
                )}
              </>
            ) : (
              <>
                <div className="filter-row">
                  <span className="filter-title">日本起訖鐵道規劃</span>
                </div>
                
                <div className="route-planner-box glass">
                  <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>出發車站</label>
                  <input
                    type="text"
                    className="route-planner-input"
                    placeholder="如：東京"
                    value={jpFromStation}
                    onChange={(e) => setJpFromStation(e.target.value)}
                  />
                  
                  <label style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>目的車站</label>
                  <input
                    type="text"
                    className="route-planner-input"
                    placeholder="如：新宿"
                    value={jpToStation}
                    onChange={(e) => setJpToStation(e.target.value)}
                  />
                  
                  <button
                    className="btn-primary"
                    onClick={onJpRouteSearch}
                    disabled={isRoutingJp || !jpFromStation || !jpToStation}
                  >
                    {isRoutingJp ? '行程計算中...' : '開始規劃'}
                  </button>
                </div>

                {isRoutingJp && (
                  <div className="loading-indicator">
                    <div className="spinner"></div> 計算乘車路徑中...
                  </div>
                )}

                {jpRoutes && jpRoutes.length > 0 ? (
                  jpRoutes.map((route: any, idx: number) => (
                    <div key={idx} className="list-card glass" style={{ gap: '8px' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', fontSize: '14px', color: 'var(--color-primary)' }}>
                        <span>方案 {idx + 1}</span>
                        <span>時間: {route.time_required || '未知'} 分</span>
                      </div>
                      <div style={{ fontSize: '13px' }}>
                        <div>票價: <b>{route.fare || '未知'} 日圓</b></div>
                        <div>轉乘次數: <b>{route.transfer_count ?? '0'} 次</b></div>
                      </div>
                      <div style={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '6px',
                        borderLeft: '2px solid var(--border-color)',
                        paddingLeft: '10px',
                        marginLeft: '4px',
                        fontSize: '12px'
                      }}>
                        {route.steps && route.steps.map((step: any, sIdx: number) => (
                          <div key={sIdx}>
                            {step.departure_time && <span>[{step.departure_time}] </span>}
                            <b>{step.station_name}</b>
                            {step.line_name && <div style={{ color: 'var(--text-secondary)', fontSize: '11px', margin: '2px 0' }}>➔ 搭乘: {step.line_name}</div>}
                          </div>
                        ))}
                      </div>
                    </div>
                  ))
                ) : (
                  !isRoutingJp && jpRoutes && <div className="empty-state">沒有找到乘車路線方案。</div>
                )}
              </>
            )}
          </>
        )}

        {/* --- Weather Mode --- */}
        {mode === 'weather' && setWeatherSubMode && (
          <>
            {/* Weather submode switches */}
            <div className="places-chips-container" style={{ marginBottom: '16px' }}>
              <button
                className={`chip-filter ${weatherSubMode === 'rain' ? 'active' : ''}`}
                onClick={() => setWeatherSubMode('rain')}
              >
                💧 雨量與預期
              </button>
              <button
                className={`chip-filter ${weatherSubMode === 'check' ? 'active' : ''}`}
                onClick={() => setWeatherSubMode('check')}
              >
                🔮 三日天氣預報
              </button>
              <button
                className={`chip-filter ${weatherSubMode === 'hourly' ? 'active' : ''}`}
                onClick={() => setWeatherSubMode('hourly')}
              >
                🕒 逐小時天氣
              </button>
            </div>

            {isLoading && (
              <div className="loading-indicator">
                <div className="spinner"></div> 載入天氣資料中...
              </div>
            )}

            {error && <div className="error-message">{error}</div>}

            {!isLoading && !error && weatherData && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                {/* 1. Rain & Forecast Submode */}
                {weatherSubMode === 'rain' && (
                  <>
                    {/* Station Info Card */}
                    <div className="list-card glass" style={{ padding: '12px' }}>
                      <div className="card-title" style={{ fontSize: '14px', color: 'var(--color-primary)' }}>
                        📡 最近雨量觀測站
                      </div>
                      <div style={{ fontSize: '13px', display: 'flex', flexDirection: 'column', gap: '4px', marginTop: '6px' }}>
                        <div>站名: <b>{weatherData.station?.name} ({weatherData.station?.id})</b></div>
                        <div>距離: <b>{weatherData.station?.distance_km} km</b></div>
                        <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                          觀測時間: {weatherData.station?.obs_time}
                        </div>
                      </div>
                    </div>

                    {/* Rain Observations Card */}
                    <div className="list-card glass" style={{ padding: '12px' }}>
                      <div className="card-title" style={{ fontSize: '14px', color: 'var(--color-primary)' }}>
                        💧 即時累積降雨量
                      </div>
                      <div style={{
                        display: 'grid',
                        gridTemplateColumns: 'repeat(2, 1fr)',
                        gap: '8px',
                        fontSize: '12px',
                        marginTop: '8px'
                      }}>
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '6px', borderRadius: '4px' }}>
                          <span style={{ color: 'var(--text-muted)' }}>10分鐘累積</span>
                          <div style={{ fontSize: '14px', fontWeight: 'bold', marginTop: '2px' }}>
                            {weatherData.observations?.past_10m}
                          </div>
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '6px', borderRadius: '4px' }}>
                          <span style={{ color: 'var(--text-muted)' }}>過去1小時</span>
                          <div style={{ fontSize: '14px', fontWeight: 'bold', marginTop: '2px' }}>
                            {weatherData.observations?.past_1h}
                          </div>
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '6px', borderRadius: '4px' }}>
                          <span style={{ color: 'var(--text-muted)' }}>過去3小時</span>
                          <div style={{ fontSize: '14px', fontWeight: 'bold', marginTop: '2px' }}>
                            {weatherData.observations?.past_3h}
                          </div>
                        </div>
                        <div style={{ background: 'rgba(255,255,255,0.02)', padding: '6px', borderRadius: '4px' }}>
                          <span style={{ color: 'var(--text-muted)' }}>過去24小時</span>
                          <div style={{ fontSize: '14px', fontWeight: 'bold', marginTop: '2px' }}>
                            {weatherData.observations?.past_24h}
                          </div>
                        </div>
                      </div>
                      <div style={{
                        marginTop: '10px',
                        borderTop: '1px solid var(--border-color)',
                        paddingTop: '8px',
                        display: 'flex',
                        flexDirection: 'column',
                        gap: '4px',
                        fontSize: '13px'
                      }}>
                        <div>今日累積量: <b>{weatherData.observations?.today}</b></div>
                        <div style={{ color: 'var(--color-primary)' }}>
                          即時雨勢體感: <b style={{ color: '#06b6d4' }}>{weatherData.observations?.intensity_label}</b>
                        </div>
                        <div>
                          防汛警戒分級: <span style={{
                            fontWeight: 'bold',
                            color: weatherData.alert?.color === 'red' ? 'var(--color-danger)' :
                                   weatherData.alert?.color === 'yellow' ? 'var(--color-warning)' : 'var(--color-success)'
                          }}>{weatherData.alert?.level}</span>
                        </div>
                      </div>
                    </div>

                    {/* Rain Forecast Outlook Card */}
                    {weatherData.forecast && weatherData.forecast.length > 0 && (
                      <div className="list-card glass" style={{ padding: '12px' }}>
                        <div className="card-title" style={{ fontSize: '14px', color: 'var(--color-primary)', marginBottom: '8px' }}>
                          🔮 未來兩日降雨預估
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                          {weatherData.forecast.map((item: any, idx: number) => {
                            const isHighPop = item.pop >= 70;
                            return (
                              <div key={idx} style={{
                                padding: '6px 8px',
                                background: 'rgba(255,255,255,0.01)',
                                borderLeft: `3px solid ${isHighPop ? 'var(--color-danger)' : 'var(--border-color)'}`,
                                fontSize: '12px'
                              }}>
                                <div style={{ fontWeight: 'bold', color: 'var(--text-primary)' }}>{item.period}</div>
                                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '2px', color: 'var(--text-muted)' }}>
                                  <span>天氣: {item.wx} ({item.pop}%)</span>
                                  <span style={{ color: isHighPop ? 'var(--color-danger)' : 'var(--text-secondary)' }}>
                                    {item.est_volume}
                                  </span>
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </>
                )}

                {/* 2. 3-Day Forecast Submode */}
                {weatherSubMode === 'check' && weatherData.data && (
                  <>
                    <div style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                      查詢層級: {weatherData.level === 'town' ? `鄉鎮市區 (${weatherData.county} ${weatherData.district})` : `縣市總體 (${weatherData.county})`}
                    </div>
                    {weatherData.data.map((item: any, idx: number) => {
                      const pop = item.pop ?? 0;
                      const isRain = pop >= 30;
                      return (
                        <div key={idx} className="list-card glass" style={{ padding: '12px' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontWeight: 'bold', fontSize: '13px' }}>{item.period_name}</span>
                            {item.recommendation && (
                              <span style={{
                                fontSize: '11px',
                                padding: '2px 6px',
                                borderRadius: '4px',
                                backgroundColor: isRain ? 'rgba(239, 68, 68, 0.1)' : 'rgba(16, 185, 129, 0.1)',
                                color: isRain ? 'var(--color-danger)' : 'var(--color-success)'
                              }}>{item.recommendation}</span>
                            )}
                          </div>
                          <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(2, 1fr)',
                            gap: '4px',
                            fontSize: '12px',
                            marginTop: '8px',
                            color: 'var(--text-secondary)'
                          }}>
                            <div>溫度: <b>{item.temp_min}°C ~ {item.temp_max}°C</b></div>
                            <div>降雨機率: <b>{pop}%</b></div>
                            <div style={{ gridColumn: 'span 2' }}>天氣: <b>{item.wx_summary}</b></div>
                            {item.comfort && <div style={{ gridColumn: 'span 2' }}>舒適度: <b>{item.comfort}</b></div>}
                          </div>
                        </div>
                      );
                    })}
                  </>
                )}

                {/* 3. Hourly Forecast Submode */}
                {weatherSubMode === 'hourly' && weatherData.data && setIsHourlyAll && (
                  <>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>{weatherData.title}</span>
                      <button
                        className="chip-filter"
                        style={{ padding: '2px 8px', fontSize: '10px', height: 'auto' }}
                        onClick={() => setIsHourlyAll(!isHourlyAll)}
                      >
                        {isHourlyAll ? '切換今日/24h' : '顯示完整48h'}
                      </button>
                    </div>

                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '400px', overflowY: 'auto', paddingRight: '4px' }}>
                      {weatherData.data.map((item: any, idx: number) => {
                        const dateObj = new Date(item.datetime);
                        const timeDisplay = dateObj.toLocaleTimeString('zh-TW', { hour: '2-digit', minute: '2-digit', hour12: false });
                        const dateDisplay = `${dateObj.getMonth() + 1}/${dateObj.getDate()}`;
                        const isHighRain = item.pop >= 70;
                        const isStrongWind = parseFloat(item.wind_speed) >= 10.8;
                        
                        return (
                          <div
                            key={idx}
                            className="list-card glass"
                            style={{
                              padding: '8px 10px',
                              borderLeft: `3px solid ${isHighRain ? 'var(--color-danger)' : 'var(--border-color)'}`,
                              marginBottom: 0
                            }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 'bold', fontSize: '12px' }}>
                              <span>🕒 {dateDisplay} {timeDisplay}</span>
                              <span style={{ color: isHighRain ? 'var(--color-danger)' : 'var(--text-secondary)' }}>
                                {item.wx} (☔{item.pop}%)
                              </span>
                            </div>
                            <div style={{
                              display: 'grid',
                              gridTemplateColumns: 'repeat(3, 1fr)',
                              gap: '4px',
                              fontSize: '11px',
                              marginTop: '6px',
                              color: 'var(--text-muted)'
                            }}>
                              <div>溫度: <b style={{ color: 'var(--text-primary)' }}>{item.temp}°C</b></div>
                              <div>體感: <b style={{ color: 'var(--text-primary)' }}>{item.apparent_temp}°C</b></div>
                              <div>濕度: <b>{item.rh}%</b></div>
                              <div style={{ gridColumn: 'span 2' }}>
                                風向: <b>{item.wind_dir}</b> ({item.wind_speed} m/s)
                                {isStrongWind && <span style={{ color: 'var(--color-danger)', marginLeft: '4px' }}>⚠️ 強風</span>}
                              </div>
                              <div>舒適: <b>{item.comfort}</b></div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </aside>
  );
}
