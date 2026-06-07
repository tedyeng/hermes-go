import os
import time
import logging
import requests
import urllib.parse
import re
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()  # Default CWD / parent directories search

# Also search user home directory and /opt/data/.env (for hermes container environment)
for env_path in [os.path.expanduser("~/.env"), "/opt/data/.env"]:
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("twbus.api")

# TDX configuration
TDX_TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_BASIC_URL = "https://tdx.transportdata.tw/api/basic"
TDX_ADVANCED_URL = "https://tdx.transportdata.tw/api/advanced"
USER_AGENT = "hermes-go-bot-tedyeng-dev-testing-2026/1.0 (tedyeng.code@gmail.com)"

# OSM Nominatim API config
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"

# Map LocationCityCode (e.g. from Stop/NearBy) to TDX API city name parameters
CITY_CODE_TO_NAME = {
    "TPE": "Taipei",
    "NWT": "NewTaipei",
    "TYN": "Taoyuan",
    "TXG": "Taichung",
    "TNN": "Tainan",
    "KHH": "Kaohsiung",
    "KEE": "Keelung",
    "HSZ": "Hsinchu",
    "HSQ": "HsinchuCounty",
    "MIA": "MiaoliCounty",
    "CHA": "ChanghuaCounty",
    "NAN": "NantouCounty",
    "YUN": "YunlinCounty",
    "CYI": "Chiayi",
    "CYQ": "ChiayiCounty",
    "PIF": "PingtungCounty",
    "ILA": "YilanCounty",
    "HUA": "HualienCounty",
    "TTT": "TaitungCounty",
    "PEN": "PenghuCounty",
    "KIN": "KinmenCounty",
    "LIE": "LienchiangCounty"
}

def get_tdx_token(client_id: Optional[str] = None, client_secret: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """
    Authenticate with TDX API to get an Access Token.
    Returns a dict with 'access_token' and 'expires_at' (epoch timestamp).
    """
    cid = client_id or os.getenv("TDX_CLIENT_ID") or os.getenv("tdx_client_id")
    csecret = client_secret or os.getenv("TDX_CLIENT_SECRET") or os.getenv("tdx_client_secret")

    if not cid or not csecret:
        logger.error("Missing TDX_CLIENT_ID or TDX_CLIENT_SECRET in environment variables.")
        return None

    data = {
        "grant_type": "client_credentials",
        "client_id": cid,
        "client_secret": csecret
    }
    
    headers = {
        "Content-Type": "application/x-www-form-urlencoded"
    }

    try:
        r = requests.post(TDX_TOKEN_URL, data=data, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            # Cache duration in seconds, typically 86400 (1 day)
            expires_in = res.get("expires_in", 3600)
            return {
                "access_token": res.get("access_token"),
                "expires_at": time.time() + expires_in - 60 # buffer of 1 minute
            }
        logger.error(f"Failed to fetch TDX token: status code {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.error(f"Exception during TDX token fetch: {e}", exc_info=True)
    return None

def parse_coordinates(text: str) -> Optional[Tuple[float, float]]:
    """
    Parse coordinates from a text string.
    Supports:
      - DMS formats like: 北緯25°5′0″ 東經121°34′43″, 25°5'0"N, 121°34'43"E, etc.
      - Decimal formats like: 25.0833, 121.5786 or (25.0833, 121.5786)
    """
    # Normalize unicode spaces and quotes
    text = text.strip()
    text = text.replace("′", "'").replace("″", '"')
    
    # Try parsing decimal format: e.g. "25.033, 121.564" or "(25.033, 121.564)" or "25.033 121.564"
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
    # A single DMS component pattern:
    # (北緯|南緯|東經|西經|[NSEW])?\s*(\d+(?:\.\d+)?)\s*°\s*(?:(\d+(?:\.\d+)?)\s*\'\s*)?(?:(\d+(?:\.\d+)?)\s*"\s*)?\s*([NSEW])?
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
            
            # Determine direction (N/S/E/W)
            dir_str = (prefix + suffix).strip()
            
            # Convert to decimal
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

def parse_single_coordinate(text: str) -> Optional[float]:
    """
    Parse a single latitude or longitude value from a string.
    Supports decimal floats (e.g. 25.033) and DMS (e.g. 北緯25°5′0″, 121°34'43"E).
    """
    text = text.strip()
    try:
        return float(text)
    except ValueError:
        pass
        
    text = text.replace("′", "'").replace("″", '"')
    
    dms_pattern = r'^(北緯|南緯|東經|西經|[NSEW])?\s*(\d+(?:\.\d+)?)\s*°\s*(?:(\d+(?:\.\d+)?)\s*\'\s*)?(?:(\d+(?:\.\d+)?)\s*"\s*)?\s*([NSEW])?$'
    match = re.match(dms_pattern, text, re.IGNORECASE)
    if match:
        prefix = match.group(1) or ""
        deg = float(match.group(2))
        min_val = float(match.group(3)) if match.group(3) else 0.0
        sec_val = float(match.group(4)) if match.group(4) else 0.0
        suffix = match.group(5) or ""
        
        dir_str = (prefix + suffix).strip()
        val = deg + min_val / 60.0 + sec_val / 3600.0
        if any(word in dir_str for word in ["南緯", "西經", "S", "s", "W", "w"]):
            val = -val
        return val
        
    return None

def geocode_address(address: str) -> Optional[Dict[str, Any]]:
    """
    Geocode address/name to (lat, lon) using OpenStreetMap Nominatim.
    Returns:
        Dict: {"lat": float, "lon": float, "display_name": str} or None
    """
    headers = {
        "User-Agent": USER_AGENT
    }
    params = {
        "q": address,
        "format": "json",
        "limit": 1
    }
    
    try:
        r = requests.get(NOMINATIM_URL, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            if res:
                return {
                    "lat": float(res[0]["lat"]),
                    "lon": float(res[0]["lon"]),
                    "display_name": res[0]["display_name"]
                }
            logger.warning(f"No geocoding results found for address: '{address}'")
        else:
            logger.error(f"Geocoding failed with status {r.status_code}: {r.text}")
    except Exception as e:
        logger.error(f"Exception during geocoding: {e}", exc_info=True)
    return None

def get_nearby_stops(token: str, lat: float, lon: float, radius: int = 500) -> List[Dict[str, Any]]:
    """
    Get nearby bus stops using spatial filter.
    Returns a list of Stop objects.
    """
    url = f"{TDX_ADVANCED_URL}/v2/Bus/Stop/NearBy"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT
    }
    params = {
        "$spatialFilter": f"nearby(StopPosition, {lat}, {lon}, {radius})",
        "$format": "JSON"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        logger.error(f"Nearby stops API failed: status code {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.error(f"Exception during nearby stops request: {e}", exc_info=True)
    return []

def get_stop_of_route(token: str, city: str, route_name: str) -> List[Dict[str, Any]]:
    """
    Get all stops along a route for sequence verification.
    city should be the TDX city name (e.g. 'Taipei').
    """
    # URL encode route name for safeness
    safe_route = urllib.parse.quote(route_name)
    url = f"{TDX_BASIC_URL}/v2/Bus/StopOfRoute/City/{city}/{safe_route}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT
    }
    params = {
        "$format": "JSON"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        logger.error(f"StopOfRoute API failed for {city}/{route_name}: status code {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.error(f"Exception during StopOfRoute request: {e}", exc_info=True)
    return []

def get_estimated_time_of_arrival(token: str, city: str, route_name: str, stop_uid: str) -> Optional[Dict[str, Any]]:
    """
    Get estimated arrival time of a route at a specific StopUID.
    Returns:
        Dict with keys:
            - 'EstimateTime': int (seconds) or None
            - 'StopStatus': int (0: normal, 1: not departed, 2: bypass, 3: last bus passed, 4: no service)
            - 'Message': str (human-readable status description)
    """
    safe_route = urllib.parse.quote(route_name)
    url = f"{TDX_BASIC_URL}/v2/Bus/EstimatedTimeOfArrival/City/{city}/{safe_route}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT
    }
    params = {
        "$filter": f"StopUID eq '{stop_uid}'",
        "$format": "JSON"
    }

    status_messages = {
        0: "正常",
        1: "尚未發車",
        2: "交管不停靠",
        3: "末班車已過",
        4: "今日未營運"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            if res:
                # Find the matching entry for this stop_uid
                for item in res:
                    if item.get("StopUID") == stop_uid:
                        status = item.get("StopStatus", 0)
                        est_time = item.get("EstimateTime")
                        
                        # Friendly text formatting
                        if status == 0 and est_time is not None:
                            minutes = est_time // 60
                            if minutes == 0:
                                msg = "即將到站"
                            else:
                                msg = f"{minutes} 分鐘"
                        else:
                            msg = status_messages.get(status, "未知狀態")

                        return {
                            "EstimateTime": est_time,
                            "StopStatus": status,
                            "Message": msg
                        }
            logger.warning(f"No ETA data found for stop {stop_uid} on route {route_name} in {city}")
        else:
            logger.error(f"ETA API failed: status code {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.error(f"Exception during ETA request: {e}", exc_info=True)
    return None

def get_estimated_time_of_arrival_for_stop(token: str, city: str, stop_uid: str) -> List[Dict[str, Any]]:
    """
    Get estimated arrival times of all routes passing through a specific StopUID.
    """
    url = f"{TDX_BASIC_URL}/v2/Bus/EstimatedTimeOfArrival/City/{city}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT
    }
    params = {
        "$filter": f"StopUID eq '{stop_uid}'",
        "$format": "JSON"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            formatted_etas = []
            status_messages = {0: "正常", 1: "尚未發車", 2: "交管不停靠", 3: "末班車已過", 4: "今日未營運"}
            for item in res:
                status = item.get("StopStatus", 0)
                est_time = item.get("EstimateTime")
                route_name = item.get("RouteName", {}).get("Zh_tw", "")
                direction = item.get("Direction", 0)
                
                if status == 0 and est_time is not None:
                    minutes = est_time // 60
                    msg = "即將到站" if minutes == 0 else f"{minutes} 分鐘"
                else:
                    msg = status_messages.get(status, "未知狀態")
                    
                formatted_etas.append({
                    "RouteName": route_name,
                    "Direction": direction,
                    "EstimateTime": est_time,
                    "StopStatus": status,
                    "Message": msg
                })
            return formatted_etas
        logger.error(f"ETA for stop {stop_uid} failed: status code {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.error(f"Exception during ETA for stop {stop_uid}: {e}", exc_info=True)
    return []

def get_estimated_time_of_arrival_for_stops(token: str, city: str, stop_uids: List[str]) -> List[Dict[str, Any]]:
    """
    Get estimated arrival times of all routes passing through a list of StopUIDs in one batch.
    """
    if not stop_uids:
        return []

    uids_subset = stop_uids[:30]
    filter_str = " or ".join([f"StopUID eq '{uid}'" for uid in uids_subset])

    url = f"{TDX_BASIC_URL}/v2/Bus/EstimatedTimeOfArrival/City/{city}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT
    }
    params = {
        "$filter": filter_str,
        "$format": "JSON"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            formatted_etas = []
            status_messages = {0: "正常", 1: "尚未發車", 2: "交管不停靠", 3: "末班車已過", 4: "今日未營運"}
            for item in res:
                status = item.get("StopStatus", 0)
                est_time = item.get("EstimateTime")
                route_name = item.get("RouteName", {}).get("Zh_tw", "")
                direction = item.get("Direction", 0)
                stop_uid = item.get("StopUID", "")
                
                if status == 0 and est_time is not None:
                    minutes = est_time // 60
                    msg = "即將到站" if minutes == 0 else f"{minutes} 分鐘"
                else:
                    msg = status_messages.get(status, "未知狀態")
                    
                formatted_etas.append({
                    "StopUID": stop_uid,
                    "RouteName": route_name,
                    "Direction": direction,
                    "EstimateTime": est_time,
                    "StopStatus": status,
                    "Message": msg
                })
            return formatted_etas
        logger.error(f"ETA for stops failed: status code {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.error(f"Exception during ETA for stops: {e}", exc_info=True)
    return []


def get_estimated_time_of_arrival_for_route(token: str, city: str, route_name: str) -> List[Dict[str, Any]]:
    """
    Get estimated arrival times of all stops for a specific route.
    """
    safe_route = urllib.parse.quote(route_name)
    url = f"{TDX_BASIC_URL}/v2/Bus/EstimatedTimeOfArrival/City/{city}/{safe_route}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT
    }
    params = {
        "$format": "JSON"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            res = r.json()
            formatted_etas = []
            status_messages = {0: "正常", 1: "尚未發車", 2: "交管不停靠", 3: "末班車已過", 4: "今日未營運"}
            for item in res:
                status = item.get("StopStatus", 0)
                est_time = item.get("EstimateTime")
                r_name = item.get("RouteName", {}).get("Zh_tw", "")
                direction = item.get("Direction", 0)
                stop_uid = item.get("StopUID", "")
                stop_name = item.get("StopName", {}).get("Zh_tw", "")
                
                if status == 0 and est_time is not None:
                    minutes = est_time // 60
                    msg = "即將到站" if minutes == 0 else f"{minutes} 分鐘"
                else:
                    msg = status_messages.get(status, "未知狀態")
                    
                formatted_etas.append({
                    "RouteName": r_name,
                    "Direction": direction,
                    "StopUID": stop_uid,
                    "StopName": stop_name,
                    "EstimateTime": est_time,
                    "StopStatus": status,
                    "Message": msg
                })
            return formatted_etas
        logger.error(f"ETA for route {route_name} failed: status code {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.error(f"Exception during ETA for route {route_name}: {e}", exc_info=True)
    return []

def get_city_stop_of_route(token: str, city: str) -> List[Dict[str, Any]]:
    """Get all stop sequences for a city (cache first)."""
    from twbus.cache import cache
    cache_key = f"city_stop_of_route:{city}"
    cached = cache.get(cache_key)
    if cached:
        return cached
        
    url = f"{TDX_BASIC_URL}/v2/Bus/StopOfRoute/City/{city}"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT
    }
    params = {
        "$format": "JSON"
    }
    
    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        if r.status_code == 200:
            data = r.json()
            # Cache for 24 hours (86400 seconds)
            cache.set(cache_key, data, custom_expiry=86400)
            return data
        logger.error(f"StopOfRoute failed for city {city}: status {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.error(f"Exception fetching city StopOfRoute: {e}", exc_info=True)
    return []

def find_matching_routes(token: str, start_lat: float, start_lon: float, dest_lat: float, dest_lon: float, radius: int = 500) -> List[Dict[str, Any]]:
    """
    Find common bus routes that go from the start coordinate to the destination coordinate.
    Checks that the start stop occurs before the destination stop in the route stop sequence.
    """
    start_stops = get_nearby_stops(token, start_lat, start_lon, radius)
    dest_stops = get_nearby_stops(token, dest_lat, dest_lon, radius)
    
    if not start_stops or not dest_stops:
        logger.warning("No nearby starting stops or destination stops found.")
        return []
        
    # Extract StopUIDs
    start_uids = {s["StopUID"] for s in start_stops if s.get("StopUID")}
    dest_uids = {d["StopUID"] for d in dest_stops if d.get("StopUID")}
    
    if not start_uids or not dest_uids:
        return []
        
    # Get all cities involved in starting stops
    cities = {CITY_CODE_TO_NAME.get(s.get("LocationCityCode")) for s in start_stops if s.get("LocationCityCode")}
    cities.discard(None)
    
    matching_routes = []
    
    for city_name in cities:
        routes_data = get_city_stop_of_route(token, city_name)
        if not routes_data:
            continue
            
        for route in routes_data:
            route_uid = route.get("RouteUID")
            route_name = route.get("RouteName", {}).get("Zh_tw", "")
            direction = route.get("Direction", 0)
            stops = route.get("Stops", [])
            
            start_candidates = []
            dest_candidates = []
            
            for stop in stops:
                stop_uid = stop.get("StopUID")
                if stop_uid in start_uids:
                    start_candidates.append(stop)
                if stop_uid in dest_uids:
                    dest_candidates.append(stop)
                    
            if start_candidates and dest_candidates:
                valid_pairs = []
                for s_cand in start_candidates:
                    s_seq = s_cand.get("StopSequence")
                    for d_cand in dest_candidates:
                        d_seq = d_cand.get("StopSequence")
                        if s_seq is not None and d_seq is not None and s_seq < d_seq:
                            valid_pairs.append((s_cand, d_cand, s_seq, d_seq))
                            
                if valid_pairs:
                    valid_pairs.sort(key=lambda x: x[3] - x[2])
                    best_s, best_d, s_seq, d_seq = valid_pairs[0]
                    
                    matching_routes.append({
                        "RouteUID": route_uid,
                        "RouteName": route_name,
                        "Direction": direction,
                        "City": city_name,
                        "StartStopUID": best_s.get("StopUID"),
                        "StartStopName": best_s.get("StopName", {}).get("Zh_tw", ""),
                        "StartStopSeq": s_seq,
                        "DestStopUID": best_d.get("StopUID"),
                        "DestStopName": best_d.get("StopName", {}).get("Zh_tw", ""),
                        "DestStopSeq": d_seq,
                        "StopCount": d_seq - s_seq
                    })
            
    return matching_routes

