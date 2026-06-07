import os
import click
import math
from rich.console import Console
from twbus import api
from twbus.cache import get_cached_token, set_cached_token, cache

# Force console width to 38 for mobile-only mode!
console = Console(width=38)

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

def get_token_or_fail() -> str:
    """Helper to retrieve cached TDX token or authenticate."""
    token = get_cached_token()
    if token:
        return token

    with console.status("[bold green]🔑 申請 TDX 權杖...[/bold green]"):
        token_data = api.get_tdx_token()
        
    if not token_data:
        console.print("[red]❌ 無法取得 TDX API token，請檢查 .env 的 tdx credentials。[/red]")
        raise click.ClickException("Authentication failed")
        
    set_cached_token(token_data)
    return token_data["access_token"]

@click.group(help="""\b
🚌 台灣公車 TDX 即時資訊查詢工具 (twbus CLI)
\b
使用範例 Examples:
\b
1. 顯示附近公車站牌與到站公車:
   twbus nearby --lat "北緯25°5′0″" --lon "東經121°34′43″"
   twbus nearby --lat 25.0833 --lon 121.5786
\b
2. 查詢特定公車到站時間:
   twbus eta --lat "北緯25°5′0″" --lon "東經121°34′43″" --route "307"
   twbus eta --lat 25.0833 --lon 121.5786 --route "307"
\b
3. 查詢直達目的地公車與乘車方案:
   twbus search --lat 25.0338 --lon 121.5298 --dest "台北101"
   twbus search --lat "北緯25°5′0″" --lon "東經121°34′43″" --dest "台北車站"
""")
def cli():
    pass

@cli.command()
@click.option("--lat", type=str, required=True, help="起點緯度 Latitude (支援十進位 or DMS)")
@click.option("--lon", type=str, required=True, help="起點經度 Longitude (支援十進位 or DMS)")
@click.option("--dest", type=str, required=True, help="目的地名稱或地址 (e.g. 台北101)")
@click.option("--radius", type=int, default=500, help="搜尋半徑 (公尺，預設 500)")
def search(lat, lon, dest, radius):
    """
    🔍 查詢從目前座標到指定目的地的公車路線
    """
    lat_val = api.parse_single_coordinate(lat)
    lon_val = api.parse_single_coordinate(lon)
    if lat_val is None:
        console.print(f"[red]❌ 緯度格式錯誤: {lat}[/red]")
        return
    if lon_val is None:
        console.print(f"[red]❌ 經度格式錯誤: {lon}[/red]")
        return
    lat, lon = lat_val, lon_val

    token = get_token_or_fail()
    
    # 1. Geocode destination
    with console.status(f"[bold cyan]🔍 解析「{dest}」座標...[/bold cyan]"):
        dest_info = api.geocode_address(dest)
        
    if not dest_info:
        console.print(f"[red]❌ 無法解析目的地「{dest}」的座標，請換個名稱。[/red]")
        return
        
    dest_lat = dest_info["lat"]
    dest_lon = dest_info["lon"]
    dest_name = dest_info["display_name"]
    
    console.print(f"[bold green]📍 地理資訊解析成功[/bold green]")
    console.print(f"• [bold]名稱[/bold]: {dest_name[:20]}...")
    console.print(f"• [bold]座標[/bold]: ({dest_lat:.4f}, {dest_lon:.4f})")
    
    # 2. Find matching routes
    with console.status("[bold yellow]🚌 搜尋直達公車路線...[/bold yellow]"):
        routes = api.find_matching_routes(token, lat, lon, dest_lat, dest_lon, radius)
        
    if not routes:
        console.print(f"[yellow]⚠️ 在 {radius}m 內找不到直達公車。[/yellow]")
        return
        
    # 3. Render routes & fetch real-time ETA
    console.print(f"\n[bold yellow]🚌 往「{dest}」的公車乘車方案[/bold yellow]")
    console.print("─" * 36)

    with console.status("[bold red]⏰ 讀取即時到站時間...[/bold red]"):
        for r in routes:
            eta_info = api.get_estimated_time_of_arrival(token, r["City"], r["RouteName"], r["StartStopUID"])
            eta_msg = eta_info["Message"] if eta_info else "暫無資料"
            
            console.print(f"[bold cyan]🚌 路線: {r['RouteName']}[/bold cyan]")
            console.print(f"• 上車: {r['StartStopName']}")
            console.print(f"• 下車: {r['DestStopName']}")
            console.print(f"• 乘車: {r['StopCount']} 站")
            console.print(f"• 到站: [bold red]{eta_msg}[/bold red]")
            console.print("─" * 36)

@cli.command()
@click.option("--lat", type=str, required=True, help="目前緯度 Latitude (支援十進位 or DMS)")
@click.option("--lon", type=str, required=True, help="目前經度 Longitude (支援十進位 or DMS)")
@click.option("--radius", type=int, default=500, help="搜尋半徑 (公尺，預設 500)")
def nearby(lat, lon, radius):
    """
    📍 顯示離該座標最近站牌的到站公車
    """
    lat_val = api.parse_single_coordinate(lat)
    lon_val = api.parse_single_coordinate(lon)
    if lat_val is None:
        console.print(f"[red]❌ 緯度格式錯誤: {lat}[/red]")
        return
    if lon_val is None:
        console.print(f"[red]❌ 經度格式錯誤: {lon}[/red]")
        return
    lat, lon = lat_val, lon_val

    token = get_token_or_fail()
    
    with console.status("[bold yellow]🚏 查詢附近公車站牌...[/bold yellow]"):
        stops = api.get_nearby_stops(token, lat, lon, radius)
        
    if not stops:
        console.print(f"[yellow]⚠️ 附近 {radius}m 內無公車站牌。[/yellow]")
        return
        
    # Group by StopName
    grouped_stops = {}
    for stop in stops:
        stop_name = stop.get("StopName", {}).get("Zh_tw", "未命名站牌")
        stop_pos = stop.get("StopPosition", {})
        stop_lat = stop_pos.get("PositionLat")
        stop_lon = stop_pos.get("PositionLon")
        
        dist = 99999.0
        if stop_lat is not None and stop_lon is not None:
            dist = calculate_distance(lat, lon, stop_lat, stop_lon)
            
        if stop_name not in grouped_stops:
            grouped_stops[stop_name] = {"distance": dist, "stops": []}
        grouped_stops[stop_name]["stops"].append(stop)
        if dist < grouped_stops[stop_name]["distance"]:
            grouped_stops[stop_name]["distance"] = dist
            
    # Sort groups by distance
    sorted_groups = sorted(grouped_stops.items(), key=lambda x: x[1]["distance"])
    
    # Collect all StopUIDs from the top 5 nearest groups
    target_uids = []
    for _, group in sorted_groups[:5]:
        for s in group["stops"]:
            if s.get("StopUID"):
                target_uids.append(s["StopUID"])
                
    # Batch query ETAs for all these stops (using the city of the nearest stop)
    eta_map = {}
    if sorted_groups and target_uids:
        first_stop = sorted_groups[0][1]["stops"][0]
        city_code = first_stop.get("LocationCityCode")
        city_name = api.CITY_CODE_TO_NAME.get(city_code)
        if city_name:
            with console.status("[bold red]⏰ 讀取即時到站時間...[/bold red]"):
                all_etas = api.get_estimated_time_of_arrival_for_stops(token, city_name, target_uids)
            for eta in all_etas:
                uid = eta["StopUID"]
                if uid not in eta_map:
                    eta_map[uid] = []
                eta_map[uid].append(eta)
                
    console.print(f"\n[bold yellow]🚏 附近公車站牌與路線 ({radius}m)[/bold yellow]")
    console.print("─" * 36)
    
    for stop_name, group in sorted_groups[:5]:
        dist_m = group["distance"]
        stop_list = group["stops"]
        
        console.print(f"[bold green]🚏 站牌: {stop_name}[/bold green] (約{dist_m:.0f}m)")
        console.print("─" * 15)
        
        has_any_eta = False
        for s in stop_list:
            stop_uid = s.get("StopUID")
            etas = eta_map.get(stop_uid, [])
            if etas:
                has_any_eta = True
                for eta in etas:
                    route_name = eta["RouteName"]
                    direction = eta["Direction"]
                    dir_text = "去程" if direction == 0 else "返程"
                    eta_msg = eta["Message"]
                    console.print(f"• {route_name} ({dir_text}) ➔ [bold red]{eta_msg}[/bold red]")
                    
        if not has_any_eta:
            console.print("[dim]• (無即時到站資料)[/dim]")
        console.print("─" * 36)

@cli.command()
@click.option("--lat", type=str, required=True, help="目前緯度 Latitude (支援十進位 or DMS)")
@click.option("--lon", type=str, required=True, help="目前經度 Longitude (支援十進位 or DMS)")
@click.option("--route", type=str, required=True, help="公車號碼 (e.g. 307)")
@click.option("--radius", type=int, default=500, help="搜尋半徑 (公尺，預設 500)")
def eta(lat, lon, route, radius):
    """
    🚌 輸入公車號碼後顯示該公車到站時間
    """
    lat_val = api.parse_single_coordinate(lat)
    lon_val = api.parse_single_coordinate(lon)
    if lat_val is None:
        console.print(f"[red]❌ 緯度格式錯誤: {lat}[/red]")
        return
    if lon_val is None:
        console.print(f"[red]❌ 經度格式錯誤: {lon}[/red]")
        return
    lat, lon = lat_val, lon_val

    token = get_token_or_fail()
    
    with console.status(f"[bold yellow]🔍 搜尋公車「{route}」站牌...[/bold yellow]"):
        stops = api.get_nearby_stops(token, lat, lon, radius)
        
    if not stops:
        console.print(f"[yellow]⚠️ 附近 {radius}m 內無公車站牌。[/yellow]")
        return
        
    # Filter stops by city code
    city_to_uids = {}
    for s in stops:
        stop_uid = s.get("StopUID")
        city_code = s.get("LocationCityCode")
        city_name = api.CITY_CODE_TO_NAME.get(city_code)
        if stop_uid and city_name:
            if city_name not in city_to_uids:
                city_to_uids[city_name] = []
            city_to_uids[city_name].append(s)
            
    if not city_to_uids:
        console.print(f"[yellow]⚠️ 附近 {radius}m 內無公車站牌。[/yellow]")
        return
        
    console.print(f"\n[bold yellow]⏰ 公車 {route} 附近站牌到站時間[/bold yellow]")
    console.print("─" * 36)
    
    found_any = False
    for city_name, city_stops in city_to_uids.items():
        with console.status(f"[bold yellow]⏰ 讀取 {city_name} 到站時間...[/bold yellow]"):
            etas = api.get_estimated_time_of_arrival_for_route(token, city_name, route)
            
        if not etas:
            continue
            
        # Match ETA stops with nearby stops
        nearby_uids = {s["StopUID"]: s for s in city_stops if s.get("StopUID")}
        
        for eta_item in etas:
            stop_uid = eta_item.get("StopUID")
            if stop_uid in nearby_uids:
                found_any = True
                stop_name = eta_item.get("StopName", "")
                direction = eta_item.get("Direction", 0)
                dir_text = "去程" if direction == 0 else "返程"
                eta_msg = eta_item.get("Message", "暫無資料")
                
                console.print(f"🚏 [bold green]{stop_name}[/bold green] ({dir_text})")
                console.print(f"   ➔ [bold red]{eta_msg}[/bold red]")
                console.print("─" * 36)
                
    if not found_any:
        console.print(f"[yellow]⚠️ 附近 {radius}m 內無 {route} 站牌。[/yellow]")

if __name__ == "__main__":
    cli()
