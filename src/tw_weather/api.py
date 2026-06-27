import os
import re
import math
import logging
import requests
import urllib.parse
import urllib3
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Suppress insecure SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Load environment variables
load_dotenv()
for env_path in [os.path.expanduser("~/.env"), "/opt/data/.env"]:
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("weather.api")

NOMINATIM_URL = "https://nominatim.openstreetmap.org"
USER_AGENT = "hermes-go-weather-cli-tedyeng-2026/1.0 (tedyeng.code@gmail.com)"

# Map Taiwan County/City to CWA 3-day (3-hourly) forecast dataset IDs (F-D0047-XXX)
# The 3-day dataset IDs start at 001 and increment by 4 for each county.
COUNTY_DATASET_MAP = {
    "宜蘭縣": "F-D0047-001",
    "桃園市": "F-D0047-005",
    "新竹縣": "F-D0047-009",
    "苗栗縣": "F-D0047-013",
    "彰化縣": "F-D0047-017",
    "南投縣": "F-D0047-021",
    "雲林縣": "F-D0047-025",
    "嘉義縣": "F-D0047-029",
    "屏東縣": "F-D0047-033",
    "臺東縣": "F-D0047-037",
    "花蓮縣": "F-D0047-041",
    "澎湖縣": "F-D0047-045",
    "基隆市": "F-D0047-049",
    "新竹市": "F-D0047-053",
    "嘉義市": "F-D0047-057",
    "臺北市": "F-D0047-061",
    "高雄市": "F-D0047-065",
    "新北市": "F-D0047-069",
    "臺中市": "F-D0047-073",
    "臺南市": "F-D0047-077",
    "連江縣": "F-D0047-081",
    "金門縣": "F-D0047-085",
}

TAIWAN_COUNTIES = set(COUNTY_DATASET_MAP.keys())

class WeatherApiError(Exception):
    """Raised when CWA or Geocoding API requests fail."""
    pass

def parse_gps_input(text: str) -> Optional[Tuple[float, float]]:
    """Parse latitude and longitude from a variety of formats (URLs or raw coordinate strings)."""
    text = text.strip()
    if "apple.com" in text or "apple.co" in text:
        return None
    
    # 1. Try URL parsing
    url_match = re.search(r'(https?://\S+)', text)
    if url_match:
        url = url_match.group(1)
        if "maps.app.goo.gl" in url or "app.goo.gl" in url or "short" in url:
            try:
                r = requests.head(url, allow_redirects=True, timeout=5)
                parsed = urllib.parse.urlparse(r.url)
                hostname = parsed.hostname or ""
                if hostname.endswith("google.com") or hostname.endswith("googleusercontent.com") or hostname.endswith("goo.gl"):
                    url = r.url
            except Exception as e:
                logger.warning(f"Failed to resolve shortened URL: {e}")
        
        path_coords = re.search(r'[/@](-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)', url)
        if path_coords:
            try:
                lat, lon = float(path_coords.group(1)), float(path_coords.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return lat, lon
            except ValueError:
                pass
        
        try:
            parsed_url = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed_url.query)
            for param in ["q", "query", "ll", "center", "loc"]:
                if param in qs:
                    val = qs[param][0]
                    val_match = re.search(r'(-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)', val)
                    if val_match:
                        try:
                            lat, lon = float(val_match.group(1)), float(val_match.group(2))
                            if -90 <= lat <= 90 and -180 <= lon <= 180:
                                return lat, lon
                        except ValueError:
                            pass
        except Exception:
            pass

    # 2. Try DMS coordinates parsing
    dms_component = r'(北緯|南緯|東經|西經|[NSEW])?\s*(\d+(?:\.\d+)?)\s*°\s*(?:(\d+(?:\.\d+)?)\s*\'\s*)?(?:(\d+(?:\.\d+)?)\s*"\s*)?\s*([NSEW])?'
    matches = list(re.finditer(dms_component, text, re.IGNORECASE))
    if len(matches) == 2:
        parts = []
        for m in matches:
            prefix = m.group(1) or ""
            deg = float(m.group(2))
            min_val = float(m.group(3)) if m.group(3) else 0.0
            sec_val = float(m.group(4)) if m.group(4) else 0.0
            suffix = m.group(5) or ""
            
            dir_str = (prefix + suffix).strip()
            val = deg + min_val / 60.0 + sec_val / 3600.0
            if any(word in dir_str for word in ["南緯", "西經", "S", "s", "W", "w"]):
                val = -val
                
            is_lat = any(word in dir_str for word in ["北緯", "南緯", "N", "n", "S", "s"])
            is_lon = any(word in dir_str for word in ["東經", "西經", "E", "e", "W", "w"])
            
            parts.append((val, is_lat, is_lon))
            
        lat, lon = None, None
        if parts[0][1] and parts[1][2]:
            lat, lon = parts[0][0], parts[1][0]
        elif parts[0][2] and parts[1][1]:
            lat, lon = parts[1][0], parts[0][0]
        else:
            lat, lon = parts[0][0], parts[1][0]
            
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon

    # 3. Try generic decimal coordinates pattern search
    pattern = r'(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)'
    matches = re.findall(pattern, text)
    for lat_str, lon_str in matches:
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                # Handle possible (lon, lat) swap if lat/lon are flipped
                if 120 < lat < 122 and 21 < lon < 26:
                    lat, lon = lon, lat
                return lat, lon
        except ValueError:
            pass

    return None

def normalize_county(name: str) -> str:
    """Normalize county spelling to traditional Chinese characters and remove extra spaces."""
    if not name:
        return ""
    name = name.strip().replace("台", "臺")
    return name

def extract_county_and_district(address_dict: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    """
    Extract county (縣市) and district/town (鄉鎮市區) from Nominatim's address dict.
    Returns: (county_name, district_name)
    """
    county = None
    district = None

    # 1. Identify county/city
    for key in ["city", "county", "state", "town", "municipality"]:
        val = address_dict.get(key)
        if val:
            normalized = normalize_county(val)
            if normalized in TAIWAN_COUNTIES:
                county = normalized
                break
    
    # Fallback search if state/city is nested or named differently
    if not county:
        for val in address_dict.values():
            if isinstance(val, str):
                normalized = normalize_county(val)
                if normalized in TAIWAN_COUNTIES:
                    county = normalized
                    break

    # 2. Identify district/town
    # Look for common district fields first
    for key in ["suburb", "city_district", "district", "town", "village", "city"]:
        val = address_dict.get(key)
        if val and isinstance(val, str):
            val = val.strip()
            # Must end with 區, 鎮, 鄉, or 市 and must not be the county itself
            if val.endswith(("區", "鎮", "鄉", "市")) and normalize_county(val) != county:
                district = val
                break
                
    # Fallback search if not found in primary keys
    if not district:
        for val in address_dict.values():
            if isinstance(val, str):
                val = val.strip()
                if val.endswith(("區", "鎮", "鄉", "市")) and normalize_county(val) != county:
                    district = val
                    break

    return county, district

def geocode_address(address: str) -> Optional[Tuple[str, str, float, float]]:
    """
    Forward geocode an address using Nominatim.
    Returns: (county, district, lat, lon) or None
    """
    headers = {"User-Agent": USER_AGENT}
    params = {
        "q": address,
        "format": "json",
        "limit": 1,
        "addressdetails": 1,
        "accept-language": "zh-TW"
    }
    try:
        url = f"{NOMINATIM_URL}/search"
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            if res:
                item = res[0]
                lat = float(item["lat"])
                lon = float(item["lon"])
                address_dict = item.get("address", {})
                county, district = extract_county_and_district(address_dict)
                if county:
                    return county, district, lat, lon
                
                # Fallback: if Nominatim address block is incomplete, check display_name
                display_name = item.get("display_name", "")
                # Try direct regex extraction from display name or input address
                direct_match = re.search(
                    r"(臺北|台北|新北|桃園|臺中|台中|臺南|台南|高雄|基隆|新竹|嘉義|苗栗|彰化|南投|雲林|屏東|宜蘭|花蓮|臺東|台東|澎湖|金門|連江)(市|縣)([^市縣鄉鎮區]{1,10}[鄉鎮市區])",
                    display_name + " " + address
                )
                if direct_match:
                    co = normalize_county(direct_match.group(1) + direct_match.group(2))
                    dist = direct_match.group(3)
                    return co, dist, lat, lon
                    
        logger.warning(f"OSM Geocoding failed to resolve county/district for address: '{address}'")
    except Exception as e:
        logger.error(f"Geocoding exception: {e}", exc_info=True)
    return None

def reverse_geocode(lat: float, lon: float) -> Optional[Tuple[str, str]]:
    """
    Reverse geocode coordinates using Nominatim.
    Returns: (county, district) or None
    """
    headers = {"User-Agent": USER_AGENT}
    params = {
        "lat": lat,
        "lon": lon,
        "format": "json",
        "accept-language": "zh-TW"
    }
    try:
        url = f"{NOMINATIM_URL}/reverse"
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            if res:
                address_dict = res.get("address", {})
                county, district = extract_county_and_district(address_dict)
                if county:
                    return county, district
                
                # Fallback to regex check of display_name
                display_name = res.get("display_name", "")
                direct_match = re.search(
                    r"(臺北|台北|新北|桃園|臺中|台中|臺南|台南|高雄|基隆|新竹|嘉義|苗栗|彰化|南投|雲林|屏東|宜蘭|花蓮|臺東|台東|澎湖|金門|連江)(市|縣)([^市縣鄉鎮區]{1,10}[鄉鎮市區])",
                    display_name
                )
                if direct_match:
                    co = normalize_county(direct_match.group(1) + direct_match.group(2))
                    dist = direct_match.group(3)
                    return co, dist
                
        logger.warning(f"OSM Reverse Geocoding failed to resolve location for ({lat}, {lon})")
    except Exception as e:
        logger.error(f"Reverse geocoding exception: {e}", exc_info=True)
    return None

def match_county_only(text: str) -> Optional[str]:
    """Helper to match county-only name prefix in Taiwan (e.g. 台北 -> 臺北市, 宜蘭 -> 宜蘭縣)."""
    normalized = normalize_county(text).strip()
    for co in TAIWAN_COUNTIES:
        if normalized == co or normalized == co[:-1]: # matches "臺北市" or "臺北"
            return co
    return None

def resolve_location(location_input: str) -> Optional[Tuple[str, Optional[str], float, float]]:
    """
    Resolves input text or coordinates to (county_name, district_name, lat, lon).
    Returns None if the location is outside Taiwan or cannot be resolved.
    """
    # 0. Check if input is a county-only name prefix
    county_only = match_county_only(location_input)
    if county_only:
        res = geocode_address(county_only)
        if res:
            return res[0], None, res[2], res[3]
        return county_only, None, 0.0, 0.0

    # 1. First, check if input directly contains "County + District" using regex to save API calls
    direct_match = re.search(
        r"(臺北|台北|新北|桃園|臺中|台中|臺南|台南|高雄|基隆|新竹|嘉義|苗栗|彰化|南投|雲林|屏東|宜蘭|花蓮|臺東|台東|澎湖|金門|連江)(市|縣)([^市縣鄉鎮區]{1,10}[鄉鎮市區])",
        location_input
    )
    if direct_match:
        county = normalize_county(direct_match.group(1) + direct_match.group(2))
        district = direct_match.group(3).strip()
        # Still do geocoding to obtain lat/lon for completion, but if it fails we can fallback to Nominatim geocode
        res = geocode_address(location_input)
        if res:
            return res
        # If geocode fails, let's try geocoding just county + district
        res = geocode_address(county + district)
        if res:
            return res
        return county, district, 0.0, 0.0

    # 2. Check if the input is coordinates
    gps = parse_gps_input(location_input)
    if gps:
        lat, lon = gps
        resolved = reverse_geocode(lat, lon)
        if resolved:
            county, district = resolved
            return county, district, lat, lon
        return None

    # 3. Otherwise, use forward geocoding
    return geocode_address(location_input)

def fetch_cwa_weather(api_key: str, dataset_id: str, district_name: str, element_names: str = "PoP12h,Wx,T") -> Dict[str, Any]:
    """
    Call CWA Open Data API to fetch 3-day (3-hourly) forecast for district.
    Uses locationName and elementName parameters to filter payload.
    """
    url = f"https://opendata.cwa.gov.tw/api/v1/rest/datastore/{dataset_id}"
    params = {
        "Authorization": api_key,
        "locationName": district_name,
        "elementName": element_names,
        "format": "JSON"
    }
    
    try:
        r = requests.get(url, params=params, timeout=15, verify=False)
        if r.status_code == 200:
            res = r.json()
            if res.get("success") == "true" or res.get("success") is True:
                return res
            raise WeatherApiError(f"CWA API error: success response is false. Details: {res}")
        raise WeatherApiError(f"CWA API returned status code {r.status_code}: {r.text}")
    except Exception as e:
        if not isinstance(e, WeatherApiError):
            raise WeatherApiError(f"Network exception calling CWA API: {e}") from e
        raise

def parse_weather_json(cwa_response: Dict[str, Any], district_name: str) -> List[Dict[str, Any]]:
    """
    Parse CWA JSON response in PascalCase. Handles both 3-day (3-hourly) and 7-day (12-hourly) datasets.
    Groups 3-hourly data into standard 12-hour (白天/晚上) periods.
    """
    records = cwa_response.get("result", {}).get("records", {}) or cwa_response.get("records", {})
    locations = records.get("Locations", [])
    if not locations:
        raise WeatherApiError("No Locations found in CWA response records.")
    
    location_list = locations[0].get("Location", [])
    # Find matching locationName
    target_loc = None
    for loc in location_list:
        if loc.get("LocationName") == district_name:
            target_loc = loc
            break
            
    if not target_loc:
        if len(location_list) == 1:
            target_loc = location_list[0]
        else:
            raise WeatherApiError(f"District '{district_name}' not found in CWA API response locations.")
            
    elements = target_loc.get("WeatherElement", [])
    
    pop_times = []
    wx_times = []
    temp_times = []
    ci_times = []
    
    for el in elements:
        name = el.get("ElementName")
        times = el.get("Time", [])
        if name in ["12小時降雨機率", "3小時降雨機率"]:
            pop_times = times
        elif name == "天氣現象":
            wx_times = times
        elif name in ["溫度", "平均溫度"]:
            temp_times = times
        elif name == "舒適度指數":
            ci_times = times

    if not pop_times:
        raise WeatherApiError("CWA response is missing rain probability data (12小時降雨機率 or 3小時降雨機率).")

    # Find the start and end of the entire forecast range to define 12-hour blocks
    all_times = []
    for t in pop_times:
        st = t.get("StartTime") or t.get("DataTime")
        if st:
            all_times.append(datetime.fromisoformat(st))
            
    if not all_times:
        raise WeatherApiError("No time entries found in PoP element.")
        
    start_forecast = min(all_times)
    
    # Align start_forecast to 06:00 or 18:00 of that day
    start_hour = start_forecast.hour
    if start_hour < 6:
        aligned_start = start_forecast.replace(hour=18, minute=0, second=0, microsecond=0)
        from datetime import timedelta
        aligned_start -= timedelta(days=1)
    elif start_hour < 18:
        aligned_start = start_forecast.replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        aligned_start = start_forecast.replace(hour=18, minute=0, second=0, microsecond=0)
        
    # Generate 12-hour intervals from aligned_start
    from datetime import timedelta
    intervals = []
    curr = aligned_start
    for _ in range(12):  # up to 6 days
        next_interval = curr + timedelta(hours=12)
        intervals.append((curr, next_interval))
        curr = next_interval
        
    periods = []
    for s_dt, e_dt in intervals:
        pop_vals = []
        for t in pop_times:
            t_st_str = t.get("StartTime") or t.get("DataTime")
            if not t_st_str:
                continue
            t_st = datetime.fromisoformat(t_st_str)
            
            if s_dt <= t_st < e_dt:
                val_list = t.get("ElementValue", [])
                if val_list:
                    # CWA key is ProbabilityOfPrecipitation
                    val_str = val_list[0].get("ProbabilityOfPrecipitation", "0")
                    if val_str not in ["–", " ", "", None]:
                        try:
                            pop_vals.append(int(val_str))
                        except ValueError:
                            pass

        if not pop_vals:
            continue
            
        pop_val = max(pop_vals)

        # Overlapping Wx
        wx_vals = []
        for t in wx_times:
            t_st_str = t.get("StartTime") or t.get("DataTime")
            if not t_st_str:
                continue
            t_st = datetime.fromisoformat(t_st_str)
            if s_dt <= t_st < e_dt:
                val_list = t.get("ElementValue", [])
                if val_list:
                    wx_vals.append(val_list[0].get("Weather", ""))

        wx_summary = "多雲"
        if wx_vals:
            rain_Wx = [w for w in wx_vals if any(x in w for x in ["雨", "雷", "陣雨", "不穩定"])]
            if rain_Wx:
                wx_summary = max(rain_Wx, key=len)
            else:
                wx_summary = wx_vals[len(wx_vals)//2]

        # Overlapping Temp
        temp_vals = []
        for t in temp_times:
            t_st_str = t.get("StartTime") or t.get("DataTime")
            if not t_st_str:
                continue
            t_st = datetime.fromisoformat(t_st_str)
            if s_dt <= t_st < e_dt:
                val_list = t.get("ElementValue", [])
                if val_list:
                    try:
                        temp_vals.append(float(val_list[0].get("Temperature", 0)))
                    except ValueError:
                        pass

        # Overlapping Comfort Index
        comfort_desc = ""
        for t in ci_times:
            t_st_str = t.get("StartTime") or t.get("DataTime")
            if not t_st_str:
                continue
            t_st = datetime.fromisoformat(t_st_str)
            if s_dt <= t_st < e_dt:
                val_list = t.get("ElementValue", [])
                if val_list:
                    desc = val_list[0].get("ComfortIndexDescription", "")
                    if desc:
                        comfort_desc = desc
                        break

        if temp_vals:
            temp_min = min(temp_vals)
            temp_max = max(temp_vals)
        else:
            temp_min = 25.0
            temp_max = 30.0

        # Recommendation logic
        is_severe_rain = any(x in wx_summary for x in ["雷雨", "大雨", "豪雨", "暴雨"])
        is_light_rain = any(x in wx_summary for x in ["雨", "陣雨"])
        
        if pop_val >= 70 or (pop_val >= 50 and is_severe_rain):
            recommendation = "需帶直傘"
        elif pop_val >= 30 or is_light_rain or is_severe_rain:
            recommendation = "需帶折疊傘"
        else:
            recommendation = "不需帶傘"

        weekday_map = {0: "一", 1: "二", 2: "三", 3: "四", 4: "五", 5: "六", 6: "日"}
        wday = weekday_map.get(s_dt.weekday(), "")
        period_type = "晚上" if s_dt.hour >= 18 or s_dt.hour < 6 else "白天"
        period_name = f"{s_dt.strftime('%m/%d')} ({wday}) {period_type}"

        periods.append({
            "start_time": s_dt.isoformat(),
            "end_time": e_dt.isoformat(),
            "pop": pop_val,
            "wx_summary": wx_summary,
            "comfort": comfort_desc,
            "temp_min": int(round(temp_min)),
            "temp_max": int(round(temp_max)),
            "recommendation": recommendation,
            "period_name": period_name
        })

    return periods

def fetch_cwa_county_weather(api_key: str, county_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Call CWA Open Data API (F-C0032-001) to fetch 36h weather forecast for all or a specific county.
    """
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/F-C0032-001"
    params = {
        "Authorization": api_key,
        "format": "JSON"
    }
    if county_name:
        params["locationName"] = county_name
        
    try:
        r = requests.get(url, params=params, timeout=15, verify=False)
        if r.status_code == 200:
            res = r.json()
            if res.get("success") == "true" or res.get("success") is True:
                return res
            raise WeatherApiError(f"CWA API error: success response is false. Details: {res}")
        raise WeatherApiError(f"CWA API returned status code {r.status_code}: {r.text}")
    except Exception as e:
        if not isinstance(e, WeatherApiError):
            raise WeatherApiError(f"Network exception calling CWA API: {e}") from e
        raise

def parse_county_weather_json(cwa_response: Dict[str, Any], county_name: str) -> List[Dict[str, Any]]:
    """
    Parse CWA F-C0032-001 JSON response (using lowercase keys for county-level forecast).
    Returns 3 periods of 12-hour forecasts.
    """
    records = cwa_response.get("result", {}).get("records", {}) or cwa_response.get("records", {})
    location_list = records.get("location", [])
    if not location_list:
        raise WeatherApiError("No location entries found in CWA response records.")
        
    # Find matching county
    target_loc = None
    normalized_target = normalize_county(county_name)
    for loc in location_list:
        if normalize_county(loc.get("locationName")) == normalized_target:
            target_loc = loc
            break
            
    if not target_loc:
        if len(location_list) == 1:
            target_loc = location_list[0]
        else:
            raise WeatherApiError(f"County '{county_name}' not found in CWA API response.")
            
    elements = target_loc.get("weatherElement", [])
    
    wx_times = []
    pop_times = []
    mint_times = []
    maxt_times = []
    ci_times = []
    
    for el in elements:
        name = el.get("elementName")
        times = el.get("time", [])
        if name == "Wx":
            wx_times = times
        elif name == "PoP":
            pop_times = times
        elif name == "MinT":
            mint_times = times
        elif name == "MaxT":
            maxt_times = times
        elif name == "CI":
            ci_times = times

    if not pop_times:
        raise WeatherApiError("CWA county response is missing PoP (rain probability) data.")

    periods = []
    for i in range(len(pop_times)):
        p_pop = pop_times[i]
        start_str = p_pop.get("startTime")
        end_str = p_pop.get("endTime")
        if not start_str or not end_str:
            continue
            
        try:
            start_dt = datetime.fromisoformat(start_str.replace(" ", "T"))
            end_dt = datetime.fromisoformat(end_str.replace(" ", "T"))
        except ValueError:
            start_dt = datetime.now()
            end_dt = datetime.now()

        try:
            pop_val = int(p_pop.get("parameter", {}).get("parameterName", "0"))
        except ValueError:
            pop_val = 0

        p_wx = wx_times[i] if i < len(wx_times) else {}
        wx_summary = p_wx.get("parameter", {}).get("parameterName", "未知")

        p_mint = mint_times[i] if i < len(mint_times) else {}
        p_maxt = maxt_times[i] if i < len(maxt_times) else {}
        try:
            temp_min = int(p_mint.get("parameter", {}).get("parameterName", "0"))
            temp_max = int(p_maxt.get("parameter", {}).get("parameterName", "0"))
        except ValueError:
            temp_min = 25
            temp_max = 30

        p_ci = ci_times[i] if i < len(ci_times) else {}
        comfort_desc = p_ci.get("parameter", {}).get("parameterName", "")

        is_severe_rain = any(x in wx_summary for x in ["雷雨", "大雨", "豪雨", "暴雨"])
        is_light_rain = any(x in wx_summary for x in ["雨", "陣雨"])
        
        if pop_val >= 70 or (pop_val >= 50 and is_severe_rain):
            recommendation = "需帶直傘"
        elif pop_val >= 30 or is_light_rain or is_severe_rain:
            recommendation = "需帶折疊傘"
        else:
            recommendation = "不需帶傘"

        weekday_map = {0: "一", 1: "二", 2: "三", 3: "四", 4: "五", 5: "六", 6: "日"}
        wday = weekday_map.get(start_dt.weekday(), "")
        period_type = "晚上" if start_dt.hour >= 18 or start_dt.hour < 6 else "白天"
        period_name = f"{start_dt.strftime('%m/%d')} ({wday}) {period_type}"

        periods.append({
            "start_time": start_dt.isoformat(),
            "end_time": end_dt.isoformat(),
            "pop": pop_val,
            "wx_summary": wx_summary,
            "comfort": comfort_desc,
            "temp_min": temp_min,
            "temp_max": temp_max,
            "recommendation": recommendation,
            "period_name": period_name
        })

    return periods


def parse_hourly_weather_json(cwa_response: Dict[str, Any], district_name: str) -> List[Dict[str, Any]]:
    """
    Parse F-D0047 1-hourly elements (T, RH, AT, CI) and 3-hourly elements (Wx, PoP, Wind direction/speed)
    for a specific district, aligning them to a 1-hour time scale.
    """
    records = cwa_response.get("result", {}).get("records", {}) or cwa_response.get("records", {})
    locations = records.get("Locations", [])
    if not locations:
        raise WeatherApiError("No Locations found in CWA response records.")
    
    location_list = locations[0].get("Location", [])
    
    # Find matching locationName, fallback to first
    target_loc = None
    for loc in location_list:
        if loc.get("LocationName") == district_name:
            target_loc = loc
            break
    if not target_loc:
        if location_list:
            target_loc = location_list[0]
        else:
            raise WeatherApiError("No district locations found in CWA response.")

    elements = target_loc.get("WeatherElement", [])
    
    t_times = []
    rh_times = []
    at_times = []
    ci_times = []
    
    pop_times = []
    wx_times = []
    wd_times = []
    ws_times = []
    
    for el in elements:
        name = el.get("ElementName")
        times = el.get("Time", [])
        if name in ["溫度", "平均溫度"]:
            t_times = times
        elif name == "相對濕度":
            rh_times = times
        elif name == "體感溫度":
            at_times = times
        elif name == "舒適度指數":
            ci_times = times
        elif name in ["12小時降雨機率", "3小時降雨機率"]:
            pop_times = times
        elif name == "天氣現象":
            wx_times = times
        elif name == "風向":
            wd_times = times
        elif name == "風速":
            ws_times = times

    if not t_times:
        raise WeatherApiError("CWA response is missing hourly temperature (溫度) data.")

    hourly_records = []
    for t_node in t_times:
        dt_str = t_node.get("DataTime") or t_node.get("StartTime")
        if not dt_str:
            continue
        dt = datetime.fromisoformat(dt_str)
        
        # Temp
        t_val = ""
        val_list = t_node.get("ElementValue", [])
        if val_list:
            t_val = val_list[0].get("Temperature", "")

        # Find overlapping Relative Humidity (RH)
        rh_val = ""
        for item in rh_times:
            item_dt_str = item.get("DataTime") or item.get("StartTime")
            if item_dt_str and datetime.fromisoformat(item_dt_str) == dt:
                v_list = item.get("ElementValue", [])
                if v_list:
                    rh_val = v_list[0].get("RelativeHumidity", "")
                break
                
        # Find overlapping Apparent Temp (AT)
        at_val = ""
        for item in at_times:
            item_dt_str = item.get("DataTime") or item.get("StartTime")
            if item_dt_str and datetime.fromisoformat(item_dt_str) == dt:
                v_list = item.get("ElementValue", [])
                if v_list:
                    at_val = v_list[0].get("ApparentTemperature", "")
                break

        # Find overlapping Comfort Index (CI)
        ci_val = ""
        for item in ci_times:
            item_dt_str = item.get("DataTime") or item.get("StartTime")
            if item_dt_str and datetime.fromisoformat(item_dt_str) == dt:
                v_list = item.get("ElementValue", [])
                if v_list:
                    ci_val = v_list[0].get("ComfortIndexDescription", "")
                break

        # Find overlapping Wx (3-hourly)
        wx_val = "未知"
        for item in wx_times:
            item_st_str = item.get("StartTime") or item.get("DataTime")
            item_et_str = item.get("EndTime")
            if not item_st_str or not item_et_str:
                continue
            item_st = datetime.fromisoformat(item_st_str)
            item_et = datetime.fromisoformat(item_et_str)
            if item_st <= dt < item_et:
                v_list = item.get("ElementValue", [])
                if v_list:
                    wx_val = v_list[0].get("Weather", "")
                break

        # Find overlapping PoP (3-hourly)
        pop_val = 0
        for item in pop_times:
            item_st_str = item.get("StartTime") or item.get("DataTime")
            item_et_str = item.get("EndTime")
            if not item_st_str or not item_et_str:
                continue
            item_st = datetime.fromisoformat(item_st_str)
            item_et = datetime.fromisoformat(item_et_str)
            if item_st <= dt < item_et:
                v_list = item.get("ElementValue", [])
                if v_list:
                    pop_str = v_list[0].get("ProbabilityOfPrecipitation", "0")
                    if pop_str not in ["–", " ", "", None]:
                        try:
                            pop_val = int(pop_str)
                        except ValueError:
                            pass
                break

        # Find overlapping Wind Direction (WD, 3-hourly)
        wd_val = ""
        for item in wd_times:
            item_dt_str = item.get("DataTime") or item.get("StartTime")
            if not item_dt_str:
                continue
            item_dt = datetime.fromisoformat(item_dt_str)
            if item_dt <= dt < item_dt + timedelta(hours=3):
                v_list = item.get("ElementValue", [])
                if v_list:
                    wd_val = v_list[0].get("WindDirection", "")
                break

        # Find overlapping Wind Speed (WS, 3-hourly)
        ws_val = ""
        for item in ws_times:
            item_dt_str = item.get("DataTime") or item.get("StartTime")
            if not item_dt_str:
                continue
            item_dt = datetime.fromisoformat(item_dt_str)
            if item_dt <= dt < item_dt + timedelta(hours=3):
                v_list = item.get("ElementValue", [])
                if v_list:
                    ws_val = v_list[0].get("WindSpeed", "")
                break

        hourly_records.append({
            "datetime": dt.isoformat(),
            "temp": t_val,
            "rh": rh_val,
            "apparent_temp": at_val,
            "comfort": ci_val,
            "wx": wx_val,
            "pop": pop_val,
            "wind_dir": wd_val,
            "wind_speed": ws_val
        })

    return hourly_records


def fetch_cwa_rain_data(api_key: str) -> Dict[str, Any]:
    """
    Call CWA Open Data API (O-A0002-001) to fetch real-time rain observation data for all stations.
    """
    url = "https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0002-001"
    params = {
        "Authorization": api_key,
        "format": "JSON"
    }
    try:
        r = requests.get(url, params=params, timeout=15, verify=False)
        if r.status_code == 200:
            res = r.json()
            if res.get("success") == "true" or res.get("success") is True:
                return res
            raise WeatherApiError(f"CWA API error: success response is false. Details: {res}")
        raise WeatherApiError(f"CWA API returned status code {r.status_code}: {r.text}")
    except Exception as e:
        if not isinstance(e, WeatherApiError):
            raise WeatherApiError(f"Network exception calling CWA API: {e}") from e
        raise


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine formula to compute distance between two GPS coordinates in km."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2)**2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_nearest_rain_station(rain_data: Dict[str, Any], lat: float, lon: float) -> Tuple[Dict[str, Any], float]:
    """
    Given O-A0002-001 JSON data, finds the station closest to target (lat, lon).
    Returns (station_dict, distance_in_km).
    """
    records = rain_data.get("result", {}).get("records", {}) or rain_data.get("records", {})
    stations = records.get("Station", [])
    if not stations:
        raise WeatherApiError("No stations found in CWA rain data response.")
        
    nearest_station = None
    min_dist = float("inf")
    
    for st in stations:
        geo_info = st.get("GeoInfo", {})
        s_lat, s_lon = 0.0, 0.0
        for coord in geo_info.get("Coordinates", []):
            if coord.get("CoordinateName") == "WGS84":
                try:
                    s_lat = float(coord.get("StationLatitude", 0))
                    s_lon = float(coord.get("StationLongitude", 0))
                except ValueError:
                    pass
                break
        if s_lat == 0.0 or s_lon == 0.0:
            coords = geo_info.get("Coordinates", [])
            if coords:
                try:
                    s_lat = float(coords[0].get("StationLatitude", 0))
                    s_lon = float(coords[0].get("StationLongitude", 0))
                except ValueError:
                    pass
                    
        if s_lat == 0.0 or s_lon == 0.0:
            continue
            
        dist = calculate_distance(lat, lon, s_lat, s_lon)
        if dist < min_dist:
            min_dist = dist
            nearest_station = st
            
    if not nearest_station:
        raise WeatherApiError("Failed to find any active rain station with valid coordinates.")
        
    return nearest_station, min_dist


def format_rain_value(val_str: Any) -> float:
    """Helper to parse CWA precipitation strings, returning float values. Cleans anomalies."""
    if val_str is None:
        return 0.0
    val_str = str(val_str).strip()
    if val_str in ["-99", "-99.0", "-99.00", "X", "x"]:
        return -99.0
    if val_str in ["-98", "-98.0", "-98.00"]:
        return 0.0
    if val_str in ["T", "t"]:
        return 0.01
    try:
        return float(val_str)
    except ValueError:
        return 0.0


def display_rain_value(val_str: Any) -> str:
    val = format_rain_value(val_str)
    if val == -99.0:
        return "缺值/無資料"
    if val == 0.01:
        return "雨跡 (Trace)"
    return f"{val:.1f} mm"


def get_rain_alert_level(rain_1h: float, rain_3h: float, rain_24h: float) -> Tuple[str, str]:
    """
    Disaster warning levels based on official CWA standard in Taiwan:
    Returns (warning_classification_name, style_color).
    """
    if rain_24h >= 500:
        return "超大豪雨 (Extremely Torrential)", "red"
    elif rain_24h >= 350 or rain_3h >= 200:
        return "大豪雨 (Torrential)", "red"
    elif rain_24h >= 200 or rain_3h >= 100:
        return "豪雨 (Extremely Heavy)", "yellow"
    elif rain_24h >= 80 or rain_1h >= 40:
        return "大雨 (Heavy Rain)", "yellow"
    else:
        return "一般 (Normal)", "green"


def get_rain_intensity_label(rain_1h: float) -> str:
    """
    Returns rain intensity description based on hourly rainfall rate:
    - 0.1 <= rate <= 2.0 -> "毛毛雨，可不撐傘"
    - 2.0 < rate <= 10.0 -> "小雨，出門記得帶傘"
    - 10.0 < rate <= 30.0 -> "大雨，開車騎車請減速"
    - > 30.0 -> "豪雨或雷雨，注意低窪地區積水"
    - rate <= 0.0 -> "目前無顯著降雨"
    """
    if rain_1h == -99.0:
        return "暫無即時雨勢資料"
    if rain_1h <= 0.0:
        return "目前無顯著降雨"
    elif 0.1 <= rain_1h <= 2.0:
        return "毛毛雨，可不撐傘"
    elif 2.0 < rain_1h <= 10.0:
        return "小雨，出門記得帶傘"
    elif 10.0 < rain_1h <= 30.0:
        return "大雨，開車騎車請減速"
    else:
        return "豪雨或雷雨，注意低窪地區積水"


def get_rain_volume_estimate(wx: str, pop: int) -> str:
    """
    Estimates the future rain volume range (mm) based on Wx weather description
    and PoP (precipitation probability).
    """
    if pop <= 0:
        return "無雨 (0 mm)"
    
    is_rain_wx = any(x in wx for x in ["雨", "雷", "陣雨", "不穩定"])
    if pop < 30 and not is_rain_wx:
        return "無雨 (0 mm)"
        
    if any(x in wx for x in ["暴雨", "大暴雨", "超大豪雨", "大豪雨", "豪雨"]):
        return "豪雨等級 (約 >30 mm)"
    elif any(x in wx for x in ["大雨", "雷陣雨", "雷雨"]):
        return "大雨等級 (約 10~30 mm)"
    elif any(x in wx for x in ["毛毛雨", "雨跡", "短暫雨"]):
        return "微量/毛毛雨 (<2 mm)"
    elif any(x in wx for x in ["陣雨", "雨"]):
        return "小雨至中雨 (約 2~10 mm)"
    else:
        if pop >= 70:
            return "小雨至中雨 (約 2~10 mm)"
        else:
            return "局部微量雨 (<2 mm)"


def estimate_3h_rain_volume(pop: int, wx: str, weather_code: Optional[int] = None) -> Tuple[float, float]:
    """
    Estimates the min/max rain volume (mm) for a 3-hour period based on PoP3h and Wx/WeatherCode.
    """
    is_rain_wx = any(x in wx for x in ["雨", "雷", "陣雨", "不穩定"])
    
    is_rain_code = False
    if weather_code is not None:
        if weather_code >= 8:
            is_rain_code = True
            
    if pop < 20 and not is_rain_wx and not is_rain_code:
        return (0.0, 0.0)
    if pop == 0:
        return (0.0, 0.0)

    if any(x in wx for x in ["超大豪雨", "大豪雨", "豪雨", "暴雨"]) or (weather_code is not None and weather_code in [31, 32, 33, 34, 38, 39, 41]):
        severity = 4
    elif any(x in wx for x in ["大雨", "雷陣雨", "雷雨"]) or (weather_code is not None and weather_code in [15, 16, 17, 18, 30, 35, 36, 37, 40]):
        severity = 3
    elif any(x in wx for x in ["陣雨", "雨", "下雨"]) or is_rain_wx or is_rain_code:
        if any(x in wx for x in ["毛毛雨", "雨跡", "短暫雨", "微雨"]):
            severity = 1
        else:
            severity = 2
    else:
        severity = 0

    if severity == 4:
        if pop >= 50:
            return (25.0, 60.0)
        else:
            return (5.0, 20.0)
    elif severity == 3:
        if pop >= 50:
            return (8.0, 25.0)
        else:
            return (2.0, 10.0)
    elif severity == 2:
        if pop >= 50:
            return (2.0, 8.0)
        else:
            return (0.5, 3.0)
    elif severity == 1:
        if pop >= 50:
            return (0.1, 2.0)
        else:
            return (0.0, 1.0)
    else:
        if pop >= 50:
            return (0.0, 0.5)
        else:
            return (0.0, 0.0)


def parse_3h_forecast_for_rain(cwa_response: Dict[str, Any], district_name: str) -> List[Dict[str, Any]]:
    """
    Parses F-D0047 3-day (3-hourly) forecast response and aggregates 3-hourly precipitation estimates
    into 12-hour QPF periods.
    """
    records = cwa_response.get("result", {}).get("records", {}) or cwa_response.get("records", {})
    locations = records.get("Locations", [])
    if not locations:
        raise WeatherApiError("No Locations found in CWA response records.")
    
    location_list = locations[0].get("Location", [])
    target_loc = None
    for loc in location_list:
        if loc.get("LocationName") == district_name:
            target_loc = loc
            break
            
    if not target_loc:
        if len(location_list) == 1:
            target_loc = location_list[0]
        else:
            raise WeatherApiError(f"District '{district_name}' not found in CWA API response locations.")
            
    elements = target_loc.get("WeatherElement", [])
    
    pop_times = []
    wx_times = []
    
    for el in elements:
        name = el.get("ElementName")
        times = el.get("Time", [])
        if name == "3小時降雨機率":
            pop_times = times
        elif name == "天氣現象":
            wx_times = times
            
    if not pop_times:
        return []

    pop_by_time = {}
    for t in pop_times:
        st_str = t.get("StartTime") or t.get("DataTime")
        if st_str:
            val_list = t.get("ElementValue", [])
            if val_list:
                pop_val = val_list[0].get("ProbabilityOfPrecipitation", "0")
                if pop_val not in ["–", " ", "", None]:
                    try:
                        pop_by_time[datetime.fromisoformat(st_str)] = int(pop_val)
                    except ValueError:
                        pass

    wx_by_time = {}
    for t in wx_times:
        st_str = t.get("StartTime") or t.get("DataTime")
        if st_str:
            val_list = t.get("ElementValue", [])
            if val_list:
                wx_text = val_list[0].get("Weather", "")
                code_str = val_list[0].get("WeatherCode", "")
                try:
                    code = int(code_str) if code_str else None
                except ValueError:
                    code = None
                wx_by_time[datetime.fromisoformat(st_str)] = (wx_text, code)

    all_times = sorted(list(pop_by_time.keys()))
    if not all_times:
        return []
        
    start_forecast = all_times[0]
    start_hour = start_forecast.hour
    if start_hour < 6:
        aligned_start = start_forecast.replace(hour=18, minute=0, second=0, microsecond=0)
        aligned_start -= timedelta(days=1)
    elif start_hour < 18:
        aligned_start = start_forecast.replace(hour=6, minute=0, second=0, microsecond=0)
    else:
        aligned_start = start_forecast.replace(hour=18, minute=0, second=0, microsecond=0)

    intervals = []
    curr = aligned_start
    for _ in range(4):  # Next 2 days (4 periods of 12 hours)
        next_interval = curr + timedelta(hours=12)
        intervals.append((curr, next_interval))
        curr = next_interval

    periods = []
    for s_dt, e_dt in intervals:
        sub_pops = []
        sub_wxs = []
        min_accum = 0.0
        max_accum = 0.0
        
        curr_3h = s_dt
        while curr_3h < e_dt:
            pop_3h = pop_by_time.get(curr_3h)
            wx_info = wx_by_time.get(curr_3h)
            
            if pop_3h is not None and wx_info is not None:
                wx_text, weather_code = wx_info
                sub_pops.append(pop_3h)
                sub_wxs.append(wx_text)
                
                p_min, p_max = estimate_3h_rain_volume(pop_3h, wx_text, weather_code)
                min_accum += p_min
                max_accum += p_max
                
            curr_3h += timedelta(hours=3)

        if not sub_pops:
            continue

        pop_val = max(sub_pops)
        rain_Wx = [w for w in sub_wxs if any(x in w for x in ["雨", "雷", "陣雨", "不穩定"])]
        if rain_Wx:
            wx_summary = max(rain_Wx, key=len)
        else:
            wx_summary = sub_wxs[len(sub_wxs)//2] if sub_wxs else "多雲"

        weekday_map = {0: "一", 1: "二", 2: "三", 3: "四", 4: "五", 5: "六", 6: "日"}
        wday = weekday_map.get(s_dt.weekday(), "")
        period_type = "晚上" if s_dt.hour >= 18 or s_dt.hour < 6 else "白天"
        period_name = f"{s_dt.strftime('%m/%d')} ({wday}) {period_type}"

        periods.append({
            "period_name": period_name,
            "pop": pop_val,
            "wx_summary": wx_summary,
            "min_mm": min_accum,
            "max_mm": max_accum
        })

    return periods



