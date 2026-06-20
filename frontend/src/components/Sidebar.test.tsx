import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import Sidebar from './Sidebar';

describe('Sidebar Component', () => {
  const mockProps = {
    lat: 25.0338,
    lon: 121.5298,
    radius: 500,
    setRadius: jest.fn(),
    data: [],
    isLoading: false,
    error: null,
    selectedItem: null,
    onSelectItem: jest.fn(),
    onCoordinatesChange: jest.fn(),
    onSearchSubmit: jest.fn(),
    busDest: '',
    setBusDest: jest.fn(),
    busRoutes: [],
    isRoutingBus: false,
    onBusRouteSearch: jest.fn(),
    jpAreas: [],
    selectedJpArea: '',
    setSelectedJpArea: jest.fn(),
    jpRoutes: [],
    jpFromStation: '',
    setJpFromStation: jest.fn(),
    jpToStation: '',
    setJpToStation: jest.fn(),
    onJpRouteSearch: jest.fn(),
    isRoutingJp: false,
    placesType: '全部',
    setPlacesType: jest.fn()
  };

  beforeEach(() => {
    jest.spyOn(console, 'error').mockImplementation(() => {});
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  it('renders brand title and search input', () => {
    render(<Sidebar {...mockProps} mode="ubike" />);
    expect(screen.getByText('Hermes Go Dashboard')).toBeInTheDocument();
  });

  it('renders YouBike stations and triggers select click', () => {
    const mockUbikeData = [
      {
        uid: 'ubike-1',
        name: '捷運市政府站',
        address: '忠孝東路五段',
        capacity: 30,
        available_rent_bikes: 12,
        available_return_bikes: 18,
        service_status: 1
      }
    ];

    render(<Sidebar {...mockProps} mode="ubike" data={mockUbikeData} />);
    const card = screen.getByText('捷運市政府站');
    expect(card).toBeInTheDocument();
    
    fireEvent.click(card);
    expect(mockProps.onSelectItem).toHaveBeenCalledWith(mockUbikeData[0]);
  });

  it('triggers onSearchSubmit on search form submission', () => {
    render(<Sidebar {...mockProps} mode="ubike" />);
    
    const input = screen.getByPlaceholderText('搜尋經緯度, 地址或 Google Map...');
    const searchButton = screen.getByTitle('搜尋');
    
    fireEvent.change(input, { target: { value: 'Taipei 101' } });
    fireEvent.click(searchButton);
    
    expect(mockProps.onSearchSubmit).toHaveBeenCalledWith('Taipei 101');
  });

  it('renders radius slider and triggers onChange', () => {
    render(<Sidebar {...mockProps} mode="ubike" />);
    const slider = screen.getByRole('slider');
    expect(slider).toBeInTheDocument();
    
    fireEvent.change(slider, { target: { value: '1000' } });
    expect(mockProps.setRadius).toHaveBeenCalledWith(1000);
  });

  it('renders Bus nearby stops and ETAs', () => {
    const mockBusData = [
      {
        uid: 'bus-1',
        name: '台北車站',
        address: '忠孝西路',
        etas: [
          { route_name: '307', estimate_time: 120, status: 0 },
          { route_name: '299', estimate_time: 30, status: 0 }
        ]
      }
    ];

    render(<Sidebar {...mockProps} mode="twbus" data={mockBusData} />);
    expect(screen.getByText('🚌 台北車站')).toBeInTheDocument();
    expect(screen.getByText('307')).toBeInTheDocument();
    expect(screen.getByText('2 分鐘')).toBeInTheDocument();
    expect(screen.getByText('即將到站')).toBeInTheDocument();
  });

  it('renders Bus route planner and triggers route search', () => {
    const mockRoutes = [
      {
        route_name: '307',
        start_stop: '南京復興',
        dest_stop: '台北車站',
        stops_count: 5,
        direction: 0,
        eta: 180
      }
    ];

    const { rerender } = render(
      <Sidebar
        {...mockProps}
        mode="twbus"
        busDest=""
      />
    );
    
    // Switch to route planning mode (we simulate switch internally since submode is a state in Sidebar, we can click the chip)
    const routeChip = screen.getByText('直達路線規劃');
    fireEvent.click(routeChip);
    
    const input = screen.getByPlaceholderText('例如：台北車站、台北101');
    fireEvent.change(input, { target: { value: '台北車站' } });
    expect(mockProps.setBusDest).toHaveBeenCalledWith('台北車站');
    
    // Rerender with busDest prop populated to enable the plan button
    rerender(
      <Sidebar
        {...mockProps}
        mode="twbus"
        busDest="台北車站"
      />
    );
    
    const planButton = screen.getByText('開始規劃');
    fireEvent.click(planButton);
    expect(mockProps.onBusRouteSearch).toHaveBeenCalled();
    
    // Rerender with route data
    rerender(
      <Sidebar
        {...mockProps}
        mode="twbus"
        busDest="台北車站"
        busRoutes={mockRoutes}
      />
    );
    // Re-click chip to keep UI
    fireEvent.click(screen.getByText('直達路線規劃'));
    expect(screen.getByText('公車路線 307')).toBeInTheDocument();
    expect(screen.getByText(/3 分鐘/)).toBeInTheDocument();
  });

  it('renders Places and filters', () => {
    const mockPlacesData = [
      {
        uid: 'place-1',
        name: '鼎泰豐',
        vicinity: '信義路',
        rating: 4.6,
        user_ratings_total: 1200,
        open_now: true
      }
    ];

    render(<Sidebar {...mockProps} mode="places" data={mockPlacesData} />);
    expect(screen.getByText('鼎泰豐')).toBeInTheDocument();
    expect(screen.getByText(/4.6 \(1200 評價\)/)).toBeInTheDocument();
    expect(screen.getByText('營業中')).toBeInTheDocument();
    
    const cafeChip = screen.getByText('咖啡廳');
    fireEvent.click(cafeChip);
    expect(mockProps.setPlacesType).toHaveBeenCalledWith('咖啡廳');
  });

  it('renders Japan train status list and area options', () => {
    const mockAreas = [
      { code: '4', name: '関東', english: 'kanto' }
    ];
    
    const mockStatusData = [
      {
        company: 'JR東日本',
        name: '山手線',
        status: '正常營運',
        status_type: 'normal',
        detail_info: '無事故資訊',
        update_time: '11:00'
      }
    ];

    render(
      <Sidebar
        {...mockProps}
        mode="jptrain"
        jpAreas={mockAreas}
        selectedJpArea="4"
        data={mockStatusData}
      />
    );
    
    expect(screen.getByText(/山手線/)).toBeInTheDocument();
    expect(screen.getByText('正常營運')).toBeInTheDocument();
    expect(screen.getByText('JR東日本')).toBeInTheDocument();
    
    const select = screen.getByRole('combobox');
    fireEvent.change(select, { target: { value: '4' } });
    expect(mockProps.setSelectedJpArea).toHaveBeenCalledWith('4');
  });

  it('renders Japan train route search and triggers search', () => {
    const mockJpRoutes = [
      {
        time_required: '30',
        fare: '350',
        transfer_count: 0,
        steps: [
          { station_name: '東京', departure_time: '10:00', line_name: '山手線' }
        ]
      }
    ];

    const { rerender } = render(
      <Sidebar
        {...mockProps}
        mode="jptrain"
        jpFromStation="東京"
        jpToStation="新宿"
      />
    );
    
    const routeChip = screen.getByText('鐵道轉乘規劃');
    fireEvent.click(routeChip);
    
    const fromInput = screen.getByPlaceholderText('如：東京');
    fireEvent.change(fromInput, { target: { value: '大阪' } });
    expect(mockProps.setJpFromStation).toHaveBeenCalledWith('大阪');
    
    const toInput = screen.getByPlaceholderText('如：新宿');
    fireEvent.change(toInput, { target: { value: '京都' } });
    expect(mockProps.setJpToStation).toHaveBeenCalledWith('京都');
    
    const searchBtn = screen.getByText('開始規劃');
    fireEvent.click(searchBtn);
    expect(mockProps.onJpRouteSearch).toHaveBeenCalled();
    
    rerender(
      <Sidebar
        {...mockProps}
        mode="jptrain"
        jpFromStation="東京"
        jpToStation="新宿"
        jpRoutes={mockJpRoutes}
      />
    );
    fireEvent.click(screen.getByText('鐵道轉乘規劃'));
    expect(screen.getByText('時間: 30 分')).toBeInTheDocument();
    expect(screen.getByText(/350/)).toBeInTheDocument();
  });

  it('attempts browser location request', () => {
    const originalGeolocation = navigator.geolocation;
    
    const mockGeolocation = {
      getCurrentPosition: jest.fn().mockImplementationOnce((success) =>
        success({
          coords: {
            latitude: 25.0338,
            longitude: 121.5298
          }
        })
      )
    };
    
    // Assign mock geolocation
    Object.defineProperty(navigator, 'geolocation', {
      value: mockGeolocation,
      writable: true,
      configurable: true
    });

    render(<Sidebar {...mockProps} mode="ubike" />);
    
    const locationBtn = screen.getByTitle('使用我的目前位置');
    fireEvent.click(locationBtn);
    
    expect(mockGeolocation.getCurrentPosition).toHaveBeenCalled();
    expect(mockProps.onCoordinatesChange).toHaveBeenCalledWith(25.0338, 121.5298);
    
    // Restore original geolocation
    Object.defineProperty(navigator, 'geolocation', {
      value: originalGeolocation,
      writable: true,
      configurable: true
    });
  });

  it('covers geolocation browser not supported and error callbacks', () => {
    const originalGeolocation = navigator.geolocation;
    const alertMock = jest.fn();
    window.alert = alertMock;

    // 1. Browser not supported
    Object.defineProperty(navigator, 'geolocation', {
      value: undefined,
      configurable: true,
      writable: true
    });

    render(<Sidebar {...mockProps} mode="ubike" />);
    const locationBtn = screen.getByTitle('使用我的目前位置');
    fireEvent.click(locationBtn);
    expect(alertMock).toHaveBeenCalledWith('您的瀏覽器不支援定位功能。');

    // 2. Geolocation failure
    const mockGeolocationError = {
      getCurrentPosition: jest.fn().mockImplementationOnce((_success, error) =>
        error(new Error('Permission Denied'))
      )
    };
    Object.defineProperty(navigator, 'geolocation', {
      value: mockGeolocationError,
      configurable: true,
      writable: true
    });

    fireEvent.click(locationBtn);
    expect(alertMock).toHaveBeenCalledWith('無法取得您的位置，請確認定位權限。');

    // Restore original geolocation
    Object.defineProperty(navigator, 'geolocation', {
      value: originalGeolocation,
      configurable: true,
      writable: true
    });
  });

  it('covers clicks on bus chips, bus stops, places, and jp status chip', () => {
    // 1. Bus chips & bus stop select
    const mockBusData = [
      {
        uid: 'bus-1',
        name: '台北車站',
        address: '忠孝西路',
        etas: []
      }
    ];
    const { rerender } = render(<Sidebar {...mockProps} mode="twbus" data={mockBusData} />);
    
    // Switch to route planning first
    fireEvent.click(screen.getByText('直達路線規劃'));
    // Click back to nearby using the chip (covers line 229)
    fireEvent.click(screen.getByText('附近公車站牌'));

    // Click on bus stop card (covers line 265)
    fireEvent.click(screen.getByText('🚌 台北車站'));
    expect(mockProps.onSelectItem).toHaveBeenCalledWith(mockBusData[0]);

    // 2. Places card click (covers line 387) and rating fallback / open_now false
    const mockPlacesData = [
      {
        uid: 'place-1',
        name: '小店',
        vicinity: '小街',
        rating: 0,
        user_ratings_total: 0,
        open_now: false
      }
    ];
    rerender(<Sidebar {...mockProps} mode="places" data={mockPlacesData} />);
    fireEvent.click(screen.getByText('小店'));
    expect(mockProps.onSelectItem).toHaveBeenCalledWith(mockPlacesData[0]);
    expect(screen.getByText('暫無評價')).toBeInTheDocument();
    expect(screen.getByText('休息中')).toBeInTheDocument();

    // 3. JP Train submode chip click (covers line 415)
    rerender(<Sidebar {...mockProps} mode="jptrain" />);
    // Switch to route first
    fireEvent.click(screen.getByText('鐵道轉乘規劃'));
    // Click back to status (covers line 415)
    fireEvent.click(screen.getByText('運行警報概況'));
  });

  it('covers empty search text submission early return', () => {
    (mockProps.onSearchSubmit as jest.Mock).mockClear();
    render(<Sidebar {...mockProps} mode="ubike" />);
    const input = screen.getByPlaceholderText('搜尋經緯度, 地址或 Google Map...');
    const searchButton = screen.getByTitle('搜尋');
    
    // Type empty search
    fireEvent.change(input, { target: { value: '   ' } });
    fireEvent.click(searchButton);
    expect(mockProps.onSearchSubmit).not.toHaveBeenCalled();
  });

  it('covers active locating state visual rendering', () => {
    const originalGeolocation = navigator.geolocation;
    const mockGeolocationLoading = {
      getCurrentPosition: jest.fn()
    };
    Object.defineProperty(navigator, 'geolocation', {
      value: mockGeolocationLoading,
      writable: true,
      configurable: true
    });

    render(<Sidebar {...mockProps} mode="ubike" />);
    const locationBtn = screen.getByTitle('使用我的目前位置');
    fireEvent.click(locationBtn);

    expect(screen.getByText('⌛')).toBeInTheDocument();

    Object.defineProperty(navigator, 'geolocation', {
      value: originalGeolocation,
      writable: true,
      configurable: true
    });
  });

  it('covers YouBike card with suspended status', () => {
    const mockUbikeData = [
      {
        uid: 'ubike-1',
        name: '捷運市政府站',
        address: '忠孝東路五段',
        capacity: 30,
        available_rent_bikes: 0,
        available_return_bikes: 30,
        service_status: 0
      }
    ];

    const nonMatchingItem = { uid: 'other-uid' };
    render(<Sidebar {...mockProps} mode="ubike" data={mockUbikeData} selectedItem={nonMatchingItem} />);
    expect(screen.getByText(/暫停營運/)).toBeInTheDocument();
  });

  it('covers bus stop card with missing address, and selected card rendering', () => {
    const mockBusData = [
      {
        uid: 'bus-1',
        name: '台北車站',
        address: '', // empty address
        etas: []
      }
    ];

    render(<Sidebar {...mockProps} mode="twbus" data={mockBusData} selectedItem={mockBusData[0]} />);
    expect(screen.getByText('無地址資訊')).toBeInTheDocument();
  });

  it('covers Places mode error message, empty data state, and selected place card rendering', () => {
    const { rerender } = render(<Sidebar {...mockProps} mode="places" error="美食 API 錯誤" />);
    expect(screen.getByText('美食 API 錯誤')).toBeInTheDocument();

    rerender(<Sidebar {...mockProps} mode="places" data={[]} />);
    expect(screen.getByText('此範圍內查無美食景點。')).toBeInTheDocument();

    const mockPlacesData = [
      {
        uid: 'place-1',
        name: '大店',
        vicinity: '大路',
        rating: 5,
        user_ratings_total: 10,
        open_now: true
      }
    ];
    rerender(<Sidebar {...mockProps} mode="places" data={mockPlacesData} selectedItem={mockPlacesData[0]} />);
  });

  it('covers Japan Train route planning fallback details and empty routes state', () => {
    const mockJpRoutes = [
      {
        time_required: '', // empty
        fare: '', // empty
        transfer_count: null, // null
        steps: [
          { station_name: '東京' }
        ]
      }
    ];

    const { rerender } = render(
      <Sidebar
        {...mockProps}
        mode="jptrain"
        jpFromStation="東京"
        jpToStation="新宿"
        jpRoutes={mockJpRoutes}
      />
    );
    
    fireEvent.click(screen.getByText('鐵道轉乘規劃'));
    
    expect(screen.getAllByText(/時間: 未知 分/).length).toBeGreaterThan(0);
    expect(screen.getByText(/票價:/).textContent).toContain('未知 日圓');
    expect(screen.getByText(/轉乘次數:/).textContent).toContain('0 次');
    
    rerender(
      <Sidebar
        {...mockProps}
        mode="jptrain"
        jpFromStation="東京"
        jpToStation="新宿"
        jpRoutes={[]}
      />
    );
    fireEvent.click(screen.getByText('鐵道轉乘規劃'));
    expect(screen.getByText('沒有找到乘車路線方案。')).toBeInTheDocument();
  });
});
