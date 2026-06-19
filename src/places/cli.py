import click
import os
from rich.console import Console
from places import api

# Force console width to 38 for mobile/Telegram bot optimization
console = Console(width=38)

def get_api_key_or_fail() -> str:
    """Retrieve Google Places API key from environment variables or fail."""
    api_key = os.getenv("GOOGLE_PLACES_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        console.print("[red]❌ 無法取得 Google Places API 金鑰。[/red]")
        console.print("[yellow]💡 請在 .env 檔案中設定 GOOGLE_PLACES_API_KEY=your_key。[/yellow]")
        raise click.ClickException("Google Places API Key not found")
    return api_key

@click.group(help="""\b
🗺️ 全球觀光美食查詢工具 (places CLI)
\b
使用範例 Examples:
\b
1. 顯示附近餐廳與景點:
   places nearby "25.033964, 121.564468"
   places nearby "北緯25°3′58″ 東經121°33′52″"
   places nearby "https://www.google.com/maps/search/?api=1&query=25.0339,121.5644"
\b
2. 透過經緯度參數查詢 (例如東京鐵塔附近 500m 內咖啡廳):
   places nearby --lat 35.6586 --lon 139.7454 --radius 500 --type 咖啡廳
\b
3. 篩選與自訂回傳語言 (顯示英文結果):
   places nearby "35.6586, 139.7454" --type bar --lang en
""")
def cli():
    pass

@cli.command()
@click.argument("location", type=str, required=False)
@click.option("--lat", type=str, help="目前緯度 Latitude (支援十進位 or DMS)")
@click.option("--lon", type=str, help="目前經度 Longitude (支援十進位 or DMS)")
@click.option("--radius", type=int, default=500, help="搜尋半徑 (公尺，預設 500)")
@click.option("--type", "type_param", type=str, help="篩選類型 (例如: 餐廳、景點、咖啡廳、酒吧等)")
@click.option("--lang", "language", type=str, default="zh-TW", help="回傳語言編碼 (例如: zh-TW, en, ja, 預設 zh-TW)")
def nearby(location, lat, lon, radius, type_param, language):
    """
    📍 查詢目前座標指定半徑內餐廳或景點與詳細資訊
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
        with console.status("[bold cyan]🔍 解析經緯度參數...[/bold cyan]"):
            parsed = api.parse_gps_input(f"{lat}, {lon}")
        if parsed:
            target_lat, target_lon = parsed
        else:
            console.print("[red]❌ 經緯度參數格式錯誤。[/red]")
            return
    else:
        console.print("[yellow]⚠️ 請提供位置資料或 --lat & --lon 參數。[/yellow]")
        console.print("例如: places nearby \"25.0339, 121.5644\"")
        return

    # Fetch API Key
    api_key = get_api_key_or_fail()

    # Query places
    type_display_name = type_param if type_param else "餐廳與景點"
    with console.status(f"[bold yellow]🗺️ 查詢附近 {type_display_name}...[/bold yellow]"):
        try:
            places = api.get_nearby_places(api_key, target_lat, target_lon, radius, type_param, language)
        except api.GooglePlacesApiError as e:
            console.print(f"[red]❌ API 錯誤：{e}[/red]")
            return

    if not places:
        console.print(f"[yellow]⚠️ 附近 {radius}m 內無相關的觀光美食點。[/yellow]")
        return

    # Calculate distance and filter/sort
    place_list = []
    for p in places:
        loc = p.get("geometry", {}).get("location", {})
        p_lat = loc.get("lat")
        p_lon = loc.get("lng")
        
        if p_lat is not None and p_lon is not None:
            dist = api.calculate_distance(target_lat, target_lon, p_lat, p_lon)
            if dist <= radius:
                place_list.append((dist, p))

    # Sort by distance
    place_list.sort(key=lambda x: x[0])

    if not place_list:
        console.print(f"[yellow]⚠️ 附近 {radius}m 內無相關的觀光美食點。[/yellow]")
        return

    # Print header
    console.print(f"\n[bold green]🗺️ 附近觀光美食 (半徑 {radius}m)[/bold green]")
    console.print(f"找到 {len(place_list)} 個地點 (顯示前 10 個)")
    console.print("─" * 36)

    # Display top 10 nearest places
    for dist, p in place_list[:10]:
        name = p.get("name", "未命名地點")
        place_id = p.get("place_id")
        loc = p.get("geometry", {}).get("location", {})
        p_lat = loc.get("lat")
        p_lng = loc.get("lng")
        
        # Rating
        rating = p.get("rating")
        user_ratings_total = p.get("user_ratings_total", 0)
        if rating is not None:
            rating_str = f"⭐ [yellow]{rating:.1f}[/yellow] ({user_ratings_total} 則評論)"
        else:
            rating_str = "⭐ [dim]無評分[/dim]"
            
        # Business status
        open_now = p.get("opening_hours", {}).get("open_now")
        if open_now is True:
            status_str = "🟢 營業中"
        elif open_now is False:
            status_str = "🔴 已打烊"
        else:
            status_str = "⚪ 營業時間未知"
            
        # Address
        address = p.get("vicinity") or p.get("formatted_address") or "無地址資料"
        
        # Types
        types = p.get("types", [])
        friendly_types = [api.TYPE_DISPLAY_MAP.get(t, t) for t in types if t not in ["point_of_interest", "establishment"]]
        # Remove duplicates and format
        friendly_types = list(dict.fromkeys(friendly_types))
        
        # Google Maps search URL with place ID to ensure correct location is selected
        gmaps_url = f"https://www.google.com/maps/search/?api=1&query={p_lat},{p_lng}&query_place_id={place_id}"

        # Display place with terminal hyperlinks
        console.print(f"📍 [link={gmaps_url}][bold cyan]{name}[/bold cyan][/link]")
        console.print(f"   (距離約 {dist:.0f}m)")
        console.print(f"• 評分: {rating_str}")
        console.print(f"• 狀態: {status_str}")
        if friendly_types:
            console.print(f"• 類型: {', '.join(friendly_types[:3])}")
        console.print(f"• 地址: [dim]{address}[/dim]")
        console.print(f"• 地圖: {gmaps_url}")
        console.print("─" * 36)

if __name__ == "__main__":
    cli()
