import pytest
from datetime import datetime, timezone, timedelta
from jp_weather.suncalc import (
    datetime_to_julian_days,
    julian_days_to_datetime,
    get_sun_times
)

def test_julian_conversions():
    # Test J2000.0 epoch: January 1, 2000 12:00:00 UTC
    dt_j2000 = datetime(2000, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    jd_days = datetime_to_julian_days(dt_j2000)
    assert abs(jd_days - 0.0) < 1e-7
    
    dt_back = julian_days_to_datetime(jd_days)
    assert dt_back == dt_j2000

def test_tokyo_solstice_sun_times():
    # Tokyo Coordinates
    lat = 35.6895
    lon = 139.6917
    
    # Test date: 2026-06-21 (Summer Solstice)
    # Expected times in JST (UTC+9):
    # Sunrise: approx 04:25 JST (2026-06-20 19:25 UTC)
    # Sunset: approx 19:00 JST (2026-06-21 10:00 UTC)
    test_date = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
    times = get_sun_times(lat, lon, test_date)
    
    # Check sunrise
    assert times["sunrise"] is not None
    sunrise_jst = times["sunrise"].astimezone(timezone(timedelta(hours=9)))
    assert sunrise_jst.year == 2026
    assert sunrise_jst.month == 6
    assert sunrise_jst.day == 21
    # Check hour and minutes (allow within 5 minutes threshold)
    total_minutes_sunrise = sunrise_jst.hour * 60 + sunrise_jst.minute
    expected_sunrise_minutes = 4 * 60 + 25
    assert abs(total_minutes_sunrise - expected_sunrise_minutes) <= 5
    
    # Check sunset
    assert times["sunset"] is not None
    sunset_jst = times["sunset"].astimezone(timezone(timedelta(hours=9)))
    assert sunset_jst.year == 2026
    assert sunset_jst.month == 6
    assert sunset_jst.day == 21
    total_minutes_sunset = sunset_jst.hour * 60 + sunset_jst.minute
    expected_sunset_minutes = 19 * 60 + 0
    assert abs(total_minutes_sunset - expected_sunset_minutes) <= 5

def test_london_equinox_sun_times():
    # London Coordinates (Equinox)
    # Lat: 51.5074, Lon: -0.1278 (West is negative in our get_sun_times API, which expects East positive)
    lat = 51.5074
    lon = -0.1278
    
    # Test date: 2026-03-20 (Spring Equinox)
    # Expected times in GMT (UTC+0):
    # Sunrise: approx 06:02 GMT (UTC)
    # Sunset: approx 18:13 GMT (UTC)
    test_date = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
    times = get_sun_times(lat, lon, test_date)
    
    assert times["sunrise"] is not None
    sunrise_utc = times["sunrise"].astimezone(timezone.utc)
    total_minutes_sunrise = sunrise_utc.hour * 60 + sunrise_utc.minute
    expected_sunrise_minutes = 6 * 60 + 2
    assert abs(total_minutes_sunrise - expected_sunrise_minutes) <= 5
    
    assert times["sunset"] is not None
    sunset_utc = times["sunset"].astimezone(timezone.utc)
    total_minutes_sunset = sunset_utc.hour * 60 + sunset_utc.minute
    expected_sunset_minutes = 18 * 60 + 13
    assert abs(total_minutes_sunset - expected_sunset_minutes) <= 5

def test_solar_phases_order():
    # Solar transitions order check
    # Morning: nadir -> blue_start -> blue_end (golden_start) -> golden_end -> sunrise -> noon
    # Evening: noon -> sunset -> golden_start -> golden_end (blue_start) -> blue_end -> nadir
    # In our naming:
    # Morning: blue_hour_am_start < blue_hour_am_end == golden_hour_am_start < golden_hour_am_end < sunrise < noon
    # Note: sunrise is actually inside the golden hour (golden hour is -4° to 6°, sunrise is -0.833°).
    # So sunrise should be between golden_hour_am_start and golden_hour_am_end.
    # Evening: noon < sunset < golden_hour_pm_start (at 6°) < golden_hour_pm_end (at -4°) == blue_hour_pm_start < blue_hour_pm_end (at -6°)
    # Wait, for evening:
    # 6° is before sunset (sunset is at -0.833°).
    # So: noon < golden_hour_pm_start (6°) < sunset (-0.833°) < golden_hour_pm_end (-4°) == blue_hour_pm_start < blue_hour_pm_end (-6°)
    
    lat = 35.6895
    lon = 139.6917
    test_date = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
    times = get_sun_times(lat, lon, test_date)
    
    assert times["blue_hour_am_start"] < times["blue_hour_am_end"]
    assert times["blue_hour_am_end"] == times["golden_hour_am_start"]
    assert times["golden_hour_am_start"] < times["sunrise"]
    assert times["sunrise"] < times["golden_hour_am_end"]
    assert times["golden_hour_am_end"] < times["noon"]
    
    assert times["noon"] < times["golden_hour_pm_start"]
    assert times["golden_hour_pm_start"] < times["sunset"]
    assert times["sunset"] < times["golden_hour_pm_end"]
    assert times["golden_hour_pm_end"] == times["blue_hour_pm_start"]
    assert times["blue_hour_pm_start"] < times["blue_hour_pm_end"]

def test_polar_status_detection():
    # Tromsø, Norway coordinates (High latitude, polar region)
    lat = 69.649
    lon = 18.956
    
    # 1. Summer Solstice - Polar Day (Midnight Sun)
    summer_date = datetime(2026, 6, 21, 12, 0, 0, tzinfo=timezone.utc)
    times_summer = get_sun_times(lat, lon, summer_date)
    assert times_summer["polar_status"] == "polar_day"
    # Sunrise & Sunset should be None in polar day
    assert times_summer["sunrise"] is None
    assert times_summer["sunset"] is None
    
    # 2. Winter Solstice - Polar Night
    winter_date = datetime(2026, 12, 21, 12, 0, 0, tzinfo=timezone.utc)
    times_winter = get_sun_times(lat, lon, winter_date)
    assert times_winter["polar_status"] == "polar_night"
    # Sunrise & Sunset should be None in polar night
    assert times_winter["sunrise"] is None
    assert times_winter["sunset"] is None
    
    # 3. Equinox - Normal Day/Night cycle
    equinox_date = datetime(2026, 3, 20, 12, 0, 0, tzinfo=timezone.utc)
    times_equinox = get_sun_times(lat, lon, equinox_date)
    assert times_equinox["polar_status"] == "normal"
    assert times_equinox["sunrise"] is not None
    assert times_equinox["sunset"] is not None
