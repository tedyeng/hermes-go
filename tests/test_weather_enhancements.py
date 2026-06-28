"""Additional tests for error handling and cache behaviour.

These tests cover the recent bug‑fixes:
- ``get_weather`` now returns ``None`` on any request failure.
- ``fetch_weather_with_cache`` propagates ``None`` and does not cache failed calls.
- ``geocode`` now generates suffix variations for both 2‑ and 3‑character CJK queries.
"""

import pytest
from unittest.mock import patch, MagicMock

from jp_weather.api import get_weather, geocode
from jp_weather.cli import fetch_weather_with_cache

# ---------------------------------------------------------------------------
# get_weather error handling
# ---------------------------------------------------------------------------
@patch("requests.get")
def test_get_weather_returns_none_on_http_error(mock_get):
    # Simulate a network timeout / HTTP error
    mock_get.side_effect = Exception("network failure")
    result = get_weather(35.0, 139.0, "Asia/Tokyo")
    assert result is None

# ---------------------------------------------------------------------------
# fetch_weather_with_cache propagates None and does not cache a failed call
# ---------------------------------------------------------------------------
def test_fetch_weather_with_cache_handles_failure(tmp_path, monkeypatch):
    # Patch the cache directory used by ``SQLiteCache`` to a temporary location.
    from platformdirs import user_cache_dir
    monkeypatch.setattr('platformdirs.user_cache_dir', lambda _: str(tmp_path))

    # Replace the module‑level cache with a fresh instance that points at the temp dir.
    from jp_weather.cache import SQLiteCache
    from jp_weather import cli as cli_module
    cli_module.cache = SQLiteCache(expiration_seconds=10)

    # Patch ``get_weather`` to return ``None`` (simulating a failed API call).
    with patch("jp_weather.api.get_weather", return_value=None) as mock_get_weather:
        loc = {"latitude": 35.0, "longitude": 139.0, "timezone": "Asia/Tokyo"}
        result = fetch_weather_with_cache(loc)
        # The wrapper should return ``None`` and not raise.
        assert result is None
        mock_get_weather.assert_called_once_with(35.0, 139.0, "Asia/Tokyo")
        # The temporary cache should not contain an entry for this key.
        cache_key = f"weather:{loc['latitude']:.4f}:{loc['longitude']:.4f}"
        assert cli_module.cache.get(cache_key) is None

# ---------------------------------------------------------------------------
# geocode suffix handling for three‑character CJK queries
# ---------------------------------------------------------------------------
@patch("jp_weather.api.fetch_geocode")
def test_geocode_suffixes_for_three_char_query(mock_fetch):
    # Return an empty list for any call; we only care about how many times it's invoked.
    mock_fetch.return_value = []
    # Two‑character query (original behaviour) – expect 1 original + 6 suffixes.
    _ = geocode("東京")
    assert mock_fetch.call_count == 7
    mock_fetch.reset_mock()
    # Three‑character CJK query – should also generate 6 suffix variations.
    _ = geocode("大阪府")  # three CJK characters
    assert mock_fetch.call_count == 7

# ---------------------------------------------------------------------------
# GPS parsing and reverse geocoding tests
# ---------------------------------------------------------------------------
from jp_weather.api import parse_gps, reverse_geocode

def test_parse_gps():
    # Decimal formats
    assert parse_gps("35.6895, 139.6917") == (35.6895, 139.6917)
    assert parse_gps("35.6895,139.6917") == (35.6895, 139.6917)
    assert parse_gps("35.6895 139.6917") == (35.6895, 139.6917)
    assert parse_gps("[35.6895, 139.6917]") == (35.6895, 139.6917)
    assert parse_gps("(35.6895, 139.6917)") == (35.6895, 139.6917)
    
    # DMS formats
    # 北緯25°5′0″ 東經121°34′43″
    lat, lon = parse_gps("北緯25°5′0″  東經121°34′43″")
    assert abs(lat - 25.08333) < 0.0001
    assert abs(lon - 121.57861) < 0.0001
    
    lat, lon = parse_gps("北緯 25° 5' 0\" 東經 121° 34' 43\"")
    assert abs(lat - 25.08333) < 0.0001
    assert abs(lon - 121.57861) < 0.0001

    lat, lon = parse_gps("N 35° 41' 22\" E 139° 41' 30\"")
    assert abs(lat - 35.68944) < 0.0001
    assert abs(lon - 139.69166) < 0.0001

    lat, lon = parse_gps("35° 41' 22\" N, 139° 41' 30\" E")
    assert abs(lat - 35.68944) < 0.0001
    assert abs(lon - 139.69166) < 0.0001
    
    # Invalid formats / values
    assert parse_gps("Tokyo") is None
    assert parse_gps("100-0001") is None
    assert parse_gps("95.0, 139.0") is None  # Latitude out of bounds
    assert parse_gps("35.0, 200.0") is None  # Longitude out of bounds

@patch("requests.get")
def test_reverse_geocode_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "place_id": 265363067,
        "display_name": "東京都島しょ保健所, 1, 西新宿二丁目, 西新宿, 新宿区, 東京都, 163-8001, 日本",
        "address": {
            "office": "東京都島しょ保健所",
            "house_number": "1",
            "neighbourhood": "西新宿二丁目",
            "quarter": "西新宿",
            "city": "新宿区",
            "ISO3166-2-lvl4": "JP-13",
            "postcode": "163-8001",
            "country": "日本",
            "country_code": "jp"
        }
    }
    mock_get.return_value = mock_resp
    
    loc = reverse_geocode(35.6895, 139.6917)
    assert loc["name"] == "東京都島しょ保健所"
    assert loc["latitude"] == 35.6895
    assert loc["longitude"] == 139.6917
    assert loc["country_code"] == "JP"
    assert loc["admin1"] == "東京都"

@patch("requests.get")
def test_reverse_geocode_failure(mock_get):
    # Simulate a network failure on reverse geocode
    mock_get.side_effect = Exception("network failure")
    loc = reverse_geocode(35.6895, 139.6917)
    
    # Should fall back gracefully to placeholder values
    assert "GPS 座標" in loc["name"]
    assert loc["latitude"] == 35.6895
    assert loc["longitude"] == 139.6917
    assert loc["country_code"] == "JP"
    assert loc["admin1"] == "GPS 定位"


# ---------------------------------------------------------------------------
# CLI --mobile Option Tests
# ---------------------------------------------------------------------------
from click.testing import CliRunner
from jp_weather.cli import cli

@patch("jp_weather.cli.get_location_or_prompt")
@patch("jp_weather.cli.fetch_weather_with_cache")
@patch("jp_weather.cli.render_current_weather")
def test_cli_current_mobile(mock_render, mock_fetch, mock_get_loc):
    runner = CliRunner()
    
    # Mock data
    mock_get_loc.return_value = {
        "name": "東京都", "latitude": 35.6895, "longitude": 139.6917,
        "country_code": "JP", "country": "日本", "admin1": "東京都"
    }
    mock_fetch.return_value = {"current": {"temperature_2m": 25.0}}
    
    # 1. Execute subcommand with `--mobile` flag at command level
    result = runner.invoke(cli, ["current", "東京", "--mobile"])
    assert result.exit_code == 0
    mock_render.assert_called_once()
    assert mock_render.call_args[1].get("mobile") is True
    
    # Reset mocks
    mock_render.reset_mock()
    mock_fetch.reset_mock()
    mock_get_loc.reset_mock()
    
    # 2. Execute subcommand with `--mobile` flag at parent level
    result = runner.invoke(cli, ["--mobile", "current", "東京"])
    assert result.exit_code == 0
    mock_render.assert_called_once()
    assert mock_render.call_args[1].get("mobile") is True


@patch("jp_weather.cli.get_location_or_prompt")
@patch("jp_weather.cli.fetch_weather_with_cache")
@patch("jp_weather.cli.render_forecast_weather")
def test_cli_forecast_mobile(mock_render, mock_fetch, mock_get_loc):
    runner = CliRunner()
    
    # Mock data
    mock_get_loc.return_value = {
        "name": "京都", "latitude": 35.0, "longitude": 135.0,
        "country_code": "JP", "country": "日本", "admin1": "京都府"
    }
    mock_fetch.return_value = {"daily": {"time": ["2026-05-31"]}}
    
    # Execute subcommand with `--mobile` flag at command level
    result = runner.invoke(cli, ["forecast", "Kyoto", "--mobile"])
    assert result.exit_code == 0
    mock_render.assert_called_once()
    assert mock_render.call_args[1].get("mobile") is True


@patch("jp_weather.cli.get_location_or_prompt")
def test_cli_current_cancel(mock_get_loc):
    runner = CliRunner()
    
    # Mock geocode returning cancellation sentinel dict
    mock_get_loc.return_value = {"cancelled": True}
    
    result = runner.invoke(cli, ["current", "東京"])
    assert result.exit_code == 0
    assert "已取消查詢。" in result.output



