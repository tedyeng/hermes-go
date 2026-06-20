import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import App from './App';

describe('App Main Component', () => {
  let fetchMock: jest.Mock;

  beforeEach(() => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
    // Mock global fetch
    fetchMock = jest.fn().mockImplementation((url: string) => {
      if (url.includes('/api/jptrain/areas')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            data: [{ code: '4', name: '関東', english: 'kanto' }]
          })
        });
      }
      
      if (url.includes('/api/ubike/nearby')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            data: [
              {
                uid: 'ubike-1',
                name: '捷運市政府站',
                address: '某路口',
                capacity: 30,
                available_rent_bikes: 15,
                available_return_bikes: 15,
                service_status: 1
              }
            ]
          })
        });
      }

      if (url.includes('/api/twbus/nearby')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            data: [
              {
                uid: 'bus-1',
                name: '市府公車站',
                lat: 25.0338,
                lon: 121.5298,
                etas: []
              }
            ]
          })
        });
      }

      if (url.includes('/api/places/nearby')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            data: [
              {
                uid: 'place-1',
                name: '咖啡館',
                vicinity: '忠孝東路',
                rating: 4.5
              }
            ]
          })
        });
      }

      if (url.includes('/api/jptrain/status')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            data: [
              {
                name: '山手線',
                company: 'JR東日本',
                status: '正常營運',
                status_type: 'normal'
              }
            ]
          })
        });
      }

      if (url.includes('/api/utils/parse-gps')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            lat: 25.0338,
            lon: 121.5644
          })
        });
      }

      if (url.includes('/api/twbus/route')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            dest_coords: { lat: 25.04, lon: 121.51 },
            data: [
              {
                route_name: '307',
                start_stop: '南京復興',
                dest_stop: '台北車站',
                stops_count: 5,
                eta: 180
              }
            ]
          })
        });
      }

      if (url.includes('/api/jptrain/route')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            data: [
              {
                time_required: '14',
                fare: '253',
                transfer_count: 0,
                steps: [
                  { station_name: '東京', departure_time: '11:00發', line_name: '山手線' }
                ]
              }
            ]
          })
        });
      }

      return Promise.reject(new Error('Unknown url requested'));
    });

    global.fetch = fetchMock as any;
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders dashboard with default YouBike mode and fetches data', async () => {
    render(<App />);
    
    // Check loading areas
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/jptrain/areas'));
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/ubike/nearby'));
    });

    // Check YouBike station is displayed
    expect(await screen.findByText('捷運市政府站')).toBeInTheDocument();
  });

  it('supports switching tabs and fetches corresponding data', async () => {
    render(<App />);
    
    // 1. Switch to Taiwan Bus ETA
    const busTab = screen.getByText('🚌 台灣公車 ETA');
    fireEvent.click(busTab);
    
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/twbus/nearby'));
    });
    expect(await screen.findByText('🚌 市府公車站')).toBeInTheDocument();

    // 2. Switch to Places
    const placesTab = screen.getByText('🗺️ 景點美食');
    fireEvent.click(placesTab);
    
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/places/nearby'));
    });
    expect(await screen.findByText('咖啡館')).toBeInTheDocument();

    // 3. Switch to Japan Train
    const jpTab = screen.getByText('🚄 日本鐵道');
    fireEvent.click(jpTab);
    
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/jptrain/status'));
    });
    expect(await screen.findByText(/山手線/)).toBeInTheDocument();
  });

  it('supports address GPS parsing search', async () => {
    render(<App />);
    
    const input = screen.getByPlaceholderText('搜尋經緯度, 地址或 Google Map...');
    const searchBtn = screen.getByTitle('搜尋');
    
    fireEvent.change(input, { target: { value: '台北101' } });
    fireEvent.click(searchBtn);
    
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/utils/parse-gps'), expect.any(Object));
    });
  });

  it('triggers Bus route planning and sets state', async () => {
    render(<App />);
    
    // Switch to Bus
    fireEvent.click(screen.getByText('🚌 台灣公車 ETA'));
    
    // Switch to route submode inside sidebar
    const routeChip = await screen.findByText('直達路線規劃');
    fireEvent.click(routeChip);
    
    const destInput = screen.getByPlaceholderText('例如：台北車站、台北101');
    fireEvent.change(destInput, { target: { value: '台北車站' } });
    
    const planBtn = screen.getByText('開始規劃');
    fireEvent.click(planBtn);
    
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/twbus/route'));
    });
    
    expect(await screen.findByText('公車路線 307')).toBeInTheDocument();
  });

  it('triggers Japan train route planning and sets state', async () => {
    render(<App />);
    
    // Switch to Japan Train
    fireEvent.click(screen.getByText('🚄 日本鐵道'));
    
    // Switch to route submode inside sidebar
    const routeChip = await screen.findByText('鐵道轉乘規劃');
    fireEvent.click(routeChip);
    
    const fromInput = screen.getByPlaceholderText('如：東京');
    const toInput = screen.getByPlaceholderText('如：新宿');
    
    fireEvent.change(fromInput, { target: { value: '東京' } });
    fireEvent.change(toInput, { target: { value: '新宿' } });
    
    const planBtn = screen.getByText('開始規劃');
    fireEvent.click(planBtn);
    
    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('/api/jptrain/route'));
    });
    
    expect(await screen.findByText('時間: 14 分')).toBeInTheDocument();
  });

  it('handles API fetch error catches and alert box alerts', async () => {
    // Override fetchMock to simulate connection error reject
    fetchMock = jest.fn().mockImplementation(() => Promise.reject(new Error('Network error')));
    global.fetch = fetchMock as any;

    const alertMock = jest.fn();
    window.alert = alertMock;

    render(<App />);

    // 1. Trigger GPS parse search failure
    const input = screen.getByPlaceholderText('搜尋經緯度, 地址或 Google Map...');
    const searchBtn = screen.getByTitle('搜尋');
    fireEvent.change(input, { target: { value: 'invalid address' } });
    fireEvent.click(searchBtn);
    await waitFor(() => expect(alertMock).toHaveBeenCalled());

    // 2. Trigger Bus route search failure
    fireEvent.click(screen.getByText('🚌 台灣公車 ETA'));
    const routeChip = await screen.findByText('直達路線規劃');
    fireEvent.click(routeChip);
    const destInput = screen.getByPlaceholderText('例如：台北車站、台北101');
    fireEvent.change(destInput, { target: { value: '台北' } });
    const planBtn = screen.getByText('開始規劃');
    fireEvent.click(planBtn);
    await waitFor(() => expect(alertMock).toHaveBeenCalled());

    // 3. Trigger Japan Train route search failure
    fireEvent.click(screen.getByText('🚄 日本鐵道'));
    const jpRouteChip = await screen.findByText('鐵道轉乘規劃');
    fireEvent.click(jpRouteChip);
    const fromInput = screen.getByPlaceholderText('如：東京');
    const toInput = screen.getByPlaceholderText('如：新宿');
    fireEvent.change(fromInput, { target: { value: '東京' } });
    fireEvent.change(toInput, { target: { value: '新宿' } });
    const jpPlanBtn = screen.getByText('開始規劃');
    fireEvent.click(jpPlanBtn);
    await waitFor(() => expect(alertMock).toHaveBeenCalled());
  });

  it('covers getApiUrl production env port mapping', async () => {
    (window as any).__MOCK_HOSTNAME__ = 'example.com';
    (window as any).__MOCK_PORT__ = '80';

    render(<App />);

    // Wait for rendering to settle to avoid async leaks
    expect(await screen.findByText('捷運市政府站')).toBeInTheDocument();

    // Restore
    delete (window as any).__MOCK_HOSTNAME__;
    delete (window as any).__MOCK_PORT__;
  });

  it('covers getApiUrl dev env port mapping (line 14)', async () => {
    (window as any).__MOCK_HOSTNAME__ = 'localhost';
    (window as any).__MOCK_PORT__ = '5173';

    render(<App />);

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(expect.stringContaining('http://localhost:8000/api/jptrain/areas'));
    });

    // Restore
    delete (window as any).__MOCK_HOSTNAME__;
    delete (window as any).__MOCK_PORT__;
  });

  it('covers fetchData with server ok false or status failure', async () => {
    fetchMock = jest.fn().mockImplementation(() => Promise.resolve({
      ok: false,
      status: 500,
      json: () => Promise.resolve({ message: 'Internal Server Error' })
    }));
    global.fetch = fetchMock as any;

    render(<App />);
    expect(await screen.findByText(/伺服器連線失敗/)).toBeInTheDocument();
  });

  it('covers fetchData with success false / status failure', async () => {
    fetchMock = jest.fn().mockImplementation((url: string) => {
      if (url.includes('/api/jptrain/areas')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: 'success', data: [] })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'error', message: 'Custom API Error' })
      });
    });
    global.fetch = fetchMock as any;

    render(<App />);
    expect(await screen.findByText('Custom API Error')).toBeInTheDocument();
  });

  it('covers fetchJpStatus failure scenarios - status error', async () => {
    fetchMock = jest.fn().mockImplementation((url: string) => {
      if (url.includes('/api/jptrain/areas')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            data: [{ code: '4', name: '関東' }]
          })
        });
      }
      if (url.includes('/api/jptrain/status')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: 'error' })
        });
      }
      return Promise.reject(new Error('Unknown url'));
    });
    global.fetch = fetchMock as any;

    render(<App />);
    fireEvent.click(screen.getByText('🚄 日本鐵道'));
    expect(await screen.findByText('無法獲取鐵路運行狀態')).toBeInTheDocument();
  });

  it('covers fetchJpStatus failure scenarios - network error', async () => {
    fetchMock = jest.fn().mockImplementation((url: string) => {
      if (url.includes('/api/jptrain/areas')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            data: [{ code: '4', name: '関東' }]
          })
        });
      }
      return Promise.reject(new Error('Network error'));
    });
    global.fetch = fetchMock as any;

    render(<App />);
    fireEvent.click(screen.getByText('🚄 日本鐵道'));
    expect(await screen.findByText('連線至後端失敗')).toBeInTheDocument();
  });

  it('covers API success resolves with status error alerts', async () => {
    fetchMock = jest.fn().mockImplementation((url: string) => {
      if (url.includes('/api/jptrain/areas')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            data: [{ code: '4', name: '関東' }]
          })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'error', message: 'Resolved Status Error' })
      });
    });
    global.fetch = fetchMock as any;

    const alertMock = jest.fn();
    window.alert = alertMock;

    render(<App />);

    const input = screen.getByPlaceholderText('搜尋經緯度, 地址或 Google Map...');
    const searchBtn = screen.getByTitle('搜尋');
    fireEvent.change(input, { target: { value: 'invalid address' } });
    fireEvent.click(searchBtn);
    await waitFor(() => expect(alertMock).toHaveBeenCalledWith('Resolved Status Error'));

    fireEvent.click(screen.getByText('🚌 台灣公車 ETA'));
    const routeChip = await screen.findByText('直達路線規劃');
    fireEvent.click(routeChip);
    const destInput = screen.getByPlaceholderText('例如：台北車站、台北101');
    fireEvent.change(destInput, { target: { value: '台北' } });
    const planBtn = screen.getByText('開始規劃');
    fireEvent.click(planBtn);
    await waitFor(() => expect(alertMock).toHaveBeenCalledWith('Resolved Status Error'));

    fireEvent.click(screen.getByText('🚄 日本鐵道'));
    const jpRouteChip = await screen.findByText('鐵道轉乘規劃');
    fireEvent.click(jpRouteChip);
    const fromInput = screen.getByPlaceholderText('如：東京');
    const toInput = screen.getByPlaceholderText('如：新宿');
    fireEvent.change(fromInput, { target: { value: '東京' } });
    fireEvent.change(toInput, { target: { value: '新宿' } });
    const jpPlanBtn = screen.getByText('開始規劃');
    fireEvent.click(jpPlanBtn);
    await waitFor(() => expect(alertMock).toHaveBeenCalledWith('Resolved Status Error'));
  });

  it('triggers map click and marker select callbacks on App level', async () => {
    const mockUbikeData = [
      {
        uid: 'ubike-1',
        name: '捷運市政府站',
        address: '某路口',
        capacity: 30,
        available_rent_bikes: 15,
        available_return_bikes: 15,
        service_status: 1,
        lat: 25.0338,
        lon: 121.5298
      }
    ];

    fetchMock = jest.fn().mockImplementation((url: string) => {
      if (url.includes('/api/jptrain/areas')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: 'success', data: [] })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'success', data: mockUbikeData })
      });
    });
    global.fetch = fetchMock as any;

    render(<App />);

    if ((global as any).mapClickCallback) {
      act(() => {
        (global as any).mapClickCallback({ latlng: { lat: 25.044, lng: 121.533 } });
      });
    }

    if ((global as any).markerClickCallback) {
      act(() => {
        (global as any).markerClickCallback();
      });
    }
    
    const card = await screen.findByText('捷運市政府站');
    expect(card).toBeInTheDocument();
    fireEvent.click(card);
  });

  it('covers all callback triggers on App level to achieve 100% coverage', async () => {
    render(<App />);

    // 1. YouBike tab click (switches back to ubike if we switch to bus first)
    fireEvent.click(screen.getByText('🚌 台灣公車 ETA'));
    fireEvent.click(screen.getByText('🚲 YouBike 車位'));

    // 2. setRadius callback
    const slider = screen.getByRole('slider');
    fireEvent.change(slider, { target: { value: '1000' } });

    // 3. setPlacesType callback
    fireEvent.click(screen.getByText('🗺️ 景點美食'));
    const cafeChip = await screen.findByText('咖啡廳');
    fireEvent.click(cafeChip);

    // 4. setSelectedJpArea callback
    fireEvent.click(screen.getByText('🚄 日本鐵道'));
    const select = await screen.findByRole('combobox');
    fireEvent.change(select, { target: { value: '4' } });

    // 5. setBusDest callback
    fireEvent.click(screen.getByText('🚌 台灣公車 ETA'));
    const routeChip = await screen.findByText('直達路線規劃');
    fireEvent.click(routeChip);
    const busInput = screen.getByPlaceholderText('例如：台北車站、台北101');
    fireEvent.change(busInput, { target: { value: '松山機場' } });

    // 6. setJpFromStation and setJpToStation callbacks
    fireEvent.click(screen.getByText('🚄 日本鐵道'));
    const jpRouteChip = await screen.findByText('鐵道轉乘規劃');
    fireEvent.click(jpRouteChip);
    const fromInput = screen.getByPlaceholderText('如：東京');
    const toInput = screen.getByPlaceholderText('如：新宿');
    fireEvent.change(fromInput, { target: { value: '東京' } });
    fireEvent.change(toInput, { target: { value: '新宿' } });

    // 7. onCoordinatesChange callback (simulate geolocation success)
    const originalGeolocation = navigator.geolocation;
    const mockGeolocation = {
      getCurrentPosition: jest.fn().mockImplementationOnce((success) =>
        success({ coords: { latitude: 25.033, longitude: 121.52 } })
      )
    };
    Object.defineProperty(navigator, 'geolocation', {
      value: mockGeolocation,
      writable: true,
      configurable: true
    });
    const locBtn = screen.getByTitle('使用我的目前位置');
    fireEvent.click(locBtn);

    // Wait for coordinate display to update to ensure state updates and re-renders settle
    expect(await screen.findByText(/25.0330/)).toBeInTheDocument();
    
    // Restore
    Object.defineProperty(navigator, 'geolocation', {
      value: originalGeolocation,
      writable: true,
      configurable: true
    });
  });

  it('covers App error fallbacks, empty inputs, dest_coords, and empty area selections', async () => {
    fetchMock = jest.fn().mockImplementation((url: string) => {
      if (url.includes('/api/jptrain/areas')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'success',
            data: [{ code: '4', name: '関東' }]
          })
        });
      }
      if (url.includes('/api/twbus/route')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({
            status: 'error'
          })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'error' })
      });
    });
    global.fetch = fetchMock as any;

    const alertMock = jest.fn();
    window.alert = alertMock;

    render(<App />);

    const input = screen.getByPlaceholderText('搜尋經緯度, 地址或 Google Map...');
    const searchBtn = screen.getByTitle('搜尋');
    fireEvent.change(input, { target: { value: 'invalid address' } });
    fireEvent.click(searchBtn);
    await waitFor(() => expect(alertMock).toHaveBeenCalledWith('無法解析輸入的經緯度或地址'));

    fireEvent.click(screen.getByText('🚌 台灣公車 ETA'));
    const routeChip = await screen.findByText('直達路線規劃');
    fireEvent.click(routeChip);
    
    const planBtn = screen.getByText('開始規劃');
    planBtn.removeAttribute('disabled');
    fireEvent.click(planBtn);

    const destInput = screen.getByPlaceholderText('例如：台北車站、台北101');
    fireEvent.change(destInput, { target: { value: '台北' } });
    const planBtnActive = screen.getByText('開始規劃');
    fireEvent.click(planBtnActive);
    await waitFor(() => expect(alertMock).toHaveBeenCalledWith('搜尋路線失敗'));

    fireEvent.click(screen.getByText('🚄 日本鐵道'));
    const jpRouteChip = await screen.findByText('鐵道轉乘規劃');
    fireEvent.click(jpRouteChip);
    
    const jpPlanBtn = screen.getByText('開始規劃');
    jpPlanBtn.removeAttribute('disabled');
    fireEvent.click(jpPlanBtn);

    const fromInput = screen.getByPlaceholderText('如：東京');
    const toInput = screen.getByPlaceholderText('如：新宿');
    fireEvent.change(fromInput, { target: { value: '東京' } });
    fireEvent.change(toInput, { target: { value: '新宿' } });
    const jpPlanBtnActive = screen.getByText('開始規劃');
    fireEvent.click(jpPlanBtnActive);
    await waitFor(() => expect(alertMock).toHaveBeenCalledWith('查詢路線失敗'));

    const statusChip = screen.getByText('運行警報概況');
    fireEvent.click(statusChip);
    const select = await screen.findByRole('combobox');
    fireEvent.change(select, { target: { value: '' } });

    fetchMock = jest.fn().mockImplementation((url: string) => {
      if (url.includes('/api/jptrain/areas')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve({ status: 'success', data: [] })
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'error' })
      });
    });
    global.fetch = fetchMock as any;
    render(<App />);
    expect(await screen.findByText('查詢時發生未知錯誤。')).toBeInTheDocument();

    fetchMock = jest.fn().mockImplementation(() => Promise.reject({}));
    global.fetch = fetchMock as any;
    render(<App />);
    expect(await screen.findByText('無法連線至 Hermes API 後端。請確認後端是否正在運作。')).toBeInTheDocument();
  });
});
