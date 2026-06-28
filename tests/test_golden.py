import pytest
from datetime import datetime, timezone, timedelta
from jp_weather.api import calculate_photography_rating

def test_calculate_photography_rating_rain():
    # Rainy scenario: precipitation probability > 30% and rain code
    start_time = datetime(2026, 6, 6, 17, 30, tzinfo=timezone.utc)
    end_time = datetime(2026, 6, 6, 18, 30, tzinfo=timezone.utc)
    
    # Matching hourly periods: 17:00, 18:00, 19:00
    hourly_data = {
        "time": ["2026-06-06T17:00", "2026-06-06T18:00", "2026-06-06T19:00"],
        "cloud_cover": [80, 95, 90],
        "precipitation_probability": [40, 60, 50],
        "weather_code": [61, 63, 61]  # Rain
    }
    
    stars, desc = calculate_photography_rating(start_time, end_time, hourly_data, "UTC")
    assert stars == 1
    assert "降雨機率高" in desc

def test_calculate_photography_rating_overcast():
    # Heavy cloud cover but no rain
    start_time = datetime(2026, 6, 6, 17, 30, tzinfo=timezone.utc)
    end_time = datetime(2026, 6, 6, 18, 30, tzinfo=timezone.utc)
    
    hourly_data = {
        "time": ["2026-06-06T17:00", "2026-06-06T18:00", "2026-06-06T19:00"],
        "cloud_cover": [95, 98, 97],
        "precipitation_probability": [10, 10, 10],
        "weather_code": [3, 3, 3]  # Overcast
    }
    
    stars, desc = calculate_photography_rating(start_time, end_time, hourly_data, "UTC")
    assert stars == 2
    assert "天空完全陰暗" in desc

def test_calculate_photography_rating_perfect_clouds():
    # Partly cloudy: ideal for sunset / burning clouds
    start_time = datetime(2026, 6, 6, 17, 30, tzinfo=timezone.utc)
    end_time = datetime(2026, 6, 6, 18, 30, tzinfo=timezone.utc)
    
    hourly_data = {
        "time": ["2026-06-06T17:00", "2026-06-06T18:00", "2026-06-06T19:00"],
        "cloud_cover": [40, 50, 45],
        "precipitation_probability": [0, 5, 0],
        "weather_code": [2, 2, 2]  # Partly cloudy
    }
    
    stars, desc = calculate_photography_rating(start_time, end_time, hourly_data, "UTC")
    assert stars == 5
    assert "雲量適中" in desc

def test_calculate_photography_rating_clear():
    # Clear sky: 0% clouds
    start_time = datetime(2026, 6, 6, 17, 30, tzinfo=timezone.utc)
    end_time = datetime(2026, 6, 6, 18, 30, tzinfo=timezone.utc)
    
    hourly_data = {
        "time": ["2026-06-06T17:00", "2026-06-06T18:00", "2026-06-06T19:00"],
        "cloud_cover": [5, 2, 0],
        "precipitation_probability": [0, 0, 0],
        "weather_code": [0, 0, 0]  # Clear sky
    }
    
    stars, desc = calculate_photography_rating(start_time, end_time, hourly_data, "UTC")
    assert stars == 4
    assert "天空晴朗無雲" in desc

# ---------------------------------------------------------------------------
# CLI golden Subcommand Tests
# ---------------------------------------------------------------------------
from click.testing import CliRunner
from unittest.mock import patch
from jp_weather.cli import cli

@patch("jp_weather.cli.get_location_or_prompt")
@patch("jp_weather.cli.fetch_weather_with_cache")
@patch("jp_weather.cli.render_golden_hour")
def test_cli_golden_today(mock_render, mock_fetch, mock_get_loc):
    runner = CliRunner()
    
    mock_get_loc.return_value = {
        "name": "東京", "latitude": 35.6895, "longitude": 139.6917,
        "country_code": "JP", "country": "日本", "admin1": "東京都"
    }
    mock_fetch.return_value = {"hourly": {"time": ["2026-06-06T12:00"]}}
    
    result = runner.invoke(cli, ["golden", "東京"])
    assert result.exit_code == 0
    mock_render.assert_called_once()
    # By default, week=False, mobile=False
    assert mock_render.call_args[1].get("week") is False
    assert mock_render.call_args[1].get("mobile") is False

@patch("jp_weather.cli.get_location_or_prompt")
@patch("jp_weather.cli.fetch_weather_with_cache")
@patch("jp_weather.cli.render_golden_hour")
def test_cli_golden_week_and_mobile(mock_render, mock_fetch, mock_get_loc):
    runner = CliRunner()
    
    mock_get_loc.return_value = {
        "name": "京都", "latitude": 35.0, "longitude": 135.0,
        "country_code": "JP", "country": "日本", "admin1": "京都府"
    }
    mock_fetch.return_value = {"hourly": {"time": ["2026-06-06T12:00"]}}
    
    result = runner.invoke(cli, ["golden", "Kyoto", "--week", "--mobile"])
    assert result.exit_code == 0
    mock_render.assert_called_once()
    assert mock_render.call_args[1].get("week") is True
    assert mock_render.call_args[1].get("mobile") is True

@patch("jp_weather.cli.get_location_or_prompt")
def test_cli_golden_cancel(mock_get_loc):
    runner = CliRunner()
    mock_get_loc.return_value = {"cancelled": True}
    
    result = runner.invoke(cli, ["golden", "東京"])
    assert result.exit_code == 0
    assert "已取消查詢。" in result.output

from jp_weather.api import parse_iso_datetime, reverse_geocode
def test_parse_iso_datetime():
    # Naive ISO string
    naive_str = "2026-06-06T12:34:56"
    dt = parse_iso_datetime(naive_str, timezone.utc)
    assert dt.tzinfo == timezone.utc
    assert dt.year == 2026 and dt.hour == 12 and dt.minute == 34
    
    # Trailing Z string
    z_str = "2026-06-06T12:34:56Z"
    dt = parse_iso_datetime(z_str, timezone.utc)
    assert dt.tzinfo == timezone.utc
    assert dt.year == 2026 and dt.hour == 12 and dt.minute == 34
    
    # Timezone-aware ISO string (Asia/Tokyo timezone)
    from zoneinfo import ZoneInfo
    tokyo_tz = ZoneInfo("Asia/Tokyo")
    aware_str = "2026-06-06T12:34:56+09:00"
    dt = parse_iso_datetime(aware_str, tokyo_tz)
    # The returned datetime should be converted to Tokyo timezone
    assert dt.tzinfo == tokyo_tz
    assert dt.hour == 12 and dt.minute == 34
    
    # Timezone-aware ISO string (UTC-05:00) converted to Tokyo
    aware_str_us = "2026-06-06T12:34:56-05:00"
    dt = parse_iso_datetime(aware_str_us, tokyo_tz)
    assert dt.tzinfo == tokyo_tz
    # 12:34:56 -05:00 is 17:34:56 UTC, which is 02:34:56 next day in Tokyo
    assert dt.day == 7
    assert dt.hour == 2

@patch("requests.get")
def test_reverse_geocode_timezone_fallback(mock_get):
    # Simulate a network failure so it triggers fallback
    mock_get.side_effect = Exception("network error")
    
    # 1. Coordinates inside Japan (Tokyo)
    loc_jp = reverse_geocode(35.6895, 139.6917)
    assert loc_jp["timezone"] == "Asia/Tokyo"
    
    # 2. Coordinates outside Japan (Tromsø, Norway)
    loc_no = reverse_geocode(69.649, 18.956)
    assert loc_no["timezone"] == "UTC"

from jp_weather.formatter import render_golden_hour
def test_render_golden_hour_execution():
    loc = {
        "name": "東京", "latitude": 35.6895, "longitude": 139.6917,
        "country_code": "JP", "country": "日本", "admin1": "東京都", "timezone": "Asia/Tokyo"
    }
    weather_data = {
        "timezone": "Asia/Tokyo",
        "hourly": {
            "time": ["2026-06-06T12:00"],
            "cloud_cover": [40],
            "precipitation_probability": [0],
            "weather_code": [2]
        },
        "daily": {
            "time": ["2026-06-06"]
        }
    }
    # Test rendering single day (normal)
    render_golden_hour(loc, weather_data, week=False, mobile=False)
    
    # Test rendering week (normal)
    render_golden_hour(loc, weather_data, week=True, mobile=False)
    
    # Test rendering mobile today
    render_golden_hour(loc, weather_data, week=False, mobile=True)
    
    # Test rendering mobile week
    render_golden_hour(loc, weather_data, week=True, mobile=True)
    
    # Test polar coordinates day today & week
    polar_loc_day = {
        "name": "Tromsø", "latitude": 69.649, "longitude": 18.956,
        "country_code": "NO", "country": "Norway", "admin1": "Troms"
    }
    render_golden_hour(polar_loc_day, weather_data, week=False, mobile=False)
    render_golden_hour(polar_loc_day, weather_data, week=True, mobile=False)

