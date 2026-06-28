import os
import sys
import logging
from typing import Optional, List, Dict, Any

# Ensure the src directory is in the path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Import modules from src
from ubike import api as ubike_api
from twbus import api as twbus_api
from places import api as places_api
from jptrain import api as jptrain_api
from jptrain.formatter import to_traditional_chinese, get_status_info
from tw_weather import api as weather_api
from tw_weather.cache import cache as weather_cache
from jp_weather import api as jp_weather_api
from jp_weather.suncalc import get_sun_times as get_jp_sun_times
from jp_weather.formatter import get_weather_info as get_jp_weather_info, get_weekday_ch as get_jp_weekday_ch, get_wind_direction_arrow as get_jp_wind_direction_arrow

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("hermes-web-server")

app = FastAPI(
    title="Hermes Go Web Dashboard API",
    description="Backend API for querying Japan railways and Taiwan TDX transport info",
    version="0.3.0"
)

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # During development we allow everything
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- Helper Structs -----------------
class GPSParseRequest(BaseModel):
    text: str

# ----------------- Endpoints -----------------

@app.post("/api/utils/parse-gps")
def parse_gps(req: GPSParseRequest):
    """
    Parse latitude and longitude from text or Google Maps URLs.
    """
    try:
        coords = ubike_api.parse_gps_input(req.text)
        if not coords:
            # Try twbus coordinator parser as fallback
            coords = twbus_api.parse_coordinates(req.text)
            
        if coords:
            return {"status": "success", "lat": coords[0], "lon": coords[1]}
        return {"status": "fail", "message": "Could not parse coordinates from the input"}
    except Exception as e:
        logger.error(f"Error parsing GPS: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/ubike/nearby")
def get_ubike_nearby(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: int = Query(200, description="Search radius in meters")
):
    """
    Fetch nearby YouBike stations and merge them with their real-time availability.
    """
    try:
        # Get TDX token
        token_info = ubike_api.get_tdx_token()
        if not token_info:
            raise HTTPException(status_code=400, detail="Failed to fetch TDX authentication token. Please verify TDX_CLIENT_ID and TDX_CLIENT_SECRET.")
        
        token = token_info["access_token"]
        
        # Fetch station info & availability
        stations = ubike_api.get_nearby_stations(token, lat, lon, radius)
        availability = ubike_api.get_nearby_availability(token, lat, lon, radius)
        
        # Merge availability into stations by StationUID
        avail_map = {item["StationUID"]: item for item in availability}
        
        merged_stations = []
        for station in stations:
            uid = station["StationUID"]
            station_avail = avail_map.get(uid, {})
            
            merged_stations.append({
                "uid": uid,
                "name": station.get("StationName", {}).get("Zh_tw", "未知站點"),
                "address": station.get("StationAddress", {}).get("Zh_tw", ""),
                "lat": station.get("StationPosition", {}).get("PositionLat", 0.0),
                "lon": station.get("StationPosition", {}).get("PositionLon", 0.0),
                "capacity": station.get("BikesCapacity", 0),
                "available_rent_bikes": station_avail.get("AvailableRentBikes", 0),
                "available_return_bikes": station_avail.get("AvailableReturnBikes", 0),
                "service_status": station_avail.get("ServiceStatus", 1), # 1: Active, 0: Suspended
                "update_time": station_avail.get("UpdateTime", "")
            })
            
        return {"status": "success", "data": merged_stations}
    except Exception as e:
        logger.error(f"Error fetching nearby YouBike: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/twbus/nearby")
def get_twbus_nearby(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: int = Query(500, description="Search radius in meters")
):
    """
    Get nearby bus stops, grouped by StopName/Position, and fetch dynamic ETA.
    """
    try:
        token_info = twbus_api.get_tdx_token()
        if not token_info:
            raise HTTPException(status_code=400, detail="Failed to fetch TDX authentication token.")
        
        token = token_info["access_token"]
        
        # 1. Get raw nearby stops (within radius)
        raw_stops = twbus_api.get_nearby_stops(token, lat, lon, radius)
        if not raw_stops:
            return {"status": "success", "data": []}
            
        # Group stops by StopUID or LocationCityCode to batch request ETAs
        city_groups = {}
        for stop in raw_stops:
            city_code = stop.get("LocationCityCode", "TPE")
            city_name = twbus_api.CITY_CODE_TO_NAME.get(city_code, "Taipei")
            
            if city_name not in city_groups:
                city_groups[city_name] = []
            city_groups[city_name].append(stop)
            
        # Fetch ETAs for each city group
        eta_map = {}
        for city, stops in city_groups.items():
            stop_uids = [s["StopUID"] for s in stops]
            try:
                etas = twbus_api.get_estimated_time_of_arrival_for_stops(token, city, stop_uids)
                for eta in etas:
                    stop_uid = eta.get("StopUID")
                    route_name = eta.get("RouteName", {}).get("Zh_tw", "")
                    # EstimateTime is in seconds.
                    est_time = eta.get("EstimateTime")
                    stop_status = eta.get("StopStatus", 0) # 0: normal, 1: no service, 2: not start...
                    
                    if stop_uid not in eta_map:
                        eta_map[stop_uid] = []
                        
                    eta_map[stop_uid].append({
                        "route_name": route_name,
                        "estimate_time": est_time,
                        "status": stop_status,
                        "direction": eta.get("Direction", 0)
                    })
            except Exception as e:
                logger.error(f"Failed to fetch ETAs for city {city}: {e}")
                
        # Consolidate results into stop coordinates
        grouped_stops = []
        for stop in raw_stops:
            stop_uid = stop["StopUID"]
            grouped_stops.append({
                "uid": stop_uid,
                "name": stop.get("StopName", {}).get("Zh_tw", "未知站牌"),
                "lat": stop.get("StopPosition", {}).get("PositionLat", 0.0),
                "lon": stop.get("StopPosition", {}).get("PositionLon", 0.0),
                "address": stop.get("Address", ""),
                "etas": eta_map.get(stop_uid, [])
            })
            
        return {"status": "success", "data": grouped_stops}
    except Exception as e:
        logger.error(f"Error fetching nearby Bus: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/twbus/route")
def get_twbus_route(
    start_lat: float = Query(..., description="Start Latitude"),
    start_lon: float = Query(..., description="Start Longitude"),
    dest: str = Query(..., description="Destination Address/Name"),
    radius: int = Query(500, description="Walking search radius in meters")
):
    """
    Search direct bus routes from start coords to destination.
    """
    try:
        # Geocode destination
        dest_geo = twbus_api.geocode_address(dest)
        if not dest_geo:
            raise HTTPException(status_code=400, detail=f"Could not resolve destination '{dest}' into geographic coordinates.")
            
        dest_lat = float(dest_geo["lat"])
        dest_lon = float(dest_geo["lon"])
        
        token_info = twbus_api.get_tdx_token()
        if not token_info:
            raise HTTPException(status_code=400, detail="Failed to fetch TDX authentication token.")
            
        token = token_info["access_token"]
        
        routes = twbus_api.find_matching_routes(token, start_lat, start_lon, dest_lat, dest_lon, radius)
        
        # Enforce clean return objects
        formatted_routes = []
        for r in routes:
            formatted_routes.append({
                "route_name": r.get("RouteName", {}).get("Zh_tw", ""),
                "start_stop": r.get("StartStopName", ""),
                "dest_stop": r.get("DestStopName", ""),
                "stops_count": r.get("StopsCount", 0),
                "direction": r.get("Direction", 0),
                "eta": r.get("ETA") # EstimateTime in seconds
            })
            
        return {
            "status": "success",
            "dest_coords": {"lat": dest_lat, "lon": dest_lon},
            "data": formatted_routes
        }
    except Exception as e:
        logger.error(f"Error searching bus route: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/places/nearby")
def get_places_nearby(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius: int = Query(500, description="Search radius in meters"),
    type_filter: Optional[str] = Query(None, alias="type", description="Search type (e.g. 咖啡廳, 餐廳, 酒吧, 景點)"),
    lang: str = Query("zh-TW", description="Result language")
):
    """
    Search nearby food & attractions using Google Places API.
    """
    api_key = os.getenv("GOOGLE_PLACES_API_KEY")
    if not api_key:
         raise HTTPException(status_code=400, detail="GOOGLE_PLACES_API_KEY is not configured in backend environment variables.")
         
    try:
        places = places_api.get_nearby_places(
            api_key=api_key,
            lat=lat,
            lon=lon,
            radius=radius,
            type_input=type_filter,
            language=lang
        )
        
        formatted_places = []
        for p in places:
            formatted_places.append({
                "name": p.get("name", "未命名地點"),
                "lat": p.get("geometry", {}).get("location", {}).get("lat", 0.0),
                "lon": p.get("geometry", {}).get("location", {}).get("lng", 0.0),
                "rating": p.get("rating", 0.0),
                "user_ratings_total": p.get("user_ratings_total", 0),
                "vicinity": p.get("vicinity", ""),
                "types": p.get("types", []),
                "open_now": p.get("opening_hours", {}).get("open_now", None)
            })
            
        return {"status": "success", "data": formatted_places}
    except Exception as e:
        logger.error(f"Error querying nearby places: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jptrain/areas")
def get_jp_areas():
    """
    Get all Japan train service areas (e.g. 関東, 関西).
    """
    try:
        areas = jptrain_api.get_areas()
        return {"status": "success", "data": areas}
    except Exception as e:
        logger.error(f"Error fetching Japan train areas: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jptrain/status")
def get_jp_status(area_code: str = Query(..., description="Area code, e.g. kanto, kansai")):
    """
    Get live delay status of railways in a Japanese region.
    """
    try:
        status_info = jptrain_api.get_area_status(area_code)
        routes = status_info.get("routes", [])
        update_time = status_info.get("update_time", "")
        
        # Resolve area name dynamically
        area_name = area_code
        try:
            areas = jptrain_api.get_areas()
            for a in areas:
                if a["code"] == area_code:
                    area_name = to_traditional_chinese(a["name"])
                    break
        except Exception:
            pass

        formatted_lines = []
        for line in routes:
            company = to_traditional_chinese(line.get("operator", "未知"))
            name = to_traditional_chinese(line.get("route", ""))
            raw_status = line.get("status", "")
            
            # Resolve status translation and type styling
            status_text, _, color_tag = get_status_info(raw_status)
            status_type = "normal" if color_tag == "green" else "delay"
            
            detail_info = to_traditional_chinese(line.get("detail", ""))
            
            formatted_lines.append({
                "name": name,
                "company": company,
                "status": status_text,
                "status_type": status_type,
                "detail_info": detail_info,
                "update_time": to_traditional_chinese(update_time)
            })
            
        return {
            "status": "success",
            "area_name": area_name,
            "data": formatted_lines
        }
    except Exception as e:
        logger.error(f"Error fetching Japan train status: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jptrain/route")
def get_jp_route(
    from_station: str = Query(..., description="Departure Station"),
    to_station: str = Query(..., description="Destination Station"),
    date: Optional[str] = Query(None, description="Date (YYYYMMDD)"),
    time_str: Optional[str] = Query(None, alias="time", description="Time (HHMM)")
):
    """
    Plan a train journey between stations in Japan.
    """
    import re
    try:
        res = jptrain_api.get_route_search(from_station, to_station, date, time_str)
        routes = res.get("routes", [])
        
        formatted_routes = []
        for r in routes:
            # 1. Parse time_required
            time_required = "未知"
            time_info = r.get("time", "")
            match_time = re.search(r'\((\d+)分\)', time_info)
            if match_time:
                time_required = match_time.group(1)
            else:
                time_required = to_traditional_chinese(time_info)
                
            # 2. Parse fare
            fare = "未知"
            fare_info = r.get("fare", "")
            match_fare = re.search(r'([\d,]+)円', fare_info)
            if match_fare:
                fare = match_fare.group(1)
            else:
                fare = fare_info.replace("円", "")
                
            # 3. Parse transfer_count
            transfer_count = 0
            transfer_info = r.get("transfer", "")
            match_transfer = re.search(r'(\d+)', transfer_info)
            if match_transfer:
                transfer_count = int(match_transfer.group(1))
                
            # 4. Parse steps from segments
            segments = r.get("segments", [])
            steps = []
            for idx, seg in enumerate(segments):
                if seg["type"] == "station":
                    station_name = to_traditional_chinese(seg.get("name", ""))
                    raw_time = seg.get("time", "")
                    # Translate "発" -> "發", "着" -> "抵達"
                    time_str_val = to_traditional_chinese(raw_time).replace("発", "發").replace("着", "抵達")
                    
                    line_name = None
                    if idx + 1 < len(segments) and segments[idx+1]["type"] == "transport":
                        line_name = to_traditional_chinese(segments[idx+1].get("name", ""))
                        
                    steps.append({
                        "station_name": station_name,
                        "departure_time": time_str_val,
                        "line_name": line_name
                    })
                    
            formatted_routes.append({
                "time_required": time_required,
                "fare": fare,
                "transfer_count": transfer_count,
                "steps": steps
            })
            
        return {
            "status": "success",
            "from": res.get("from", from_station),
            "to": res.get("to", to_station),
            "data": formatted_routes
        }
    except Exception as e:
        logger.error(f"Error searching Japan route: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ----------------- Weather Endpoints -----------------

@app.get("/api/weather/check")
def get_weather_check(
    location: str = Query("臺北市信義區", description="Location name or GPS coordinates"),
    cache_time: int = Query(900, description="Cache TTL in seconds")
):
    """
    Get 3-day weather forecast and umbrella advice for a location.
    """
    api_key = os.getenv("CWA_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="CWA_API_KEY is not configured in backend environment variables.")
        
    try:
        loc_res = weather_api.resolve_location(location)
        if not loc_res:
            raise HTTPException(status_code=400, detail="Could not resolve the specified location.")
            
        county, district, resolved_lat, resolved_lon = loc_res
        
        # County Fallback
        if not district:
            dataset_id = weather_api.COUNTY_DATASET_MAP.get(county)
            if not dataset_id:
                raise HTTPException(status_code=400, detail=f"County '{county}' is not supported by CWA.")
                
            cache_key = f"cwa_county_{dataset_id}"
            weather_data = weather_cache.get(cache_key)
            if not weather_data:
                raw_data = weather_api.fetch_cwa_weather(api_key, "F-C0032-001", county)
                weather_data = weather_api.parse_county_weather_json(raw_data, county)
                weather_cache.set(cache_key, weather_data, custom_expiry=cache_time)
                
            return {
                "status": "success",
                "level": "county",
                "county": county,
                "data": weather_data
            }
        else:
            dataset_id = weather_api.COUNTY_DATASET_MAP.get(county)
            if not dataset_id:
                raise HTTPException(status_code=400, detail=f"County '{county}' is not supported by CWA.")
                
            cache_key = f"cwa_weather_{dataset_id}_{district}"
            weather_data = weather_cache.get(cache_key)
            if not weather_data:
                raw_data = weather_api.fetch_cwa_weather(api_key, dataset_id, district)
                weather_data = weather_api.parse_weather_json(raw_data, district)
                weather_cache.set(cache_key, weather_data, custom_expiry=cache_time)
                
            return {
                "status": "success",
                "level": "town",
                "county": county,
                "district": district,
                "coords": {"lat": resolved_lat, "lon": resolved_lon},
                "data": weather_data
            }
    except Exception as e:
        logger.error(f"Error checking weather: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/weather/hourly")
def get_weather_hourly(
    location: str = Query("臺北市信義區", description="Location name or GPS coordinates"),
    all_hours: bool = Query(False, description="Whether to show all 48 hours instead of today/24h filter"),
    cache_time: int = Query(900, description="Cache TTL in seconds")
):
    """
    Get 48h hourly forecast (temp, apparent temp, RH, rain prob, wind direction & speed).
    """
    api_key = os.getenv("CWA_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="CWA_API_KEY is not configured in backend environment variables.")
        
    try:
        loc_res = weather_api.resolve_location(location)
        if not loc_res:
            raise HTTPException(status_code=400, detail="Could not resolve the specified location.")
            
        county, district, resolved_lat, resolved_lon = loc_res
        
        # If district is missing, resolve first district
        if not district:
            base_id = weather_api.COUNTY_DATASET_MAP.get(county)
            if not base_id:
                raise HTTPException(status_code=400, detail=f"County '{county}' is not supported.")
            raw_data = weather_api.fetch_cwa_weather(api_key, base_id, "")
            records = raw_data.get("records", {})
            locations = records.get("Locations", [])
            if locations and locations[0].get("Location"):
                district = locations[0].get("Location", [])[0].get("LocationName")
            else:
                raise HTTPException(status_code=400, detail="Failed to resolve district for county.")
                
        base_id = weather_api.COUNTY_DATASET_MAP.get(county)
        dataset_id = base_id
        
        cache_key = f"cwa_weather_{dataset_id}_all"
        weather_data = weather_cache.get(cache_key)
        if not weather_data:
            weather_data = weather_api.fetch_cwa_weather(api_key, dataset_id, district)
            weather_cache.set(cache_key, weather_data, custom_expiry=cache_time)
            
        hourly_records = weather_api.parse_hourly_weather_json(weather_data, district)
        
        # Filter logic matching cli
        from datetime import datetime, timezone, timedelta
        tz = timezone(timedelta(hours=8))
        now = datetime.now(tz)
        today_midnight = now.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        if all_hours:
            filtered_hours = [r for r in hourly_records if datetime.fromisoformat(r["datetime"]) >= now - timedelta(minutes=30)]
            title = "未來 48 小時完整預報"
        else:
            filtered_hours = []
            for r in hourly_records:
                dt = datetime.fromisoformat(r["datetime"])
                if dt >= now - timedelta(minutes=30) and dt <= today_midnight:
                    filtered_hours.append(r)
            
            showing_24h = False
            if len(filtered_hours) < 6:
                filtered_hours = []
                showing_24h = True
                end_time = now + timedelta(hours=24)
                for r in hourly_records:
                    dt = datetime.fromisoformat(r["datetime"])
                    if dt >= now - timedelta(minutes=30) and dt <= end_time:
                        filtered_hours.append(r)
            title = "今日剩餘時段預報" if not showing_24h else "未來 24 小時精細預報"
            
        return {
            "status": "success",
            "county": county,
            "district": district,
            "title": title,
            "data": filtered_hours
        }
    except Exception as e:
        logger.error(f"Error checking hourly weather: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/weather/rain")
def get_weather_rain(
    location: str = Query("臺北市信義區", description="Location name or GPS coordinates"),
    cache_time: int = Query(600, description="Cache TTL in seconds")
):
    """
    Get live rain observation data, rain rate label, alerts, and 2-day outlook.
    """
    api_key = os.getenv("CWA_API_KEY")
    if not api_key:
        raise HTTPException(status_code=400, detail="CWA_API_KEY is not configured in backend environment variables.")
        
    try:
        loc_res = weather_api.resolve_location(location)
        if not loc_res:
            raise HTTPException(status_code=400, detail="Could not resolve the specified location.")
            
        county, district, resolved_lat, resolved_lon = loc_res
        
        if resolved_lat == 0.0 or resolved_lon == 0.0:
            resolved_lat, resolved_lon = 25.0339, 121.5644
            res = weather_api.geocode_address(county)
            if res:
                resolved_lat, resolved_lon = res[2], res[3]
                
        # Fetch live rain data
        cache_key = "cwa_rain_observations"
        weather_data = weather_cache.get(cache_key)
        if not weather_data:
            weather_data = weather_api.fetch_cwa_rain_data(api_key)
            weather_cache.set(cache_key, weather_data, custom_expiry=cache_time)
            
        nearest_station, distance = weather_api.find_nearest_rain_station(weather_data, resolved_lat, resolved_lon)
        
        st_name = nearest_station.get("StationName", "未知")
        st_id = nearest_station.get("StationId", "未知")
        obs_time = nearest_station.get("ObsTime", {}).get("DateTime", "未知")
        
        # Extract station coordinates
        coords = nearest_station.get("GeoInfo", {}).get("Coordinates", [])
        st_lat = resolved_lat
        st_lon = resolved_lon
        if coords:
            for coord in coords:
                if coord.get("CoordinateName") == "WGS84":
                    try:
                        st_lat = float(coord.get("StationLatitude", 0.0))
                        st_lon = float(coord.get("StationLongitude", 0.0))
                    except ValueError:
                        pass
                    break
        
        elements = nearest_station.get("RainfallElement", {})
        r_10m = elements.get("Past10Min", {}).get("Precipitation", "0.0")
        r_1h = elements.get("Past1hr", {}).get("Precipitation", "0.0")
        r_3h = elements.get("Past3hr", {}).get("Precipitation", "0.0")
        r_24h = elements.get("Past24hr", {}).get("Precipitation", "0.0")
        r_today = elements.get("Now", {}).get("Precipitation", "0.0")
        
        f_1h = weather_api.format_rain_value(r_1h)
        f_3h = weather_api.format_rain_value(r_3h)
        f_24h = weather_api.format_rain_value(r_24h)
        
        warning_name, warning_color = weather_api.get_rain_alert_level(f_1h, f_3h, f_24h)
        intensity_label = weather_api.get_rain_intensity_label(f_1h)
        
        # Fetch future rain forecast (using QPF estimates)
        fc_list = []
        try:
            town_dataset_id = weather_api.COUNTY_DATASET_MAP.get(county)
            if town_dataset_id:
                cache_key_fc = f"weather_qpf_forecast_{town_dataset_id}_{district}"
                fc_data = weather_cache.get(cache_key_fc)
                if not fc_data:
                    fc_raw = weather_api.fetch_cwa_weather(api_key, town_dataset_id, district, element_names="PoP3h,Wx")
                    fc_data = weather_api.parse_3h_forecast_for_rain(fc_raw, district)
                    weather_cache.set(cache_key_fc, fc_data, custom_expiry=cache_time)
                
                for item in fc_data[:4]:
                    wx = item.get("wx_summary", "未知")
                    pop = item.get("pop", 0)
                    min_mm = item.get("min_mm", 0.0)
                    max_mm = item.get("max_mm", 0.0)
                    if max_mm <= 0.0:
                        mm_str = "無雨 (0 mm)"
                    elif min_mm == max_mm:
                        mm_str = f"{min_mm:.1f} mm"
                    else:
                        mm_str = f"{min_mm:.1f} ~ {max_mm:.1f} mm"
                    fc_list.append({
                        "period": item.get("period_name", ""),
                        "wx": wx,
                        "pop": pop,
                        "est_volume": mm_str
                    })
        except Exception:
            pass
            
        return {
            "status": "success",
            "county": county,
            "district": district,
            "station": {
                "name": st_name,
                "id": st_id,
                "distance_km": round(distance, 2),
                "obs_time": obs_time,
                "lat": st_lat,
                "lon": st_lon
            },
            "observations": {
                "past_10m": weather_api.display_rain_value(r_10m),
                "past_1h": weather_api.display_rain_value(r_1h),
                "past_3h": weather_api.display_rain_value(r_3h),
                "past_24h": weather_api.display_rain_value(r_24h),
                "today": weather_api.display_rain_value(r_today),
                "intensity_label": intensity_label
            },
            "alert": {
                "level": warning_name,
                "color": warning_color
            },
            "forecast": fc_list
        }
    except Exception as e:
        logger.error(f"Error checking rain observations: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/jpweather/weather")
def get_jp_weather(
    location: str = Query("東京", description="Location name, zip code, or GPS coordinates")
):
    """
    Get current weather, hourly forecast (next 24h), weekly forecast, and photography index for Japan/global locations.
    """
    from datetime import datetime, timezone as dt_timezone
    from zoneinfo import ZoneInfo
    
    try:
        # Resolve location
        # 1. Parse GPS first
        gps_coords = jp_weather_api.parse_gps(location)
        if gps_coords:
            lat, lon = gps_coords
            loc_data = jp_weather_api.reverse_geocode(lat, lon)
        else:
            # 2. Text geocoding
            locations = jp_weather_api.geocode(location)
            if not locations:
                raise HTTPException(status_code=400, detail="Could not resolve the specified Japanese or global location.")
            loc_data = locations[0]
            
        lat = loc_data.get("latitude")
        lon = loc_data.get("longitude")
        timezone_str = loc_data.get("timezone", "Asia/Tokyo")
        
        # Fetch weather data
        weather_raw = jp_weather_api.get_weather(lat, lon, timezone_str)
        if not weather_raw:
            raise HTTPException(status_code=500, detail="Failed to fetch weather data from Open-Meteo API.")
            
        # Parse current weather
        curr = weather_raw.get("current", {})
        temp = curr.get("temperature_2m")
        humidity = curr.get("relative_humidity_2m")
        apparent_temp = curr.get("apparent_temperature")
        precip = curr.get("precipitation", 0.0)
        wind_speed = curr.get("wind_speed_10m")
        wind_dir = curr.get("wind_direction_10m")
        w_code = curr.get("weather_code", 0)
        
        weather_desc, weather_emoji, weather_color = get_jp_weather_info(w_code)
        wind_arrow = get_jp_wind_direction_arrow(wind_dir)
        
        current_formatted = {
            "temperature": temp,
            "apparent_temperature": apparent_temp,
            "humidity": humidity,
            "precipitation": precip,
            "wind_speed": wind_speed,
            "wind_direction": wind_dir,
            "wind_direction_arrow": wind_arrow,
            "weather_code": w_code,
            "weather_desc": weather_desc,
            "weather_emoji": weather_emoji,
            "weather_color": weather_color,
            "time": curr.get("time", "")
        }
        
        # Parse hourly trend (next 24h, step 3)
        hourly_raw = weather_raw.get("hourly", {})
        h_times = hourly_raw.get("time", [])
        h_temps = hourly_raw.get("temperature_2m", [])
        h_pops = hourly_raw.get("precipitation_probability", [])
        h_codes = hourly_raw.get("weather_code", [])
        
        hourly_list = []
        for i in range(0, min(24, len(h_times)), 3):
            if i < len(h_times):
                h_code = h_codes[i] if i < len(h_codes) else 0
                h_desc, h_emoji, h_color = get_jp_weather_info(h_code)
                t_str = h_times[i].split("T")[1] if "T" in h_times[i] else h_times[i]
                hourly_list.append({
                    "time": t_str,
                    "temp": h_temps[i] if i < len(h_temps) else None,
                    "pop": h_pops[i] if i < len(h_pops) else 0,
                    "weather_desc": h_desc,
                    "weather_emoji": h_emoji,
                    "weather_color": h_color
                })
                
        # Parse daily forecast (7 days)
        daily_raw = weather_raw.get("daily", {})
        d_times = daily_raw.get("time", [])
        d_codes = daily_raw.get("weather_code", [])
        d_maxs = daily_raw.get("temperature_2m_max", [])
        d_mins = daily_raw.get("temperature_2m_min", [])
        d_precips = daily_raw.get("precipitation_sum", [])
        d_pops = daily_raw.get("precipitation_probability_max", [])
        d_winds = daily_raw.get("wind_speed_10m_max", [])
        d_uvs = daily_raw.get("uv_index_max", [])
        
        daily_list = []
        for i in range(len(d_times)):
            d_code = d_codes[i] if i < len(d_codes) else 0
            d_desc, d_emoji, d_color = get_jp_weather_info(d_code)
            date_val = d_times[i]
            formatted_date = date_val[5:] if len(date_val) >= 10 else date_val
            weekday_ch = get_jp_weekday_ch(date_val)
            
            daily_list.append({
                "date": formatted_date,
                "weekday": weekday_ch,
                "temp_max": d_maxs[i] if i < len(d_maxs) else None,
                "temp_min": d_mins[i] if i < len(d_mins) else None,
                "pop": d_pops[i] if i < len(d_pops) else 0,
                "precipitation_sum": d_precips[i] if i < len(d_precips) else 0.0,
                "wind_speed_max": d_winds[i] if i < len(d_winds) else 0.0,
                "uv_index": d_uvs[i] if i < len(d_uvs) else 0.0,
                "weather_desc": d_desc,
                "weather_emoji": d_emoji,
                "weather_color": d_color
            })
            
        # Parse photography/sun times
        try:
            tz_info = ZoneInfo(timezone_str)
        except Exception:
            tz_info = dt_timezone.utc
            
        now_dt = datetime.now(tz_info)
        sun_times = get_jp_sun_times(lat, lon, now_dt)
        polar_status = sun_times.get("polar_status", "normal")
        
        stars_am, desc_am = 3, "無資料"
        stars_pm, desc_pm = 3, "無資料"
        
        if polar_status == "normal" and hourly_raw:
            try:
                stars_am, desc_am = jp_weather_api.calculate_photography_rating(
                    sun_times.get("blue_hour_am_start"),
                    sun_times.get("golden_hour_am_end"),
                    hourly_raw,
                    timezone_str
                )
                stars_pm, desc_pm = jp_weather_api.calculate_photography_rating(
                    sun_times.get("golden_hour_pm_start"),
                    sun_times.get("blue_hour_pm_end"),
                    hourly_raw,
                    timezone_str
                )
            except Exception:
                pass
                
        def format_time_helper(dt):
            if not dt:
                return "--:--"
            if dt.tzinfo is None:
                return dt.strftime("%H:%M")
            return dt.astimezone(tz_info).strftime("%H:%M")
            
        photo_data = {
            "polar_status": polar_status,
            "stars_am": stars_am,
            "desc_am": desc_am,
            "stars_pm": stars_pm,
            "desc_pm": desc_pm,
            "am": {
                "blue_start": format_time_helper(sun_times.get("blue_hour_am_start")),
                "blue_end": format_time_helper(sun_times.get("blue_hour_am_end")),
                "golden_start": format_time_helper(sun_times.get("golden_hour_am_start")),
                "golden_end": format_time_helper(sun_times.get("golden_hour_am_end")),
                "sunrise": format_time_helper(sun_times.get("sunrise"))
            },
            "pm": {
                "sunset": format_time_helper(sun_times.get("sunset")),
                "golden_start": format_time_helper(sun_times.get("golden_hour_pm_start")),
                "golden_end": format_time_helper(sun_times.get("golden_hour_pm_end")),
                "blue_start": format_time_helper(sun_times.get("blue_hour_pm_start")),
                "blue_end": format_time_helper(sun_times.get("blue_hour_pm_end"))
            }
        }
        
        return {
            "status": "success",
            "location": {
                "name": loc_data.get("name"),
                "prefecture": loc_data.get("admin1"),
                "country": loc_data.get("country"),
                "country_code": loc_data.get("country_code"),
                "lat": lat,
                "lon": lon,
                "timezone": timezone_str
            },
            "coords": {"lat": lat, "lon": lon},
            "current": current_formatted,
            "hourly": hourly_list,
            "daily": daily_list,
            "photography": photo_data
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error checking Japan weather: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ----------------- Serve Frontend Assets -----------------

# Path to built frontend assets
frontend_dist = os.path.join(os.path.dirname(current_dir), "frontend", "dist")

if os.path.exists(frontend_dist):
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")
    
    @app.get("/{catchall:path}")
    def serve_frontend(catchall: str):
        # Prevent intercepting API routes
        if catchall.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")
        index_file = os.path.join(frontend_dist, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        raise HTTPException(status_code=404, detail="Index HTML not found")
else:
    @app.get("/")
    def read_root():
        return {
            "message": "Hermes Go API Server is running. Frontend has not been built yet. Please build the frontend inside the `/frontend` directory."
        }

if __name__ == "__main__":
    import uvicorn
    # Start the server on port 8000
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
