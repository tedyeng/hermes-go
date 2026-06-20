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
