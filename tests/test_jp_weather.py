import pytest
from unittest.mock import patch, MagicMock
from jp_weather.api import is_cjk, clean_query, geocode, get_weather
from jp_weather.formatter import get_weather_info, get_wind_direction_arrow, get_weekday_ch

def test_is_cjk():
    assert is_cjk("東") is True
    assert is_cjk("京") is True
    assert is_cjk("a") is False
    assert is_cjk("1") is False

def test_clean_query():
    assert clean_query("  東京  ") == "東京"
    assert clean_query("\nKyoto\t") == "Kyoto"

def test_get_weather_info():
    desc, emoji, color = get_weather_info(0)
    assert "晴天" in desc
    assert emoji == "☀"
    assert color == "yellow"
    
    desc, emoji, color = get_weather_info(95)
    assert "雷雨" in desc
    assert emoji == "⛈"
    
    desc_unk, emoji_unk, _ = get_weather_info(999)
    assert "未知" in desc_unk
    assert emoji_unk == "❓"

def test_get_wind_direction_arrow():
    assert get_wind_direction_arrow(0) == "↓"
    assert get_wind_direction_arrow(180) == "↑"
    assert get_wind_direction_arrow(90) == "←"
    assert get_wind_direction_arrow(270) == "→"
    assert get_wind_direction_arrow(None) == ""

def test_get_weekday_ch():
    # 2026-05-31 is Sunday (週日)
    assert get_weekday_ch("2026-05-31") == "週日"
    assert get_weekday_ch("invalid") == ""

@patch("requests.get")
def test_geocode(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [
            {
                "id": 1850147,
                "name": "東京都",
                "latitude": 35.6895,
                "longitude": 139.6917,
                "country_code": "JP",
                "country": "日本",
                "admin1": "東京都"
            }
        ]
    }
    mock_get.return_value = mock_resp
    
    results = geocode("東京")
    assert len(results) > 0
    assert results[0]["name"] == "東京都"
    assert results[0]["country_code"] == "JP"
