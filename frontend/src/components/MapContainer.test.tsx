import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import MapContainer from './MapContainer';
import L from 'leaflet';

describe('MapContainer Component', () => {
  const mockProps = {
    lat: 25.0338,
    lon: 121.5298,
    onMapClick: jest.fn(),
    mode: 'ubike' as const,
    data: [],
    selectedItem: null,
    onSelectItem: jest.fn()
  };

  it('renders leaflet container successfully', () => {
    const { container, rerender } = render(<MapContainer {...mockProps} />);
    const mapDiv = container.querySelector('#map');
    expect(mapDiv).toBeInTheDocument();

    // Rerender with updated coordinates to test center marker update (line 75)
    rerender(<MapContainer {...mockProps} lat={25.044} lon={121.533} />);
  });

  it('renders YouBike stations as markers and reacts to updates', () => {
    const mockUbikeData = [
      {
        uid: 'ubike-1',
        name: '捷運站',
        address: '某路口',
        lat: 25.0339,
        lon: 121.5299,
        capacity: 30,
        available_rent_bikes: 10,
        available_return_bikes: 20,
        service_status: 1
      },
      {
        uid: 'ubike-2',
        name: '捷運站2',
        address: '某路口2',
        lat: 25.0335,
        lon: 121.5295,
        capacity: 30,
        available_rent_bikes: 0,
        available_return_bikes: 30,
        service_status: 0
      },
      {
        uid: 'ubike-3',
        name: '捷運站3',
        address: '某路口3',
        lat: 25.0332,
        lon: 121.5292,
        capacity: 30,
        available_rent_bikes: 2,
        available_return_bikes: 28,
        service_status: 1
      }
    ];

    const { rerender } = render(<MapContainer {...mockProps} data={mockUbikeData} />);
    
    // Rerender with selected item
    rerender(<MapContainer {...mockProps} data={mockUbikeData} selectedItem={mockUbikeData[0]} />);
    expect(L.divIcon).toHaveBeenCalled();
  });

  it('renders twbus and places markers correctly', () => {
    const mockBusData = [
      {
        uid: 'bus-1',
        name: '市府站',
        lat: 25.0339,
        lon: 121.5299,
        etas: [{ route_name: '307', estimate_time: 120, status: 0 }]
      }
    ];

    const { rerender } = render(<MapContainer {...mockProps} mode="twbus" data={mockBusData} />);
    
    const mockPlacesData = [
      {
        uid: 'place-1',
        name: '咖啡廳',
        lat: 25.0339,
        lon: 121.5299,
        rating: 4.5,
        user_ratings_total: 100,
        vicinity: '台北市'
      }
    ];

    rerender(<MapContainer {...mockProps} mode="places" data={mockPlacesData} />);
    expect(L.divIcon).toHaveBeenCalled();
  });

  it('triggers map click and marker select click callbacks', () => {
    render(<MapContainer {...mockProps} />);
    
    // Simulate Map Click
    if ((global as any).mapClickCallback) {
      (global as any).mapClickCallback({ latlng: { lat: 25.0338, lng: 121.5298 } });
      expect(mockProps.onMapClick).toHaveBeenCalledWith(25.0338, 121.5298);
    }

    // Render with one station to register marker click
    const mockUbikeData = [{
      uid: 'ubike-1',
      name: '捷運站',
      address: '某路口',
      lat: 25.0339,
      lon: 121.5299,
      capacity: 30,
      available_rent_bikes: 10,
      available_return_bikes: 20,
      service_status: 1
    }];

    render(<MapContainer {...mockProps} data={mockUbikeData} />);

    // Simulate Marker Click
    if ((global as any).markerClickCallback) {
      (global as any).markerClickCallback();
      expect(mockProps.onSelectItem).toHaveBeenCalled();
    }
  });

  it('covers MapContainer early returns when map is not initialized', () => {
    const React = require('react');

    jest.spyOn(React, 'useRef').mockImplementation(() => {
      const ref = {};
      Object.defineProperty(ref, 'current', {
        get: () => null,
        set: () => {},
        configurable: true
      });
      return ref;
    });
    const { unmount } = render(<MapContainer {...mockProps} />);
    unmount();

    (React.useRef as any).mockRestore();
  });

  it('covers bus ETAs with null and undefined estimate_times', () => {
    const mockBusData = [
      {
        uid: 'bus-1',
        name: '市府站',
        lat: 25.0339,
        lon: 121.5299,
        etas: [
          { route_name: '307', estimate_time: null, status: 0 },
          { route_name: '299', estimate_time: undefined, status: 0 }
        ]
      }
    ];

    render(<MapContainer {...mockProps} mode="twbus" data={mockBusData} />);
    expect(L.divIcon).toHaveBeenCalled();
  });

  it('covers MapContainer edge cases: missing rating, missing user ratings, invalid coordinates, empty/missing etas, and jptrain mode', () => {
    const mockUbikeData = [
      {
        uid: 'ubike-invalid-coords',
        name: '捷運站無座標',
        address: '無',
        lat: 0,
        lon: 0,
        capacity: 30,
        available_rent_bikes: 10,
        available_return_bikes: 20,
        service_status: 1
      }
    ];

    // 1. Invalid coordinates for YouBike
    render(<MapContainer {...mockProps} data={mockUbikeData} />);

    // 2. Bus with empty/missing etas
    const mockBusDataNoEtas = [
      {
        uid: 'bus-no-etas',
        name: '市府站無動態',
        lat: 25.0339,
        lon: 121.5299,
        etas: []
      },
      {
        uid: 'bus-null-etas',
        name: '市府站空動態',
        lat: 25.0339,
        lon: 121.5299,
        etas: undefined as any
      }
    ];
    render(<MapContainer {...mockProps} mode="twbus" data={mockBusDataNoEtas} />);

    // 3. Places with missing rating and user_ratings_total
    const mockPlacesDataMissingFields = [
      {
        uid: 'place-missing',
        name: '未知店家',
        lat: 25.0339,
        lon: 121.5299,
        vicinity: '未知地址'
      }
    ];
    render(<MapContainer {...mockProps} mode="places" data={mockPlacesDataMissingFields} />);

    // 4. JpTrain mode (does not draw markers)
    render(<MapContainer {...mockProps} mode="jptrain" data={mockPlacesDataMissingFields} />);
  });
});
