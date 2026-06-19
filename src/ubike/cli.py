import click
import math
from rich.console import Console
from ubike import api
from ubike.cache import get_cached_token, set_cached_token

# Force console width to 38 for mobile/Telegram bot optimization
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
🚲 台灣公共自行車 YouBike 即時資訊查詢工具 (ubike CLI)
\b
使用範例 Examples:
\b
1. 顯示附近 YouBike 站點:
   ubike nearby "25.033964, 121.564468"
   ubike nearby "北緯25°5′0″ 東經121°34′43″"
   ubike nearby "https://www.google.com/maps/search/?api=1&query=25.0339,121.5644"
\b
2. 透過經緯度參數查詢:
   ubike nearby --lat 25.0339 --lon 121.5644 --radius 200
\b
3. 清除本地快取資料:
   ubike clean
""")
def cli():
    pass

@cli.command()
@click.argument("location", type=str, required=False)
@click.option("--lat", type=str, help="目前緯度 Latitude (支援十進位 or DMS)")
@click.option("--lon", type=str, help="目前經度 Longitude (支援十進位 or DMS)")
@click.option("--radius", type=int, default=200, help="搜尋半徑 (公尺，預設 200)")
def nearby(location, lat, lon, radius):
    """
    📍 查詢目前座標 200m 內 YouBike 站點與即時車況
    """
    target_lat, target_lon = None, None
    
    if location:
        with console.status("[bold cyan]🔍 解析輸入位置...[/bold cyan]"):
            parsed = api.parse_gps_input(location)
        if parsed:
            target_lat, target_lon = parsed
        else:
            console.print("[red]❌ 無法從輸入內容解析經緯度，請確認格式。[/red]")
            return
    elif lat and lon:
        # Combine lat and lon as a string to reuse the parser
        with console.status("[bold cyan]🔍 解析經緯度參數...[/bold cyan]"):
            parsed = api.parse_gps_input(f"{lat}, {lon}")
        if parsed:
            target_lat, target_lon = parsed
        else:
            console.print("[red]❌ 經緯度參數格式錯誤。[/red]")
            return
    else:
        console.print("[yellow]⚠️ 請提供位置資料或 --lat & --lon 參數。[/yellow]")
        console.print("例如: ubike nearby \"25.0339, 121.5644\"")
        return

    # Fetch token
    token = get_token_or_fail()

    # Query stations and availability
    with console.status("[bold yellow]🚲 查詢附近 YouBike 站點...[/bold yellow]"):
        try:
            stations = api.get_nearby_stations(token, target_lat, target_lon, radius)
        except api.TdxApiError as e:
            console.print(f"[red]❌ API 錯誤：{e}[/red]")
            return

    if not stations:
        console.print(f"[yellow]⚠️ 附近 {radius}m 內無 YouBike 站點。[/yellow]")
        return

    with console.status("[bold yellow]📊 讀取即時車位狀態...[/bold yellow]"):
        try:
            availability = api.get_nearby_availability(token, target_lat, target_lon, radius)
        except api.TdxApiError as e:
            console.print(f"[red]❌ API 錯誤：{e}[/red]")
            return

    # Map availability by StationUID
    avail_map = {item["StationUID"]: item for item in availability if "StationUID" in item}

    # Calculate distance and build list of stations with distance
    station_list = []
    for s in stations:
        st_pos = s.get("StationPosition", {})
        st_lat = st_pos.get("PositionLat")
        st_lon = st_pos.get("PositionLon")
        
        if st_lat is not None and st_lon is not None:
            dist = calculate_distance(target_lat, target_lon, st_lat, st_lon)
            if dist <= radius:
                station_list.append((dist, s))

    # Sort by distance
    station_list.sort(key=lambda x: x[0])

    if not station_list:
        console.print(f"[yellow]⚠️ 附近 {radius}m 內無 YouBike 站點。[/yellow]")
        return

    # Print header
    console.print(f"\n[bold yellow]🚲 附近 YouBike 站點 (半徑 {radius}m)[/bold yellow]")
    console.print(f"找到 {len(station_list)} 個站點 (顯示前 10 個)")
    console.print("─" * 36)

    status_msgs = {
        1: "🟢 正常營運",
        2: "🟡 暫停營運",
        0: "🔴 停止營運"
    }

    # Display top 10 nearest stations
    for dist, st in station_list[:10]:
        uid = st.get("StationUID")
        name = st.get("StationName", {}).get("Zh_tw", "未命名站點")
        name = name.replace("YouBike2.0_", "").replace("YouBike1.0_", "")
        address = st.get("StationAddress", {}).get("Zh_tw", "無地址資料")
        st_pos = st.get("StationPosition", {})
        st_lat = st_pos.get("PositionLat")
        st_lon = st_pos.get("PositionLon")
        
        # Get real-time availability
        avail = avail_map.get(uid, {})
        status_code = avail.get("ServiceStatus", 0)
        status_str = status_msgs.get(status_code, "🔴 停運/未知")
        
        rentable = avail.get("AvailableRentBikes", 0)
        returnable = avail.get("AvailableReturnBikes", 0)
        update_time = avail.get("SrcUpdateTime", "無時間資料")
        
        # Parse and format update time (usually in YYYY-MM-DDTHH:MM:SS+08:00)
        if "T" in update_time:
            try:
                # Extract HH:MM:SS from ISO string
                time_part = update_time.split("T")[1]
                if "+" in time_part:
                    update_time = time_part.split("+")[0]
                elif "-" in time_part:
                    update_time = time_part.split("-")[0]
            except Exception:
                pass

        # Google Map URL
        gmaps_url = f"https://www.google.com/maps/search/?api=1&query={st_lat},{st_lon}"

        # Display station with terminal hyperlinks
        console.print(f"🚲 [link={gmaps_url}][bold green]{name}[/bold green][/link]")
        console.print(f"   (距離約 {dist:.0f}m)")
        console.print(f"• 狀態: {status_str}")
        console.print(f"• 可借: [bold cyan]{rentable}[/bold cyan] | 空位: [bold yellow]{returnable}[/bold yellow]")
        console.print(f"• 地址: [dim]{address}[/dim]")
        console.print(f"• 更新: {update_time}")
        console.print(f"• 地圖: {gmaps_url}", soft_wrap=True)
        console.print("─" * 36)


@cli.command()
def clean():
    """
    🧹 清除本地 YouBike 快取資料
    """
    from ubike.cache import cache
    with console.status("[bold yellow]🧹 正在清除快取資料...[/bold yellow]"):
        cache.clear()
    console.print("[bold green]✨ 快取資料已成功清除！[/bold green]")

if __name__ == "__main__":
    cli()
