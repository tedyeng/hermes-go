import os
import re
import math
import logging
import requests
import urllib.parse
from typing import List, Dict, Any, Optional, Tuple

# Load environment variables
from dotenv import load_dotenv
load_dotenv()
for env_path in [os.path.expanduser("~/.env"), "/opt/data/.env"]:
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("places.api")

GOOGLE_PLACES_API_URL = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"

class GooglePlacesApiError(Exception):
    """Raised when Google Places API requests fail or return non-OK status."""
    pass

TYPE_MAP = {
    "餐廳": "restaurant",
    "美食": "restaurant",
    "restaurant": "restaurant",
    "food": "restaurant",
    "景點": "tourist_attraction",
    "觀光": "tourist_attraction",
    "tourist": "tourist_attraction",
    "attraction": "tourist_attraction",
    "tourist_attraction": "tourist_attraction",
    "咖啡": "cafe",
    "咖啡廳": "cafe",
    "cafe": "cafe",
    "咖啡店": "cafe",
    "酒吧": "bar",
    "bar": "bar",
    "住宿": "lodging",
    "飯店": "lodging",
    "旅館": "lodging",
    "hotel": "lodging",
    "lodging": "lodging",
    "博物館": "museum",
    "museum": "museum",
    "公園": "park",
    "park": "park",
    "百貨": "shopping_mall",
    "商場": "shopping_mall",
    "購物中心": "shopping_mall",
    "shopping_mall": "shopping_mall",
    "mall": "shopping_mall",
}

TYPE_DISPLAY_MAP = {
    "restaurant": "餐廳",
    "food": "美食",
    "tourist_attraction": "景點",
    "cafe": "咖啡廳",
    "bar": "酒吧",
    "lodging": "住宿",
    "hotel": "飯店",
    "museum": "博物館",
    "park": "公園",
    "shopping_mall": "商場",
    "bakery": "麵包店",
    "meal_takeaway": "外帶美食",
    "meal_delivery": "外送美食",
    "amusement_park": "遊樂園",
    "aquarium": "水族館",
    "art_gallery": "美術館",
    "zoo": "動物園",
    "store": "商店",
    "place_of_worship": "寺廟/教堂",
}

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine formula to calculate distance in meters between two coordinates."""
    R = 6371000  # Radius of Earth in meters
    phi_1 = math.radians(lat1)
    phi_2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    
    a = math.sin(delta_phi / 2.0) ** 2 + \
        math.cos(phi_1) * math.cos(phi_2) * \
        math.sin(delta_lambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def parse_coordinates(text: str) -> Optional[Tuple[float, float]]:
    """
    Parse coordinates from a text string.
    Supports:
      - DMS formats like: 北緯25°5′0″ 東經121°34′43″, 25°5'0"N, 121°34'43"E, etc.
      - Decimal formats like: 25.0833, 121.5786 or (25.0833, 121.5786)
    """
    text = text.strip()
    text = text.replace("′", "'").replace("″", '"')
    
    # Try parsing decimal format
    dec_pattern = r'^\(?[NNSS]?\s*(-?\d+\.\d+)[,\s]+[EEWW]?\s*(-?\d+\.\d+)\)?$'
    match = re.match(dec_pattern, text, re.IGNORECASE)
    if match:
        try:
            lat = float(match.group(1))
            lon = float(match.group(2))
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except ValueError:
            pass

    # DMS parsing
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
            
            parts.append((val, is_lat, is_lon, dir_str))
            
        lat, lon = None, None
        if parts[0][1] and parts[1][2]:
            lat, lon = parts[0][0], parts[1][0]
        elif parts[0][2] and parts[1][1]:
            lat, lon = parts[1][0], parts[0][0]
        else:
            lat, lon = parts[0][0], parts[1][0]
            
        if -90 <= lat <= 90 and -180 <= lon <= 180:
            return lat, lon

    return None

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
                r = requests.head(url, allow_redirects=True, timeout=3)
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

    # 2. Try generic decimal coordinates pattern search
    pattern = r'(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)'
    matches = re.findall(pattern, text)
    for lat_str, lon_str in matches:
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            
            # Universal global swapping check:
            # If lat is not in [-90, 90] but lon is, and lat is in [-180, 180]
            if not (-90 <= lat <= 90) and (-180 <= lat <= 180) and (-90 <= lon <= 90):
                lat, lon = lon, lat
                
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except ValueError:
            pass

    # 3. Fallback to DMS/decimal coordinate parser
    res = parse_coordinates(text)
    if res:
        # Check global swap for fallback coordinate result too
        lat, lon = res
        if not (-90 <= lat <= 90) and (-180 <= lat <= 180) and (-90 <= lon <= 90):
            lat, lon = lon, lat
        return lat, lon

    return None

def _raw_query_places(api_key: str, lat: float, lon: float, radius: int, place_type: Optional[str] = None, language: str = "zh-TW") -> List[Dict[str, Any]]:
    """Helper to query the Google Places API for a single type."""
    params = {
        "location": f"{lat},{lon}",
        "radius": radius,
        "key": api_key,
        "language": language
    }
    if place_type:
        params["type"] = place_type

    try:
        r = requests.get(GOOGLE_PLACES_API_URL, params=params, timeout=10)
        if r.status_code != 200:
            raise GooglePlacesApiError(f"API request failed with status code {r.status_code}: {r.text}")
        
        data = r.json()
        status = data.get("status")
        
        if status == "OK":
            return data.get("results", [])
        elif status == "ZERO_RESULTS":
            return []
        elif status == "REQUEST_DENIED":
            err_msg = data.get("error_message", "請檢查您的 Google Places API 金鑰是否有效且已啟用 Places API。")
            raise GooglePlacesApiError(f"API 請求被拒絕: {err_msg}")
        elif status == "OVER_QUERY_LIMIT":
            raise GooglePlacesApiError("已超出 Google Places API 的配額限制。")
        elif status == "INVALID_REQUEST":
            raise GooglePlacesApiError("無效的請求參數。")
        else:
            raise GooglePlacesApiError(f"Google Places API 錯誤: {status}")
            
    except requests.RequestException as e:
        logger.error(f"HTTP request exception: {e}", exc_info=True)
        raise GooglePlacesApiError(f"網路連線異常: {e}")

def get_nearby_places(api_key: str, lat: float, lon: float, radius: int = 500, type_input: Optional[str] = None, language: str = "zh-TW") -> List[Dict[str, Any]]:
    """
    Search for places near the given coordinates globally.
    If type_input is None or Empty, it queries both 'restaurant' and 'tourist_attraction' and merges them.
    Otherwise, it maps the type_input using TYPE_MAP or passes it directly.
    """
    mapped_type = None
    if type_input:
        cleaned_type = type_input.strip().lower()
        mapped_type = TYPE_MAP.get(cleaned_type, cleaned_type)

    # If no type is specified, search for both restaurant and tourist_attraction
    if not mapped_type:
        restaurants = _raw_query_places(api_key, lat, lon, radius, "restaurant", language)
        attractions = _raw_query_places(api_key, lat, lon, radius, "tourist_attraction", language)
        
        # Merge and deduplicate by place_id
        seen = set()
        merged = []
        for p in restaurants + attractions:
            pid = p.get("place_id")
            if pid and pid not in seen:
                seen.add(pid)
                merged.append(p)
        return merged
    else:
        return _raw_query_places(api_key, lat, lon, radius, mapped_type, language)
