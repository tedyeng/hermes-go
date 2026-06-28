import pytest
from unittest.mock import patch, MagicMock
from server import get_jp_weather

@patch("jp_weather.api.geocode")
@patch("jp_weather.api.get_weather")
def test_get_jp_weather_function_success(mock_get_weather, mock_geocode):
    # Mock geocode return
    mock_geocode.return_value = [
        {
            "name": "東京",
            "admin1": "東京都",
            "country": "日本",
            "country_code": "JP",
            "latitude": 35.6895,
            "longitude": 139.6917,
            "timezone": "Asia/Tokyo"
        }
    ]
    
    # Mock weather payload
    mock_get_weather.return_value = {
        "current": {
            "temperature_2m": 22.8,
            "relative_humidity_2m": 56,
            "apparent_temperature": 22.5,
            "precipitation": 0.0,
            "wind_speed_10m": 16.6,
            "wind_direction_10m": 180,
            "weather_code": 0,
            "time": "2026-06-28T11:30"
        },
        "hourly": {
            "time": ["2026-06-28T12:00", "2026-06-28T15:00"],
            "temperature_2m": [24.5, 24.8],
            "precipitation_probability": [0, 0],
            "weather_code": [0, 0]
        },
        "daily": {
            "time": ["2026-06-28"],
            "weather_code": [0],
            "temperature_2m_max": [27.6],
            "temperature_2m_min": [15.6],
            "precipitation_sum": [0.0],
            "precipitation_probability_max": [0],
            "wind_speed_10m_max": [12.0],
            "uv_index_max": [5.3]
        }
    }
    
    result = get_jp_weather("東京")
    assert result["status"] == "success"
    assert result["location"]["name"] == "東京"
    assert result["current"]["temperature"] == 22.8
    assert len(result["hourly"]) > 0
    assert len(result["daily"]) > 0
    assert result["photography"]["polar_status"] == "normal"
