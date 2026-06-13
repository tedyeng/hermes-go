import pytest
from unittest.mock import patch, MagicMock
from ubike import api
from ubike import cli

# Mock data for YouBike APIs
MOCK_BIKE_STATIONS = [
    {
        "StationUID": "TPE500101",
        "StationID": "500101001",
        "StationName": {"Zh_tw": "捷運科技大樓站", "En": "MRT Technology Building Station"},
        "StationPosition": {"PositionLat": 25.02605, "PositionLon": 121.5436},
        "StationAddress": {"Zh_tw": "復興南路二段235號前", "En": "No. 235, Sec. 2, Fuxing S. Rd."},
        "BikesCapacity": 30,
        "ServiceType": 2, # YouBike 2.0
        "UpdateTime": "2026-06-13T09:00:00+08:00"
    },
    {
        "StationUID": "TPE500102",
        "StationID": "500101002",
        "StationName": {"Zh_tw": "科技大樓站前", "En": "Technology Building Sta."},
        "StationPosition": {"PositionLat": 25.0268, "PositionLon": 121.5438},
        "StationAddress": {"Zh_tw": "和平東路二段與復興南路口", "En": "Heping E. Rd. & Fuxing S. Rd."},
        "BikesCapacity": 25,
        "ServiceType": 2, # YouBike 2.0
        "UpdateTime": "2026-06-13T09:00:00+08:00"
    }
]

MOCK_BIKE_AVAILABILITY = [
    {
        "StationUID": "TPE500101",
        "AvailableRentBikes": 12,
        "AvailableReturnBikes": 18,
        "ServiceStatus": 1, # Normal
        "SrcUpdateTime": "2026-06-13T09:24:00+08:00",
        "UpdateTime": "2026-06-13T09:24:30+08:00"
    },
    {
        "StationUID": "TPE500102",
        "AvailableRentBikes": 0,
        "AvailableReturnBikes": 25,
        "ServiceStatus": 2, # Suspended
        "SrcUpdateTime": "2026-06-13T09:22:00+08:00",
        "UpdateTime": "2026-06-13T09:23:00+08:00"
    }
]

def test_parse_gps_input_raw_decimals():
    # Standard format
    res = api.parse_gps_input("25.033964, 121.564468")
    assert res is not None
    assert abs(res[0] - 25.033964) < 1e-6
    assert abs(res[1] - 121.564468) < 1e-6

    # Text surrounding coordinates
    res2 = api.parse_gps_input("My Location: (25.0339, 121.5644)")
    assert res2 is not None
    assert abs(res2[0] - 25.0339) < 1e-6
    assert abs(res2[1] - 121.5644) < 1e-6

    # Swapped lat/lon correction (Taiwan longitude is > 110, latitude is ~25)
    res3 = api.parse_gps_input("121.564468, 25.033964")
    assert res3 is not None
    assert abs(res3[0] - 25.033964) < 1e-6
    assert abs(res3[1] - 121.564468) < 1e-6

def test_parse_gps_input_urls():
    # Google Maps query URL
    res = api.parse_gps_input("https://www.google.com/maps/search/?api=1&query=25.033964,121.564468")
    assert res == (25.033964, 121.564468)

    # Google Maps place URL
    res2 = api.parse_gps_input("https://www.google.com/maps/place/25.02605,121.5436/data=!3m1!4b1")
    assert res2 == (25.02605, 121.5436)

    # Google Maps path @ coordinate
    res3 = api.parse_gps_input("https://www.google.com/maps/@25.0336,121.5644,17z")
    assert res3 == (25.0336, 121.5644)

    # Apple Maps URL should be ignored
    res4 = api.parse_gps_input("https://maps.apple.com/?q=25.033,-121.564")
    assert res4 is None

    # Telegram style URL
    res5 = api.parse_gps_input("https://maps.google.com/maps?q=25.033,121.564&ll=25.033,121.564")
    assert res5 == (25.033, 121.564)

@patch("ubike.api.requests.head")
def test_parse_gps_input_short_url(mock_head):
    # Mock redirect resolution
    mock_resp = MagicMock()
    mock_resp.url = "https://www.google.com/maps/place/25.02605,121.5436/"
    mock_head.return_value = mock_resp

    res = api.parse_gps_input("https://maps.app.goo.gl/abcd")
    mock_head.assert_called_once_with("https://maps.app.goo.gl/abcd", allow_redirects=True, timeout=3)
    assert res == (25.02605, 121.5436)

def test_parse_gps_input_dms():
    res = api.parse_gps_input("北緯25°5′0″ 東經121°34′43″")
    assert res is not None
    assert abs(res[0] - 25.083333333333332) < 1e-5
    assert abs(res[1] - 121.5786111111111) < 1e-5

def test_calculate_distance():
    # Test distance between Taipei 101 (25.033964, 121.564468) and Taipei Station (25.047675, 121.517055)
    # Proximity is roughly ~4.9 km (4900 meters)
    dist = cli.calculate_distance(25.033964, 121.564468, 25.047675, 121.517055)
    assert 4700 <= dist <= 5100

@patch("ubike.api.requests.get")
def test_get_nearby_stations(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_BIKE_STATIONS
    mock_get.return_value = mock_resp

    res = api.get_nearby_stations("mock_token", 25.026, 121.543, 500)
    assert len(res) == 2
    assert res[0]["StationUID"] == "TPE500101"
    assert res[1]["StationName"]["Zh_tw"] == "科技大樓站前"
    
    # Assert parameters
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert "v2/Bike/Station/NearBy" in args[0]
    assert kwargs["params"]["$spatialFilter"] == "nearby(25.026, 121.543, 500)"

@patch("ubike.api.requests.get")
def test_get_nearby_availability(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_BIKE_AVAILABILITY
    mock_get.return_value = mock_resp

    res = api.get_nearby_availability("mock_token", 25.026, 121.543, 500)
    assert len(res) == 2
    assert res[0]["StationUID"] == "TPE500101"
    assert res[0]["AvailableRentBikes"] == 12
    assert res[1]["ServiceStatus"] == 2
