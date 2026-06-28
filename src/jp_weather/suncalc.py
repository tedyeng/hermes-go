import math
from datetime import datetime, timezone, timedelta
from typing import Dict, Tuple, Optional, Any

# Constants
RAD = math.pi / 180.0
ECLIPTIC_OBLIQUITY = 23.4397 * RAD
J0 = 0.0009

# Solar Altitude Constants (degrees)
ALT_SUNRISE_SUNSET = -0.833   # Correction for atmospheric refraction & solar disc size
ALT_BLUE_HOUR_MIN = -6.0      # Start of morning / end of evening civil/nautical twilight
ALT_BLUE_HOUR_MAX = -4.0      # Boundary between blue hour and golden hour
ALT_GOLDEN_HOUR_MAX = 6.0     # End of morning / start of evening golden hour

def datetime_to_julian_days(dt: datetime) -> float:
    """Calculate the number of Julian days since J2000.0 (January 1, 2000 12:00 UTC)."""
    # Ensure datetime is timezone-aware and converted to UTC
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    else:
        dt = dt.astimezone(timezone.utc)
    
    # Julian Date at Unix epoch (1970-01-01 00:00:00 UTC) is 2440587.5
    # J2000.0 epoch Julian Date is 2451545.0
    # Difference: 2440587.5 - 2451545.0 = -10957.5
    timestamp = dt.timestamp()
    days_since_epoch = timestamp / 86400.0
    return days_since_epoch - 10957.5

def julian_days_to_datetime(days: float) -> datetime:
    """Convert Julian days since J2000.0 back to a UTC datetime object."""
    timestamp = (days + 10957.5) * 86400.0
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)

def get_solar_mean_anomaly(d: float) -> float:
    """Compute the solar mean anomaly (g) in radians."""
    return (357.5291 + 0.98560028 * d) * RAD

def get_ecliptic_longitude(g: float) -> float:
    """Compute the ecliptic longitude (lambda) in radians."""
    # Equation of center
    c = (1.9148 * math.sin(g) + 0.02 * math.sin(2 * g) + 0.0003 * math.sin(3 * g)) * RAD
    # Perihelion longitude
    p = 102.9372 * RAD
    return g + c + p + math.pi

def get_solar_declination(l: float) -> float:
    """Compute the solar declination (delta) in radians."""
    return math.asin(math.sin(l) * math.sin(ECLIPTIC_OBLIQUITY))

def get_julian_cycle(d: float, lw: float) -> float:
    """Compute the Julian cycle (approximate number of days since J2000)."""
    return round(d - J0 - lw / (2 * math.pi))

def get_approx_solar_transit(ht: float, lw: float, n: float) -> float:
    """Compute the approximate Julian date of solar transit."""
    return J0 + ht + lw / (2 * math.pi) + n

def get_solar_transit_j2000(ds: float, g: float, l: float) -> float:
    """Compute the precise J2000 Julian date of solar transit."""
    return J0 + ds + 0.0053 * math.sin(g) - 0.0069 * math.sin(2 * l)

def get_hour_angle(h: float, phi: float, delta: float) -> Optional[float]:
    """Compute the hour angle (H) in radians for a given solar altitude, latitude, and declination.
    
    Returns None if the sun never reaches this altitude (always above or below).
    """
    numerator = math.sin(h) - math.sin(phi) * math.sin(delta)
    denominator = math.cos(phi) * math.cos(delta)
    
    # Avoid division by zero
    if denominator == 0:
        return None
        
    cos_h = numerator / denominator
    
    if cos_h > 1.0:
        # Sun is always below this altitude (polar night for positive h)
        return None
    elif cos_h < -1.0:
        # Sun is always above this altitude (midnight sun for positive h)
        return None
        
    return math.acos(cos_h)

def get_sun_times_j2000(d: float, lat: float, lon: float) -> Dict[str, Optional[float]]:
    """Calculate Julian days (J2000) for solar transitions on a given Julian day d.
    
    Coordinates: lat (latitude), lon (longitude, east is positive).
    """
    lw = -lon * RAD
    phi = lat * RAD
    
    n = get_julian_cycle(d, lw)
    ds = get_approx_solar_transit(0, lw, n)
    
    g = get_solar_mean_anomaly(ds)
    l = get_ecliptic_longitude(g)
    delta = get_solar_declination(l)
    
    j_noon = get_solar_transit_j2000(ds, g, l)
    
    altitudes = {
        "sunrise": ALT_SUNRISE_SUNSET,
        "blue_min": ALT_BLUE_HOUR_MIN,
        "blue_max": ALT_BLUE_HOUR_MAX,
        "golden_max": ALT_GOLDEN_HOUR_MAX
    }
    
    result = {
        "noon": j_noon,
        "nadir": j_noon - 0.5
    }
    
    for key, alt_deg in altitudes.items():
        h = alt_deg * RAD
        H = get_hour_angle(h, phi, delta)
        
        if H is None:
            # Set consistent keys for _rise and _set to avoid missing keys
            result[f"{key}_rise"] = None
            result[f"{key}_set"] = None
        else:
            j_rise = j_noon - H / (2 * math.pi)
            j_set = j_noon + H / (2 * math.pi)
            result[f"{key}_rise"] = j_rise
            result[f"{key}_set"] = j_set
            
    return result

def get_sun_times(lat: float, lon: float, date: datetime) -> Dict[str, Any]:
    """Get precise solar times and polar status for the given latitude, longitude, and date.
    
    All returned datetime objects are timezone-aware (UTC timezone).
    """
    # Midday approximation (approx 12:00 local time)
    # We construct a datetime object for 12:00:00 UTC on the target date
    # to find the transit near noon on that day.
    midday_utc = datetime(date.year, date.month, date.day, 12, 0, 0, tzinfo=timezone.utc)
    d = datetime_to_julian_days(midday_utc)
    
    j_times = get_sun_times_j2000(d, lat, lon)
    
    times = {}
    
    # Convert Julian day values back to timezone-aware UTC datetime objects
    def to_dt(j_val: Optional[float]) -> Optional[datetime]:
        if j_val is None:
            return None
        return julian_days_to_datetime(j_val)
    
    noon = to_dt(j_times.get("noon"))
    nadir = to_dt(j_times.get("nadir"))
    
    times["noon"] = noon
    times["nadir"] = nadir
    
    # Sunrise & Sunset
    times["sunrise"] = to_dt(j_times.get("sunrise_rise"))
    times["sunset"] = to_dt(j_times.get("sunrise_set"))
    
    # Morning light phases:
    # - Blue hour: starts when sun rises above -6° (blue_min_rise) and ends at -4° (blue_max_rise).
    # - Golden hour: starts at -4° (blue_max_rise) and ends at 6° (golden_max_rise).
    times["blue_hour_am_start"] = to_dt(j_times.get("blue_min_rise"))
    times["blue_hour_am_end"] = to_dt(j_times.get("blue_max_rise"))
    
    times["golden_hour_am_start"] = to_dt(j_times.get("blue_max_rise"))
    times["golden_hour_am_end"] = to_dt(j_times.get("golden_max_rise"))
    
    # Evening light phases:
    # Note on chronology: As the sun sets, its altitude decreases.
    # It passes 6° (golden_max_set) FIRST, then passes -4° (blue_max_set) LATER.
    # Therefore, golden_max_set is earlier than blue_max_set.
    # - Golden hour: starts at 6° (golden_max_set) and ends at -4° (blue_max_set).
    # - Blue hour: starts at -4° (blue_max_set) and ends at -6° (blue_min_set).
    times["golden_hour_pm_start"] = to_dt(j_times.get("golden_max_set"))
    times["golden_hour_pm_end"] = to_dt(j_times.get("blue_max_set"))
    
    times["blue_hour_pm_start"] = to_dt(j_times.get("blue_max_set"))
    times["blue_hour_pm_end"] = to_dt(j_times.get("blue_min_set"))
    
    # Add polar day/night status
    times["polar_status"] = get_polar_status(lat, date)
    
    return times

def get_polar_status(lat: float, date: datetime) -> str:
    """Determine if the location is experiencing polar day, polar night, or normal day/night cycle.
    
    Returns 'polar_day', 'polar_night', or 'normal'.
    """
    # Calculate solar declination for the day
    midday_utc = datetime(date.year, date.month, date.day, 12, 0, 0, tzinfo=timezone.utc)
    d = datetime_to_julian_days(midday_utc)
    lw = 0.0  # Longitude doesn't affect declination calculation
    n = get_julian_cycle(d, lw)
    ds = get_approx_solar_transit(0, lw, n)
    g = get_solar_mean_anomaly(ds)
    l = get_ecliptic_longitude(g)
    delta = get_solar_declination(l)
    
    phi = lat * RAD
    
    # Max altitude (at transit)
    sin_alt_max = math.sin(phi) * math.sin(delta) + math.cos(phi) * math.cos(delta)
    sin_alt_max_clipped = max(-1.0, min(1.0, sin_alt_max))
    alt_max = math.asin(sin_alt_max_clipped) / RAD
    
    # Min altitude (at nadir)
    sin_alt_min = math.sin(phi) * math.sin(delta) - math.cos(phi) * math.cos(delta)
    sin_alt_min_clipped = max(-1.0, min(1.0, sin_alt_min))
    alt_min = math.asin(sin_alt_min_clipped) / RAD
    
    if alt_max < ALT_SUNRISE_SUNSET:
        return "polar_night"
    elif alt_min > ALT_SUNRISE_SUNSET:
        return "polar_day"
    return "normal"
