import pytest
from unittest.mock import patch, MagicMock
from twbus import api

# Mock Data
MOCK_TOKEN_RESPONSE = {
    "access_token": "mock_access_token_12345",
    "expires_in": 3600
}

MOCK_NOMINATIM_RESPONSE = [
    {
        "lat": "25.033964",
        "lon": "121.564468",
        "display_name": "台北101, 信義路五段, 信義區, 台北市, 110, 臺灣"
    }
]

MOCK_NEARBY_STOPS_START = [
    {
        "StopUID": "TPE10001",
        "StopID": "10001",
        "StopName": {"Zh_tw": "捷運動門站", "En": "MRT Dongmen Station"},
        "RouteUID": "TPE12345",
        "RouteID": "12345",
        "RouteName": {"Zh_tw": "信義幹線", "En": "Xinyi Main Line"},
        "Direction": 0,
        "StopPosition": {"PositionLat": 25.0338, "PositionLon": 121.5298},
        "LocationCityCode": "TPE"
    },
    {
        "StopUID": "TPE10002",
        "StopID": "10002",
        "StopName": {"Zh_tw": "捷運動門站", "En": "MRT Dongmen Station"},
        "RouteUID": "TPE54321",
        "RouteID": "54321",
        "RouteName": {"Zh_tw": "20", "En": "20"},
        "Direction": 0,
        "StopPosition": {"PositionLat": 25.0338, "PositionLon": 121.5298},
        "LocationCityCode": "TPE"
    }
]

MOCK_NEARBY_STOPS_DEST = [
    {
        "StopUID": "TPE10005",
        "StopID": "10005",
        "StopName": {"Zh_tw": "捷運台北101/世貿站", "En": "MRT Taipei 101/World Trade Center Station"},
        "RouteUID": "TPE12345",
        "RouteID": "12345",
        "RouteName": {"Zh_tw": "信義幹線", "En": "Xinyi Main Line"},
        "Direction": 0,
        "StopPosition": {"PositionLat": 25.0330, "PositionLon": 121.5638},
        "LocationCityCode": "TPE"
    },
    {
        # A stop on route 20 but in the backward direction (Direction 1) to test direction filter
        "StopUID": "TPE10006",
        "StopID": "10006",
        "StopName": {"Zh_tw": "捷運台北101/世貿站", "En": "MRT Taipei 101/World Trade Center Station"},
        "RouteUID": "TPE54321",
        "RouteID": "54321",
        "RouteName": {"Zh_tw": "20", "En": "20"},
        "Direction": 1,
        "StopPosition": {"PositionLat": 25.0330, "PositionLon": 121.5638},
        "LocationCityCode": "TPE"
    }
]

# Stop Of Route sequence data
MOCK_STOP_OF_ROUTE_XINYI = [
    {
        "RouteUID": "TPE12345",
        "RouteName": {"Zh_tw": "信義幹線", "En": "Xinyi Main Line"},
        "Direction": 0,
        "Stops": [
            {"StopUID": "TPE10001", "StopSequence": 1, "StopName": {"Zh_tw": "捷運動門站"}},
            {"StopUID": "TPE10003", "StopSequence": 2, "StopName": {"Zh_tw": "信義永康街口"}},
            {"StopUID": "TPE10005", "StopSequence": 3, "StopName": {"Zh_tw": "捷運台北101/世貿站"}}
        ]
    }
]

@patch("twbus.api.requests.post")
def test_get_tdx_token(mock_post):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_TOKEN_RESPONSE
    mock_post.return_value = mock_resp

    res = api.get_tdx_token(client_id="test_id", client_secret="test_secret")
    assert res is not None
    assert res["access_token"] == "mock_access_token_12345"
    assert res["expires_at"] > 0

@patch("twbus.api.requests.get")
def test_geocode_address(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_NOMINATIM_RESPONSE
    mock_get.return_value = mock_resp

    res = api.geocode_address("台北101")
    assert res is not None
    assert res["lat"] == 25.033964
    assert res["lon"] == 121.564468
    assert "台北101" in res["display_name"]

@patch("twbus.api.requests.get")
def test_get_nearby_stops(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_NEARBY_STOPS_START
    mock_get.return_value = mock_resp

    res = api.get_nearby_stops("token_123", 25.0338, 121.5298, radius=500)
    assert len(res) == 2
    assert res[0]["StopUID"] == "TPE10001"
    assert res[1]["RouteName"]["Zh_tw"] == "20"

@patch("twbus.api.get_nearby_stops")
@patch("twbus.api.requests.get")
def test_find_matching_routes(mock_get, mock_get_nearby_stops):
    # Setup mocks
    def side_effect_stops(token, lat, lon, radius=500):
        if lat == 25.0338:
            return MOCK_NEARBY_STOPS_START
        return MOCK_NEARBY_STOPS_DEST
        
    mock_get_nearby_stops.side_effect = side_effect_stops
    
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = MOCK_STOP_OF_ROUTE_XINYI
    mock_get.return_value = mock_resp

    routes = api.find_matching_routes("token_123", 25.0338, 121.5298, 25.0330, 121.5638)
    
    # We should match Xinyi Main Line (TPE12345) because StartStopSeq (1) < DestStopSeq (3)
    # We should NOT match Route 20 (TPE54321) because direction of start is 0 and destination is 1
    assert len(routes) == 1
    r = routes[0]
    assert r["RouteUID"] == "TPE12345"
    assert r["RouteName"] == "信義幹線"
    assert r["StartStopName"] == "捷運動門站"
    assert r["DestStopName"] == "捷運台北101/世貿站"
    assert r["StopCount"] == 2 # 3 - 1 = 2

def test_parse_coordinates():
    # Test DMS formats
    dms1 = "北緯25°5′0″  東經121°34′43″"
    res1 = api.parse_coordinates(dms1)
    assert res1 is not None
    assert abs(res1[0] - 25.083333333333332) < 1e-6
    assert abs(res1[1] - 121.5786111111111) < 1e-6

    dms2 = "25°5'0\"N, 121°34'43\"E"
    res2 = api.parse_coordinates(dms2)
    assert res2 is not None
    assert abs(res2[0] - 25.083333333333332) < 1e-6
    assert abs(res2[1] - 121.5786111111111) < 1e-6

    # Test Decimal formats
    dec1 = "25.0833, 121.5786"
    res3 = api.parse_coordinates(dec1)
    assert res3 == (25.0833, 121.5786)

    dec2 = "(25.0833, 121.5786)"
    res4 = api.parse_coordinates(dec2)
    assert res4 == (25.0833, 121.5786)

    # Test invalid format
    assert api.parse_coordinates("invalid string") is None

def test_parse_single_coordinate():
    # Test DMS formats
    lat_dms = "北緯25°5′0″"
    res_lat = api.parse_single_coordinate(lat_dms)
    assert res_lat is not None
    assert abs(res_lat - 25.083333333333332) < 1e-6

    lon_dms = "東經121°34′43″"
    res_lon = api.parse_single_coordinate(lon_dms)
    assert res_lon is not None
    assert abs(res_lon - 121.5786111111111) < 1e-6

    # Test decimal formats
    assert api.parse_single_coordinate("25.0833") == 25.0833
    assert api.parse_single_coordinate("-121.5786") == -121.5786

    # Test invalid format
    assert api.parse_single_coordinate("invalid") is None

