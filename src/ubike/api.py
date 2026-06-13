import os
import time
import logging
import requests
import urllib.parse
import re
from typing import List, Dict, Any, Optional, Tuple

# Custom exception for TDX API errors
class TdxApiError(Exception):
    """Raised when a TDX API request returns a non‑200 status."""
    pass
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
for env_path in [os.path.expanduser("~/.env"), "/opt/data/.env"]:
    if os.path.exists(env_path):
        load_dotenv(dotenv_path=env_path)

logger = logging.getLogger("ubike.api")

# TDX configurations
TDX_TOKEN_URL = "https://tdx.transportdata.tw/auth/realms/TDXConnect/protocol/openid-connect/token"
TDX_ADVANCED_URL = "https://tdx.transportdata.tw/api/advanced"
USER_AGENT = "hermes-go-bot-tedyeng-dev-testing-2026/1.0 (tedyeng.code@gmail.com)"

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
            expires_in = res.get("expires_in", 3600)
            return {
                "access_token": res.get("access_token"),
                "expires_at": time.time() + expires_in - 60 # buffer of 1 minute
            }
        logger.error(f"Failed to fetch TDX token: status code {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.error(f"Exception during TDX token fetch: {e}", exc_info=True)
    return None

def parse_gps_input(text: str) -> Optional[Tuple[float, float]]:
    """Parse latitude and longitude from a variety of formats.

    Returns a tuple (lat, lon) or ``None`` if parsing fails.
    """
    """
    Parse latitude and longitude from a variety of formats:
      - Shortened/Full Google Maps, Apple Maps, or Telegram shared location URLs
      - Raw coordinates inside copied text (Decimal or DMS formats)
    """
    text = text.strip()
    if "apple.com" in text or "apple.co" in text:
        return None
    
    # 1. Try URL parsing
    url_match = re.search(r'(https?://\S+)', text)
    if url_match:
        url = url_match.group(1)
        # Resolve short URLs (e.g. Google Maps maps.app.goo.gl)
        if "maps.app.goo.gl" in url or "app.goo.gl" in url or "short" in url:
            try:
                # Use a small timeout of 3 seconds to avoid blocking the CLI indefinitely
                r = requests.head(url, allow_redirects=True, timeout=3)
                # Verify the final URL points to a Google Maps domain before trusting it
                parsed = urllib.parse.urlparse(r.url)
                hostname = parsed.hostname or ""
                if not (hostname.endswith("google.com") or hostname.endswith("googleusercontent.com") or hostname.endswith("goo.gl")):
                    logger.warning(f"Short URL resolved to unexpected host '{hostname}'. Ignoring.")
                else:
                    url = r.url
            except Exception as e:
                logger.warning(f"Failed to resolve shortened URL: {e}")
        
        # Try extracting coordinates from URL path (e.g. /@25.033,121.564 or /place/25.033,121.564)
        path_coords = re.search(r'[/@](-?\d+\.\d+)\s*,\s*(-?\d+\.\d+)', url)
        if path_coords:
            try:
                lat, lon = float(path_coords.group(1)), float(path_coords.group(2))
                if -90 <= lat <= 90 and -180 <= lon <= 180:
                    return lat, lon
            except ValueError:
                pass
        
        # Try extracting coordinates from query params (e.g. ?q=25.033,121.564 or ?ll=25.033,121.564)
        try:
            parsed_url = urllib.parse.urlparse(url)
            qs = urllib.parse.parse_qs(parsed_url.query)
            for param in ["q", "query", "ll", "center", "loc"]:
                if param in qs:
                    val = qs[param][0]
                    # Parse decimal format in query parameter value
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

    # 2. Try generic decimal coordinates pattern search in raw text
    # (Matches e.g. "25.0339, 121.5644" or "緯度:25.033 經度:121.564" etc.)
    pattern = r'(-?\d+\.\d+)[,\s]+(-?\d+\.\d+)'
    matches = re.findall(pattern, text)
    for lat_str, lon_str in matches:
        try:
            lat = float(lat_str)
            lon = float(lon_str)
            
            # Since Taiwan coordinates are lat ~21-26, lon ~118-122, if they are swapped, 
            # we can automatically correct it.
            if 20.0 <= lon <= 27.0 and 110.0 <= lat <= 125.0:
                lat, lon = lon, lat
                
            if -90 <= lat <= 90 and -180 <= lon <= 180:
                return lat, lon
        except ValueError:
            pass

    # 3. Fallback to twbus DMS/decimal coordinate parser
    try:
        from twbus.api import parse_coordinates as twbus_parse
        res = twbus_parse(text)
        if res:
            return res
    except ImportError:
        pass

    return None

def get_nearby_stations(token: str, lat: float, lon: float, radius: int = 200) -> List[Dict[str, Any]]:
    """
    Get nearby YouBike stations using spatial filter on TDX advanced API.
    """
    url = f"{TDX_ADVANCED_URL}/v2/Bike/Station/NearBy"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT
    }
    params = {
        "$spatialFilter": f"nearby({lat}, {lon}, {radius})",
        "$format": "JSON"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        # Raise error for caller to handle
        raise TdxApiError(f"Nearby stations API failed: status code {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.error(f"Exception during nearby stations request: {e}", exc_info=True)
        raise TdxApiError(str(e))
    # No fallback return; callers should handle exceptions

def get_nearby_availability(token: str, lat: float, lon: float, radius: int = 200) -> List[Dict[str, Any]]:
    """
    Get nearby YouBike availability using spatial filter on TDX advanced API.
    """
    url = f"{TDX_ADVANCED_URL}/v2/Bike/Availability/NearBy"
    headers = {
        "Authorization": f"Bearer {token}",
        "User-Agent": USER_AGENT
    }
    params = {
        "$spatialFilter": f"nearby({lat}, {lon}, {radius})",
        "$format": "JSON"
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json()
        # Raise error for caller to handle
        raise TdxApiError(f"Nearby availability API failed: status code {r.status_code}, response: {r.text}")
    except Exception as e:
        logger.error(f"Exception during nearby availability request: {e}", exc_info=True)
        raise TdxApiError(str(e))
    # No fallback return; callers should handle exceptions
