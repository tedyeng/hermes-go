import pytest
from unittest.mock import patch, MagicMock
from places import api
from places import cli

MOCK_RESTAURANTS = [
    {
        "place_id": "restaurant_01",
        "name": "鼎泰豐 101店",
        "geometry": {"location": {"lat": 25.0336, "lng": 121.5646}},
        "rating": 4.6,
        "user_ratings_total": 12050,
        "opening_hours": {"open_now": True},
        "vicinity": "市府路45號B1",
        "types": ["restaurant", "food", "establishment"]
    },
    {
        "place_id": "restaurant_02",
        "name": "一蘭拉麵 台北本店",
        "geometry": {"location": {"lat": 25.0334, "lng": 121.5681}},
        "rating": 4.3,
        "user_ratings_total": 8900,
        "opening_hours": {"open_now": False},
        "vicinity": "松仁路97號",
        "types": ["restaurant", "food", "establishment"]
    }
]

MOCK_ATTRACTIONS = [
    {
        "place_id": "attraction_01",
        "name": "台北101觀景台",
        "geometry": {"location": {"lat": 25.0339, "lng": 121.5645}},
        "rating": 4.7,
        "user_ratings_total": 24000,
        "opening_hours": {"open_now": True},
        "vicinity": "信義路五段7號89樓",
        "types": ["tourist_attraction", "point_of_interest", "establishment"]
    },
    # Duplicate with restaurant_01 to test deduplication in joint queries
    {
        "place_id": "restaurant_01",
        "name": "鼎泰豐 101店",
        "geometry": {"location": {"lat": 25.0336, "lng": 121.5646}},
        "rating": 4.6,
        "user_ratings_total": 12050,
        "opening_hours": {"open_now": True},
        "vicinity": "市府路45號B1",
        "types": ["restaurant", "food", "establishment"]
    }
]

def test_calculate_distance():
    # Taipei 101 to Taipei Station (~4.9 km)
    dist = api.calculate_distance(25.033964, 121.564468, 25.047675, 121.517055)
    assert 4700 <= dist <= 5100

def test_parse_gps_input_raw():
    res = api.parse_gps_input("25.0339, 121.5644")
    assert res is not None
    assert abs(res[0] - 25.0339) < 1e-4
    assert abs(res[1] - 121.5644) < 1e-4

    # Swapped lat/lon correction for Taiwan
    res2 = api.parse_gps_input("121.5644, 25.0339")
    assert res2 is not None
    assert abs(res2[0] - 25.0339) < 1e-4
    assert abs(res2[1] - 121.5644) < 1e-4

    # Swapped lat/lon correction worldwide (e.g. San Francisco -122.4194, 37.7749)
    res3 = api.parse_gps_input("-122.4194, 37.7749")
    assert res3 is not None
    assert abs(res3[0] - 37.7749) < 1e-4
    assert abs(res3[1] - -122.4194) < 1e-4


def test_parse_gps_input_urls():
    res = api.parse_gps_input("https://www.google.com/maps/search/?api=1&query=25.0339,121.5644")
    assert res == (25.0339, 121.5644)

    # Google Maps path coordinate
    res2 = api.parse_gps_input("https://www.google.com/maps/@25.0336,121.5644,17z")
    assert res2 == (25.0336, 121.5644)

    # Apple maps should be ignored
    res3 = api.parse_gps_input("https://maps.apple.com/?q=25.033,-121.564")
    assert res3 is None

@patch("places.api.requests.head")
def test_parse_gps_input_short_url(mock_head):
    mock_resp = MagicMock()
    mock_resp.url = "https://www.google.com/maps/place/25.0260,121.5436/"
    mock_head.return_value = mock_resp

    res = api.parse_gps_input("https://maps.app.goo.gl/abcd")
    mock_head.assert_called_once_with("https://maps.app.goo.gl/abcd", allow_redirects=True, timeout=3)
    assert res == (25.0260, 121.5436)

def test_parse_gps_input_dms():
    res = api.parse_gps_input("北緯25°5′0″ 東經121°34′43″")
    assert res is not None
    assert abs(res[0] - 25.0833) < 1e-3
    assert abs(res[1] - 121.5786) < 1e-3

    # DMS coordinate swapped global checking
    # 121°34′43″E, 25°5′0″N
    res2 = api.parse_gps_input("東經121°34′43″ 北緯25°5′0″")
    assert res2 is not None
    assert abs(res2[0] - 25.0833) < 1e-3
    assert abs(res2[1] - 121.5786) < 1e-3

@patch("places.api.requests.get")
def test_raw_query_places_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "OK",
        "results": MOCK_RESTAURANTS
    }
    mock_get.return_value = mock_resp

    res = api._raw_query_places("mock_key", 25.0339, 121.5644, 500, "restaurant", "zh-TW")
    assert len(res) == 2
    assert res[0]["name"] == "鼎泰豐 101店"
    assert res[1]["place_id"] == "restaurant_02"
    mock_get.assert_called_once()
    args, kwargs = mock_get.call_args
    assert kwargs["params"]["location"] == "25.0339,121.5644"
    assert kwargs["params"]["type"] == "restaurant"
    assert kwargs["params"]["language"] == "zh-TW"

@patch("places.api.requests.get")
def test_raw_query_places_denied(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "status": "REQUEST_DENIED",
        "error_message": "The provided API key is invalid."
    }
    mock_get.return_value = mock_resp

    with pytest.raises(api.GooglePlacesApiError) as exc_info:
        api._raw_query_places("invalid_key", 25.0339, 121.5644, 500, "restaurant")
    assert "API 請求被拒絕" in str(exc_info.value)

@patch("places.api._raw_query_places")
def test_get_nearby_places_mixed(mock_raw):
    # Mock separate queries for restaurant and tourist_attraction
    def side_effect(key, lat, lon, radius, place_type, language):
        if place_type == "restaurant":
            return MOCK_RESTAURANTS
        elif place_type == "tourist_attraction":
            return MOCK_ATTRACTIONS
        return []

    mock_raw.side_effect = side_effect

    # No type specified: searches both and deduplicates
    res = api.get_nearby_places("mock_key", 25.0339, 121.5644, 500, None, "zh-TW")
    
    # MOCK_RESTAURANTS has: restaurant_01, restaurant_02
    # MOCK_ATTRACTIONS has: attraction_01, restaurant_01 (duplicate)
    # Total unique: restaurant_01, restaurant_02, attraction_01
    assert len(res) == 3
    place_ids = [p["place_id"] for p in res]
    assert "restaurant_01" in place_ids
    assert "restaurant_02" in place_ids
    assert "attraction_01" in place_ids
    assert len(set(place_ids)) == 3
