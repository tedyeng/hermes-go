import requests
import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone, timedelta

# Setup logging
logger = logging.getLogger("jp_weather.api")

# Open-Meteo API base URLs
GEO_URL = "https://geocoding-api.open-meteo.com/v1/search"
WEATHER_URL = "https://api.open-meteo.com/v1/forecast"

# Photography rating thresholds
PRECIP_THRESHOLD_HIGH = 50.0      # Precipitation probability > 50% means high chance of rain
PRECIP_THRESHOLD_MODERATE = 30.0  # Precipitation probability > 30% means moderate chance of rain
CLOUD_COVER_OVERCAST = 90.0       # Cloud cover > 90% is overcast
CLOUD_COVER_MOSTLY_CLOUDY = 75.0  # Cloud cover > 75% is mostly cloudy
CLOUD_COVER_PARTLY_CLOUDY_MIN = 30.0
CLOUD_COVER_PARTLY_CLOUDY_MAX = 70.0
CLOUD_COVER_CLEAR = 10.0          # Cloud cover < 10% is completely clear

def is_in_japan_bounds(lat: float, lon: float) -> bool:
    """Heuristic check if coordinates are within or close to Japan's boundaries."""
    return 20.0 <= lat <= 46.0 and 122.0 <= lon <= 154.0

def parse_iso_datetime(t_str: str, default_tz: timezone) -> datetime:
    """Parse ISO datetime string, handling 'Z' suffix, and ensure it has timezone info.
    
    If naive, attaches default_tz. If aware, converts to default_tz.
    """
    if t_str.endswith("Z"):
        t_str = t_str[:-1] + "+00:00"
    dt = datetime.fromisoformat(t_str)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=default_tz)
    return dt.astimezone(default_tz)

def is_cjk(char: str) -> bool:
    """Check if a character is CJK (Chinese/Japanese/Korean)."""
    return any([
        '\u4e00' <= char <= '\u9fff', # Unified Ideographs
        '\u3040' <= char <= '\u309f', # Hiragana
        '\u30a0' <= char <= '\u30ff', # Katakana
    ])

import unicodedata

def clean_query(query: str) -> str:
    """Normalize and trim the query.

    The CLI mixes full‑width/half‑width characters, so we normalise to NFC and
    strip surrounding whitespace. Lower‑casing is handled by the caller when
    constructing cache keys.
    """
    # Normalise Unicode (e.g., full‑width characters) and trim whitespace
    return unicodedata.normalize('NFC', query).strip()

def fetch_geocode(name: str) -> List[Dict[str, Any]]:
    """Helper to perform a single geocode request."""
    params = {
        "name": name,
        "count": 10,
        "language": "ja",
        "format": "json"
    }
    try:
        r = requests.get(GEO_URL, params=params, timeout=10)
        if r.status_code == 200:
            return r.json().get("results", [])
    except Exception as exc:
        logger.debug("Geocode request failed for name %s: %s", name, exc, exc_info=True)
    return []

def fetch_nominatim_fallback(query: str) -> List[Dict[str, Any]]:
    """
    Fallback geocoding using Nominatim (OpenStreetMap) if Open-Meteo geocoding has no results.
    Highly robust for tourist spots, landmarks, and mountains in Japan.
    """
    url = "https://nominatim.openstreetmap.org/search"
    headers = {
        "User-Agent": "jp_weather_cli_agent_tedyeng"
    }
    params = {
        "q": query,
        "format": "json",
        "limit": 5,
        "accept-language": "ja",
        "addressdetails": 1
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            results = r.json()
            formatted_results = []
            for res in results:
                addr = res.get("address", {})
                
                # Try to find the most specific name
                name = (
                    addr.get("valley") or addr.get("tourism") or addr.get("attraction") or
                    addr.get("natural") or addr.get("peak") or addr.get("suburb") or
                    addr.get("village") or addr.get("town") or addr.get("city") or
                    res.get("display_name", "").split(",")[0]
                )
                
                admin1 = addr.get("province") or addr.get("state") or addr.get("prefecture")
                country = addr.get("country", "日本")
                country_code = addr.get("country_code", "jp").upper()
                
                # Make a unique ID
                place_id = int(res.get("place_id", 0))
                
                formatted_results.append({
                    "id": place_id or hash(name),
                    "name": name,
                    "latitude": float(res.get("lat")),
                    "longitude": float(res.get("lon")),
                    "country_code": country_code,
                    "country": country,
                    "admin1": admin1,
                    "timezone": "Asia/Tokyo"
                })
            return formatted_results
    except Exception as exc:
        logger.debug("Nominatim fallback geocode request failed for query %s: %s", query, exc, exc_info=True)
    return []

def parse_gps(query: str) -> Optional[Tuple[float, float]]:
    """Parse GPS coordinates from a query string.
    
    Supports:
    1. Standard decimal formats:
       - 35.6895, 139.6917
       - 35.6895,139.6917
       - 35.6895 139.6917
       - [35.6895, 139.6917]
       - (35.6895, 139.6917)
       
    2. DMS (Degrees, Minutes, Seconds) formats:
       - 北緯25°5′0″ 東經121°34′43″
       - 北緯 25° 5' 0" 東經 121° 34' 43"
       - N 35° 41' 22" E 139° 41' 30"
       - 35° 41' 22" N, 139° 41' 30" E
       - 北緯35.6895° 東經139.6917°
    """
    cleaned = query.strip().strip("[]()")
    
    # 1. Try standard decimal coordinates first
    gps_pattern = re.compile(r"^\s*([+-]?\d+(?:\.\d+)?)\s*[\s,]\s*([+-]?\d+(?:\.\d+)?)\s*$")
    match = gps_pattern.match(cleaned)
    if match:
        try:
            lat = float(match.group(1))
            lon = float(match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except ValueError:
            pass

    # 2. Try DMS parsing
    lat_pref_pat = re.compile(r"(?P<pref>北緯|南緯|[北南NS])\s*(?P<deg>\d+(?:\.\d+)?)\s*°\s*(?:(?P<min>\d+(?:\.\d+)?)\s*[′']\s*)?(?:(?P<sec>\d+(?:\.\d+)?)\s*[″\"′′'']\s*)?", re.IGNORECASE)
    lat_suff_pat = re.compile(r"(?P<deg>\d+(?:\.\d+)?)\s*°\s*(?:(?P<min>\d+(?:\.\d+)?)\s*[′']\s*)?(?:(?P<sec>\d+(?:\.\d+)?)\s*[″\"′′'']\s*)?\s*(?P<suff>[NS])", re.IGNORECASE)

    lon_pref_pat = re.compile(r"(?P<pref>東經|西經|[東西EW])\s*(?P<deg>\d+(?:\.\d+)?)\s*°\s*(?:(?P<min>\d+(?:\.\d+)?)\s*[′']\s*)?(?:(?P<sec>\d+(?:\.\d+)?)\s*[″\"′′'']\s*)?", re.IGNORECASE)
    lon_suff_pat = re.compile(r"(?P<deg>\d+(?:\.\d+)?)\s*°\s*(?:(?P<min>\d+(?:\.\d+)?)\s*[′']\s*)?(?:(?P<sec>\d+(?:\.\d+)?)\s*[″\"′′'']\s*)?\s*(?P<suff>[EW])", re.IGNORECASE)

    lat_m = lat_pref_pat.search(cleaned) or lat_suff_pat.search(cleaned)
    lon_m = lon_pref_pat.search(cleaned) or lon_suff_pat.search(cleaned)

    if lat_m and lon_m:
        try:
            # Parse latitude
            lat_deg = float(lat_m.group("deg"))
            lat_min = float(lat_m.group("min")) if lat_m.group("min") else 0.0
            lat_sec = float(lat_m.group("sec")) if lat_m.group("sec") else 0.0
            lat_val = lat_deg + (lat_min / 60.0) + (lat_sec / 3600.0)
            
            # Determine latitude direction sign
            lat_dir = ""
            if "pref" in lat_m.groupdict() and lat_m.group("pref"):
                lat_dir += lat_m.group("pref").upper()
            if "suff" in lat_m.groupdict() and lat_m.group("suff"):
                lat_dir += lat_m.group("suff").upper()
            
            if any(k in lat_dir for k in ["S", "南"]):
                lat_val = -lat_val

            # Parse longitude
            lon_deg = float(lon_m.group("deg"))
            lon_min = float(lon_m.group("min")) if lon_m.group("min") else 0.0
            lon_sec = float(lon_m.group("sec")) if lon_m.group("sec") else 0.0
            lon_val = lon_deg + (lon_min / 60.0) + (lon_sec / 3600.0)
            
            # Determine longitude direction sign
            lon_dir = ""
            if "pref" in lon_m.groupdict() and lon_m.group("pref"):
                lon_dir += lon_m.group("pref").upper()
            if "suff" in lon_m.groupdict() and lon_m.group("suff"):
                lon_dir += lon_m.group("suff").upper()
            
            if any(k in lon_dir for k in ["W", "西"]):
                lon_val = -lon_val

            if -90 <= lat_val <= 90 and -180 <= lon_val <= 180:
                return lat_val, lon_val
        except (ValueError, IndexError):
            pass

    return None

def reverse_geocode(lat: float, lon: float) -> dict:
    """
    Reverse geocode lat/lon coordinates using Nominatim API to get location name.
    """
    url = "https://nominatim.openstreetmap.org/reverse"
    headers = {
        "User-Agent": "jp_weather_cli_agent_tedyeng"
    }
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "accept-language": "ja",
        "addressdetails": 1
    }
    try:
        r = requests.get(url, headers=headers, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json()
            addr = data.get("address", {})
            
            # Prioritize building/landmark names, then suburbs/cities, then roads
            name = (
                addr.get("tourism") or addr.get("attraction") or
                addr.get("amenity") or addr.get("building") or
                addr.get("shop") or addr.get("office") or
                addr.get("road") or addr.get("suburb") or
                addr.get("town") or addr.get("city") or
                data.get("display_name", "").split(",")[0]
            )
            
            admin1 = addr.get("province") or addr.get("state") or addr.get("prefecture")
            
            # Smart CJK prefecture extraction from display_name if missing in address dict
            display_name = data.get("display_name", "")
            parts = [p.strip() for p in display_name.split(",") if p.strip()]
            if not admin1 and len(parts) >= 3:
                for p in parts:
                    if p.endswith(("都", "道", "府", "県")):
                        admin1 = p
                        break
                if not admin1:
                    idx = -2
                    if len(parts) >= 3 and parts[-2].replace("-", "").isdigit():
                        idx = -3
                    if abs(idx) <= len(parts):
                        admin1 = parts[idx]

            country = addr.get("country", "日本")
            country_code = addr.get("country_code", "jp").upper()
            return {
                "id": int(data.get("place_id", hash(f"{lat},{lon}"))),
                "name": name or f"GPS 座標 ({lat:.4f}, {lon:.4f})",
                "latitude": lat,
                "longitude": lon,
                "country_code": country_code,
                "country": country,
                "admin1": admin1,
                "timezone": "Asia/Tokyo" if is_in_japan_bounds(lat, lon) else "UTC"
            }
    except Exception as exc:
        logger.debug("Reverse geocode failed for coords (%s, %s): %s", lat, lon, exc, exc_info=True)
    
    # Fallback if reverse geocode fails
    return {
        "id": hash(f"{lat},{lon}"),
        "name": f"GPS 座標 ({lat:.4f}, {lon:.4f})",
        "latitude": lat,
        "longitude": lon,
        "country_code": "JP",
        "country": "日本",
        "admin1": "GPS 定位",
        "timezone": "Asia/Tokyo" if is_in_japan_bounds(lat, lon) else "UTC"
    }
def _location_sort_key(item: Dict[str, Any], base_query: str) -> Tuple[int, int]:
    """Helper to compute sort priority for geocoding results."""
    name = (item.get("name") or "").lower()
    admin1 = (item.get("admin1") or "").lower()
    q_lower = base_query.lower()
    
    # Priority boost if exact match of the search query
    is_exact = 1 if (name == q_lower or q_lower in name or q_lower in admin1) else 0
    pop = item.get("population", 0) or 0
    return (is_exact, pop)

def geocode(query: str) -> List[Dict[str, Any]]:
    """
    Search for a location using geocoding or parse direct GPS coordinates.
    If the query is a short CJK term (2 or 3 characters), automatically generates and queries
    variants with common Japanese suffixes (都, 市, 府, 県, 町, 村) to improve match rates.
    """
    query = clean_query(query)
    if not query:
        return []

    # Check if direct GPS coordinates are queried
    gps_coords = parse_gps(query)
    if gps_coords:
        lat, lon = gps_coords
        return [reverse_geocode(lat, lon)]

    # If it looks like a Japanese postal code with a hyphen (e.g. 100-0001),
    # let's try searching as is. We also try striping the hyphen.
    queries_to_try = [query]
    
    # Smart suffix stripping:
    # If query ends with a common Japanese administrative suffix (都, 市, 府, 県, 町, 村)
    # and has more than 2 characters, let's also try searching for the base name!
    suffixes = ["都", "市", "府", "県", "町", "村"]
    base_query = query
    if len(query) > 2 and query[-1] in suffixes and all(is_cjk(c) for c in query):
        base_query = query[:-1]
        if base_query not in queries_to_try:
            queries_to_try.append(base_query)
            
    # If the query or base query is 2 CJK characters, generate all suffix variations
    if len(base_query) == 2 and all(is_cjk(c) for c in base_query):
        for suffix in suffixes:
            q_var = base_query + suffix
            if q_var not in queries_to_try:
                queries_to_try.append(q_var)

    all_results = []
    seen_ids = set()

    for q in queries_to_try:
        res_list = fetch_geocode(q)
        for res in res_list:
            loc_id = res.get("id")
            if loc_id and loc_id not in seen_ids:
                seen_ids.add(loc_id)
                all_results.append(res)
                
    # Filter for Japan results (JP) since JMA/Japan weather is requested.
    # If no JP results, keep all (for flexibility).
    jp_results = [r for r in all_results if r.get("country_code") == "JP"]
    results_to_use = jp_results if jp_results else all_results

    # Fallback to Nominatim if no results found
    if not results_to_use:
        results_to_use = fetch_nominatim_fallback(query)

    results_to_use.sort(key=lambda x: _location_sort_key(x, base_query), reverse=True)
    return results_to_use

def get_weather(lat: float, lon: float, timezone: str) -> Optional[Dict[str, Any]]:
    """Fetch current weather and 7‑day forecast data for the given coordinates.

    Returns the JSON payload on success or ``None`` if the request fails
    (network error, timeout, non‑2xx status, etc.). This prevents the CLI
    from crashing on transient API problems.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": (
            "temperature_2m,relative_humidity_2m,apparent_temperature,"
            "precipitation,weather_code,wind_speed_10m,wind_direction_10m"
        ),
        "hourly": (
            "temperature_2m,precipitation_probability,weather_code,cloud_cover"
        ),
        "daily": (
            "weather_code,temperature_2m_max,temperature_2m_min,"
            "precipitation_sum,precipitation_probability_max,"
            "wind_speed_10m_max,uv_index_max"
        ),
        "timezone": timezone,
    }
    try:
        r = requests.get(WEATHER_URL, params=params, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # Broad catch – any request failure returns None
        logger.error("Failed to fetch weather data from %s: %s", WEATHER_URL, exc, exc_info=True)
        return None

def calculate_photography_rating(
    start_time: Optional[datetime],
    end_time: Optional[datetime],
    hourly_data: dict,
    timezone_str: str
) -> Tuple[int, str]:
    """
    Calculate the photography rating (1 to 5 stars) and a text recommendation
    for a given time window, based on hourly forecast data from Open-Meteo.
    """
    if not start_time or not end_time or not hourly_data:
        return 3, "資料不足，無法評估拍攝條件。"

    from zoneinfo import ZoneInfo
    try:
        local_tz = ZoneInfo(timezone_str)
    except Exception as exc:
        logger.warning("Invalid timezone %s, falling back to UTC: %s", timezone_str, exc)
        local_tz = timezone.utc

    start_local = start_time.astimezone(local_tz)
    end_local = end_time.astimezone(local_tz)

    matched_clouds = []
    matched_precip = []
    matched_codes = []

    for i, t_str in enumerate(hourly_data.get("time", [])):
        try:
            t_dt = parse_iso_datetime(t_str, local_tz)
        except Exception as exc:
            logger.debug("Failed to parse hourly forecast time string %s: %s", t_str, exc)
            continue
        
        # Consider the hourly forecast relevant if it falls within the window hour boundaries
        window_start_hour = start_local.replace(minute=0, second=0, microsecond=0)
        window_end_hour = end_local.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        
        if window_start_hour <= t_dt <= window_end_hour:
            if i < len(hourly_data.get("cloud_cover", [])):
                matched_clouds.append(hourly_data["cloud_cover"][i])
            if i < len(hourly_data.get("precipitation_probability", [])):
                matched_precip.append(hourly_data["precipitation_probability"][i])
            if i < len(hourly_data.get("weather_code", [])):
                matched_codes.append(hourly_data["weather_code"][i])

    if not matched_clouds:
        return 3, "無該時段預報，無法評估。"

    avg_cloud = sum(matched_clouds) / len(matched_clouds)
    avg_precip = sum(matched_precip) / len(matched_precip) if matched_precip else 0.0

    # Rating criteria logic using extracted constants
    is_raining = avg_precip > PRECIP_THRESHOLD_MODERATE or any(code >= 50 for code in matched_codes)
    
    if is_raining:
        if avg_precip > PRECIP_THRESHOLD_HIGH or any(code >= 60 for code in matched_codes):
            return 1, "🌧️ 降雨機率高，不建議戶外拍照。"
        return 2, "🌦️ 可能有短暫降雨，拍照需注意防護。"

    if avg_cloud > CLOUD_COVER_OVERCAST:
        return 2, "☁️ 天空完全陰暗，光線將嚴重受阻。"
    elif avg_cloud > CLOUD_COVER_MOSTLY_CLOUDY:
        return 3, "🌥️ 多雲蔽日，光影效果一般。"
    elif CLOUD_COVER_PARTLY_CLOUDY_MIN <= avg_cloud <= CLOUD_COVER_PARTLY_CLOUDY_MAX:
        return 5, "⛅ 雲量適中！極易出現炫麗火燒雲與光影層次。"
    elif avg_cloud < CLOUD_COVER_CLEAR:
        return 4, "☀️ 天空晴朗無雲，光線柔和但背景較為單調。"
    else:
        return 4, "🌤️ 天氣晴朗，有少量雲彩點綴，適合拍攝。"
