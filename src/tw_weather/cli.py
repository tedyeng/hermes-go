import os
import click
from datetime import datetime
from rich.console import Console
from tw_weather import api
from tw_weather.cache import cache

# Force console width to 38 for mobile/Telegram bot optimization (same as other CLIs)
console = Console(width=38)

def get_api_key_or_fail() -> str:
    """Retrieve CWA API key from environment variables or fail."""
    api_key = os.getenv("CWA_API_KEY")
    if not api_key:
        console.print("[red]❌ 無法取得中央氣象署 (CWA) API 金鑰。[/red]")
        console.print("[yellow]💡 請在 .env 檔案中設定 CWA_API_KEY=your_key。[/yellow]")
        console.print("   可至氣象資料開放平臺免費註冊申請：")
        console.print("   https://opendata.cwa.gov.tw/")
        raise click.ClickException("CWA API Key not found")
    return api_key

@click.group(help="""\b
🌦️ 台灣鄉鎮天氣預報與雨具建議 (tw-weather CLI)

提供即時降雨量、防汛警戒、雨具攜帶建議、快速天氣摘要、全台降雨看板、逐小時風速預報等完整天氣監測功能。

\b
主要功能與使用範例:
\b
  check   - 查詢降雨機率與雨具建議 (近期12h)
            $ tw-weather check "臺北市信義區"
            $ tw-weather check "板橋區"
            $ tw-weather check "25.0339, 121.5644"
            $ tw-weather check --lat 25.0339 --lon 121.5644
\b
  summary - 縣市快速摘要預報 (今明36h)
            $ tw-weather summary "高雄市"
            $ tw-weather summary "宜蘭縣"
\b
  board   - 全台各縣市降雨機率與雨具看板
            $ tw-weather board
\b
  hourly  - 逐小時氣象預報 (溫度/體感/濕度/風速)
            $ tw-weather hourly "台中市西屯區"
            $ tw-weather hourly "板橋區" --all-hours
\b
  rain    - 即時降雨觀測、防汛警戒、雨量預估
            $ tw-weather rain "臺南市安平區"
            $ tw-weather rain --lat 22.9975 --lon 120.1544
\b
  clean   - 清除本地快取的氣象 API 資料
            $ tw-weather clean
""")
def cli():
    pass

@cli.command()
@click.argument("location", type=str, required=False)
@click.option("--lat", type=str, help="目前緯度 Latitude (支援十進位 or DMS)")
@click.option("--lon", type=str, help="目前經度 Longitude (支援十進位 or DMS)")
@click.option("--cache-time", type=int, default=900, help="快取時間 (秒，預設 900/15分鐘)")
def check(location, lat, lon, cache_time):
    """\b
    🔍 查詢指定位置降雨機率與雨具攜帶建議

    \b
    支援輸入位置名稱（如 "臺北市信義區"、"羅東"）、
    經緯度字串（"25.033, 121.56"），或者使用 --lat
    和 --lon 參數。回傳近期 12 小時雨具建議
    （免帶/折傘/直傘）以及未來數日逐 12 小時天氣預報。

    \b
    使用範例 Example:
      $ tw-weather check "臺北市信義區"
      $ tw-weather check "板橋區"
      $ tw-weather check --lat 25.0339 --lon 121.5644
    """
    target_input = None
    
    if location:
        target_input = location
    elif lat and lon:
        target_input = f"{lat}, {lon}"
    else:
        console.print("[yellow]⚠️ 請提供位置名稱或 --lat & --lon 參數。[/yellow]")
        console.print("例如: tw-weather check \"台北市信義區\"")
        return

    # 1. Resolve Location
    with console.status("[bold cyan]🔍 解析地理位置與行政區...[/bold cyan]"):
        loc_res = api.resolve_location(target_input)

    if not loc_res:
        console.print("[red]❌ 無法解析該地點，請輸入明確的臺灣縣市與鄉鎮區名稱或經緯度。[/red]")
        return

    county, district, resolved_lat, resolved_lon = loc_res

    # Fallback to county-level forecast if district is not specified
    if not district:
        console.print(f"\n[bold green]📍 定位資訊 (縣市級預報)[/bold green]")
        console.print(f"• 縣市: [bold]{county}[/bold]")
        if resolved_lat != 0.0 and resolved_lon != 0.0:
            console.print(f"• 座標: ({resolved_lat:.4f}, {resolved_lon:.4f})")
        console.print("─" * 36)

        api_key = get_api_key_or_fail()

        cache_key = f"cwa_weather_county_{county}"
        weather_data = cache.get(cache_key)

        if weather_data:
            console.print("[dim]⚡ 讀取本地快取天氣資料...[/dim]")
        else:
            with console.status(f"[bold yellow]🌦️ 下載 {county} 預報...[/bold yellow]"):
                try:
                    weather_data = api.fetch_cwa_county_weather(api_key, county)
                    cache.set(cache_key, weather_data, custom_expiry=cache_time)
                except api.WeatherApiError as e:
                    console.print(f"[red]❌ API 錯誤：{e}[/red]")
                    return

        with console.status("[bold cyan]📊 分析降雨機率與雨具建議...[/bold cyan]"):
            try:
                periods = api.parse_county_weather_json(weather_data, county)
            except Exception as e:
                console.print(f"[red]❌ 預報解析錯誤：{e}[/red]")
                return

        display_weather_periods(periods)
        return

    # Get CWA Dataset ID
    dataset_id = api.COUNTY_DATASET_MAP.get(county)
    if not dataset_id:
        console.print(f"[red]❌ 縣市「{county}」不在中央氣象署鄉鎮預報支援範圍中。[/red]")
        return

    # Print location headers
    console.print(f"\n[bold green]📍 定位資訊[/bold green]")
    console.print(f"• 縣市: [bold]{county}[/bold]")
    console.print(f"• 鄉鎮區: [bold]{district}[/bold]")
    if resolved_lat != 0.0 and resolved_lon != 0.0:
        console.print(f"• 座標: ({resolved_lat:.4f}, {resolved_lon:.4f})")
    console.print("─" * 36)

    # 2. Get API key
    api_key = get_api_key_or_fail()

    # 3. Retrieve weather forecast with caching
    cache_key = f"cwa_weather_{dataset_id}_{district}"
    weather_data = cache.get(cache_key)

    if weather_data:
        console.print("[dim]⚡ 讀取本地快取天氣資料...[/dim]")
    else:
        with console.status(f"[bold yellow]🌦️ 下載 {county}{district} 預報...[/bold yellow]"):
            try:
                weather_data = api.fetch_cwa_weather(api_key, dataset_id, district)
                # Store in cache
                cache.set(cache_key, weather_data, custom_expiry=cache_time)
            except api.WeatherApiError as e:
                console.print(f"[red]❌ API 錯誤：{e}[/red]")
                return

    # 4. Parse weather forecast periods
    with console.status("[bold cyan]📊 分析降雨機率與雨具建議...[/bold cyan]"):
        try:
            periods = api.parse_weather_json(weather_data, district)
        except Exception as e:
            console.print(f"[red]❌ 預報解析錯誤：{e}[/red]")
            return

    display_weather_periods(periods)


def display_weather_periods(periods: List[Dict[str, Any]]):
    if not periods:
        console.print("[yellow]⚠️ 無法取得預報資料。[/yellow]")
        return

    immediate = periods[0]
    rec = immediate["recommendation"]
    pop = immediate["pop"]
    wx = immediate["wx_summary"]
    comfort = immediate.get("comfort", "")
    temp_min = immediate["temp_min"]
    temp_max = immediate["temp_max"]

    rec_style = {
        "需帶直傘": ("[bold red]🔴 建議攜帶「直傘」☂️[/bold red]", "預期有較大雨勢或持續降雨，直傘防風防雨效果最佳。"),
        "需帶折疊傘": ("[bold yellow]🟡 建議攜帶「折疊傘」🌂[/bold yellow]", "有降雨機會或局部短暫雨，帶折疊傘備用即可。"),
        "不需帶傘": ("[bold green]🟢 不需帶傘 ☀️[/bold green]", "降雨機率低，可輕鬆出門！")
    }

    style_title, style_tip = rec_style.get(rec, ("[white]未知建議[/white]", ""))

    comfort_str = f" ({comfort})" if comfort else ""
    console.print(f"\n[bold yellow]💡 雨具攜帶建議 (近期 12 小時)[/bold yellow]")
    console.print(style_title)
    console.print(f"• 時間: {immediate['period_name']}")
    console.print(f"• 天氣: {wx}{comfort_str} | {temp_min}~{temp_max}°C")
    console.print(f"• 降雨機率: {pop}%")
    console.print(f"[dim]提示: {style_tip}[/dim]")
    console.print("─" * 36)

    # Display list
    console.print("\n[bold]📅 逐 12 小時預報清單[/bold]")
    
    rec_icons = {
        "需帶直傘": "🔴 ☂️ 直傘",
        "需帶折疊傘": "🟡 🌂 折傘",
        "不需帶傘": "🟢 ☀️ 免帶"
    }

    for p in periods:
        p_name = p["period_name"]
        p_pop = p["pop"]
        p_wx = p["wx_summary"]
        p_comfort = p.get("comfort", "")
        p_tmin = p["temp_min"]
        p_tmax = p["temp_max"]
        p_rec = p["recommendation"]
        icon = rec_icons.get(p_rec, "❓")
        
        p_comfort_str = f" ({p_comfort})" if p_comfort else ""
        console.print(f"[bold]{p_name}[/bold]")
        console.print(f"  天氣: {p_wx}{p_comfort_str} ({p_tmin}~{p_tmax}°C)")
        console.print(f"  降雨: {p_pop}% -> {icon}")
        console.print("─" * 36)


@cli.command()
@click.argument("county", type=str, required=False)
@click.option("--cache-time", type=int, default=900, help="快取時間 (秒，預設 900)")
def summary(county, cache_time):
    """\b
    📋 縣市天氣今明 36h 快速摘要預報

    \b
    查詢指定縣市（如 "臺北市"、"花蓮"）今明 36 小時
    的快速天氣摘要預報。提供降雨機率、舒適度說明、
    氣溫區間及近期 12h 的雨具攜帶建議。

    \b
    使用範例 Example:
      $ tw-weather summary "臺北市"
      $ tw-weather summary "宜蘭縣"
    """
    if not county:
        console.print("[yellow]⚠️ 請指定要查詢的縣市。[/yellow]")
        console.print("例如: tw-weather summary \"臺北市\"")
        return
        
    normalized_county = api.normalize_county(county)
    if normalized_county not in api.TAIWAN_COUNTIES:
        matched = api.match_county_only(county)
        if matched:
            normalized_county = matched
        else:
            console.print(f"[red]❌ 無法識別縣市「{county}」，請輸入正確的台灣縣市名稱。[/red]")
            return

    console.print(f"\n[bold green]📍 縣市快速摘要預報[/bold green]")
    console.print(f"• 縣市: [bold]{normalized_county}[/bold]")
    console.print("─" * 36)

    api_key = get_api_key_or_fail()

    cache_key = f"cwa_weather_county_{normalized_county}"
    weather_data = cache.get(cache_key)

    if weather_data:
        console.print("[dim]⚡ 讀取本地快取天氣資料...[/dim]")
    else:
        with console.status(f"[bold yellow]🌦️ 下載 {normalized_county} 預報...[/bold yellow]"):
            try:
                weather_data = api.fetch_cwa_county_weather(api_key, normalized_county)
                cache.set(cache_key, weather_data, custom_expiry=cache_time)
            except api.WeatherApiError as e:
                console.print(f"[red]❌ API 錯誤：{e}[/red]")
                return

    with console.status("[bold cyan]📊 分析降雨機率與雨具建議...[/bold cyan]"):
        try:
            periods = api.parse_county_weather_json(weather_data, normalized_county)
        except Exception as e:
            console.print(f"[red]❌ 預報解析錯誤：{e}[/red]")
            return

    display_weather_periods(periods)


@cli.command()
@click.option("--cache-time", type=int, default=900, help="快取時間 (秒，預設 900)")
def board(cache_time):
    """\b
    📊 全台各縣市降雨機率與雨具攜帶看板

    \b
    一次獲取全台灣所有縣市的近期 12 小時降雨機率
    以及雨具攜帶建議。看板會自動依「降雨機率」由
    高至低排序，方便掌握全台下雨狀況。

    \b
    使用範例 Example:
      $ tw-weather board
    """
    api_key = get_api_key_or_fail()

    cache_key = "cwa_weather_all_counties"
    weather_data = cache.get(cache_key)

    if weather_data:
        console.print("[dim]⚡ 讀取全台快取天氣資料...[/dim]")
    else:
        with console.status("[bold yellow]🌦️ 下載全台縣市預報...[/bold yellow]"):
            try:
                weather_data = api.fetch_cwa_county_weather(api_key)
                cache.set(cache_key, weather_data, custom_expiry=cache_time)
            except api.WeatherApiError as e:
                console.print(f"[red]❌ API 錯誤：{e}[/red]")
                return

    records = weather_data.get("result", {}).get("records", {}) or weather_data.get("records", {})
    location_list = records.get("location", [])
    if not location_list:
        console.print("[red]❌ CWA 回傳空的天氣資料。[/red]")
        return

    board_entries = []
    period_title = "近期 12 小時"
    
    with console.status("[bold cyan]📊 解析全台預報資料...[/bold cyan]"):
        for loc in location_list:
            co_name = loc.get("locationName", "")
            try:
                periods = api.parse_county_weather_json(weather_data, co_name)
                if periods:
                    p = periods[0]
                    board_entries.append((co_name, p))
                    period_title = p["period_name"]
            except Exception:
                pass

    if not board_entries:
        console.print("[yellow]⚠️ 無法解析任何縣市資料。[/yellow]")
        return

    board_entries.sort(key=lambda x: x[1]["pop"], reverse=True)

    console.print(f"\n[bold yellow]☔ 全台降雨與雨具看板 ({period_title})[/bold yellow]")
    console.print("────────────────────────────────────")

    rec_icons = {
        "需帶直傘": "🔴 ☂️ 直傘",
        "需帶折疊傘": "🟡 🌂 折傘",
        "不需帶傘": "🟢 ☀️ 免帶"
    }

    for name, p in board_entries:
        pop = p["pop"]
        rec = p["recommendation"]
        wx = p["wx_summary"]
        comfort = p.get("comfort", "")
        icon = rec_icons.get(rec, "❓")
        
        comfort_str = f" ({comfort})" if comfort else ""
        console.print(f"[bold]{name}[/bold] {pop:2d}% -> {icon}")
        console.print(f"  [dim]{wx}{comfort_str}[/dim]")
        console.print("────────────────────────────────────")


@cli.command()
@click.argument("location", type=str, required=False)
@click.option("--lat", type=float, help="緯度 (Latitude)")
@click.option("--lon", type=float, help="經度 (Longitude)")
@click.option("--all-hours", is_flag=True, help="顯示完整 48 小時預報")
@click.option("--cache-time", type=int, default=900, help="快取時間 (秒，預設 900)")
def hourly(location, lat, lon, all_hours, cache_time):
    """\b
    🕒 逐小時天氣預報與攝影/戶外風速警戒

    \b
    查詢指定位置未來 24 小時的逐小時天氣。
    使用 --all-hours 可顯示完整 48 小時預報。
    欄位: 溫度、體感、降雨機率、濕度、風向風速。
    風速 >= 10.8 m/s 或降雨 >= 70% 顯示警戒提示。

    \b
    使用範例 Example:
      $ tw-weather hourly "臺北市信義區"
      $ tw-weather hourly "板橋區" --all-hours
    """
    if lat is not None and lon is not None:
        target_input = f"{lat}, {lon}"
    elif location:
        target_input = location
    else:
        target_input = "臺北市信義區"

    with console.status("[bold cyan]🔍 解析地理位置與行政區...[/bold cyan]"):
        loc_res = api.resolve_location(target_input)

    if not loc_res:
        console.print("[red]❌ 無法解析該地點，請輸入明確的臺灣縣市與鄉鎮區名稱或經緯度。[/red]")
        return

    county, district, resolved_lat, resolved_lon = loc_res

    if not district:
        dataset_id = api.COUNTY_DATASET_MAP.get(county)
        if not dataset_id:
            console.print(f"[red]❌ 縣市「{county}」不在中央氣象署鄉鎮預報支援範圍中。[/red]")
            return
        
        api_key = get_api_key_or_fail()
        with console.status(f"[bold yellow]🌦️ 正在取得 {county} 的地區清單...[/bold yellow]"):
            try:
                raw_data = api.fetch_cwa_weather(api_key, dataset_id, "")
                records = raw_data.get("result", {}).get("records", {}) or raw_data.get("records", {})
                locations = records.get("Locations", [])
                if locations and locations[0].get("Location"):
                    district = locations[0].get("Location", [])[0].get("LocationName")
                else:
                    console.print(f"[red]❌ 無法取得「{county}」的鄉鎮區資料。[/red]")
                    return
            except Exception as e:
                console.print(f"[red]❌ 取得地區失敗：{e}[/red]")
                return
    else:
        dataset_id = api.COUNTY_DATASET_MAP.get(county)
        if not dataset_id:
            console.print(f"[red]❌ 縣市「{county}」不在中央氣象署鄉鎮預報支援範圍中。[/red]")
            return

    console.print(f"\n[bold green]📍 逐小時預報定位[/bold green]")
    console.print(f"• 縣市: [bold]{county}[/bold]")
    console.print(f"• 鄉鎮區: [bold]{district}[/bold]")
    if resolved_lat != 0.0 and resolved_lon != 0.0:
        console.print(f"• 座標: ({resolved_lat:.4f}, {resolved_lon:.4f})")
    console.print("─" * 36)

    api_key = get_api_key_or_fail()

    cache_key = f"cwa_weather_{dataset_id}_all"
    weather_data = cache.get(cache_key)

    if weather_data:
        console.print("[dim]⚡ 讀取本地快取天氣資料...[/dim]")
    else:
        with console.status(f"[bold yellow]🌦️ 下載 {county} 逐小時預報...[/bold yellow]"):
            try:
                weather_data = api.fetch_cwa_weather(api_key, dataset_id, district)
                cache.set(cache_key, weather_data, custom_expiry=cache_time)
            except api.WeatherApiError as e:
                console.print(f"[red]❌ API 錯誤：{e}[/red]")
                return

    with console.status("[bold cyan]📊 分析逐小時氣象數據...[/bold cyan]"):
        try:
            hourly_records = api.parse_hourly_weather_json(weather_data, district)
        except Exception as e:
            console.print(f"[red]❌ 預報解析錯誤：{e}[/red]")
            return

    if not hourly_records:
        console.print("[yellow]⚠️ 無法取得該區域逐小時預報資料。[/yellow]")
        return

    from datetime import datetime, timezone, timedelta
    tz = timezone(timedelta(hours=8))
    now = datetime.now(tz)
    today_midnight = now.replace(hour=23, minute=59, second=59, microsecond=999999)

    if all_hours:
        todays_hours = [r for r in hourly_records if datetime.fromisoformat(r["datetime"]) >= now - timedelta(minutes=30)]
        title = "未來 48 小時完整預報"
    else:
        todays_hours = []
        for r in hourly_records:
            dt = datetime.fromisoformat(r["datetime"])
            if dt >= now - timedelta(minutes=30) and dt <= today_midnight:
                todays_hours.append(r)

        showing_24h = False
        if len(todays_hours) < 6:
            todays_hours = []
            showing_24h = True
            end_time = now + timedelta(hours=24)
            for r in hourly_records:
                dt = datetime.fromisoformat(r["datetime"])
                if dt >= now - timedelta(minutes=30) and dt <= end_time:
                    todays_hours.append(r)
        title = "今日剩餘時段預報" if not showing_24h else "未來 24 小時精細預報"

    high_rain_pop = [r["pop"] for r in todays_hours if r["pop"] >= 70]
    if high_rain_pop:
        max_pop = max(high_rain_pop)
        console.print(f"[bold red]⚠️ 警報：部分時段降雨機率高達 {max_pop}%！[/bold red]")
        console.print("[red]出門請務必準備雨具防雨。[/red]")
        console.print("─" * 36)

    console.print(f"\n[bold yellow]🕒 {title}[/bold yellow]")
    console.print("────────────────────────────────────")

    for r in todays_hours:
        dt = datetime.fromisoformat(r["datetime"])
        time_str = dt.strftime("%H:%M")
        
        pop = r["pop"]
        wx = r["wx"]
        temp = r["temp"]
        apparent_temp = r["apparent_temp"]
        rh = r["rh"]
        wd = r["wind_dir"]
        ws = r["wind_speed"]
        comfort = r["comfort"]
        
        comfort_str = f" ({comfort})" if comfort else ""
        pop_indicator = "☔" if pop >= 30 else "☀️"
        if pop >= 70:
            pop_indicator = "🔴☔"

        console.print(f"[bold]🕒 {time_str}[/bold] | {wx}{comfort_str}")
        console.print(f"  溫度: {temp}°C (體感 {apparent_temp}°C)")
        console.print(f"  降雨: {pop}% {pop_indicator} | 濕度: {rh}%")
        if wd or ws:
            console.print(f"  風向: {wd} ({ws} m/s)")
        console.print("────────────────────────────────────")


@cli.command()
@click.argument("location", type=str, required=False)
@click.option("--lat", type=float, help="緯度 (Latitude)")
@click.option("--lon", type=float, help="經度 (Longitude)")
@click.option("--cache-time", type=int, default=600, help="快取時間 (秒，預設 600)")
def rain(location, lat, lon, cache_time):
    """\b
    ☔ 即時降雨量觀測、災害防汛警戒與雨量預估

    \b
    定位最近的氣象觀測站，回傳即時雨量觀測數據
    （10m/1h/3h/24h/今日累積），並自動計算：
    1. 雨勢體感（毛毛雨/小雨/中雨/大雨/豪雨）
    2. 防汛警戒分級（一般→大雨→豪雨→超大豪雨）
    3. 未來 2 天降雨預估與 mm 雨量範圍估計

    \b
    使用範例 Example:
      $ tw-weather rain "臺北市信義區"
      $ tw-weather rain --lat 25.0339 --lon 121.5644
    """
    if lat is not None and lon is not None:
        target_input = f"{lat}, {lon}"
    elif location:
        target_input = location
    else:
        target_input = "臺北市信義區"

    with console.status("[bold cyan]🔍 解析地理位置與座標...[/bold cyan]"):
        loc_res = api.resolve_location(target_input)

    if not loc_res:
        console.print("[red]❌ 無法解析該地點，請輸入明確的臺灣縣市與鄉鎮區名稱或經緯度。[/red]")
        return

    county, district, resolved_lat, resolved_lon = loc_res

    if resolved_lat == 0.0 or resolved_lon == 0.0:
        resolved_lat, resolved_lon = 25.0339, 121.5644
        with console.status(f"[bold yellow]🔍 取得 {county} 代表座標...[/bold yellow]"):
            res = api.geocode_address(county)
            if res:
                resolved_lat, resolved_lon = res[2], res[3]

    console.print(f"\n[bold green]📍 降雨觀測定位[/bold green]")
    console.print(f"• 縣市: [bold]{county}[/bold]")
    if district:
        console.print(f"• 鄉鎮區: [bold]{district}[/bold]")
    console.print(f"• 座標: ({resolved_lat:.4f}, {resolved_lon:.4f})")
    console.print("─" * 36)

    api_key = get_api_key_or_fail()

    cache_key = "cwa_rain_observations"
    weather_data = cache.get(cache_key)

    if weather_data:
        console.print("[dim]⚡ 讀取本地快取雨量資料...[/dim]")
    else:
        with console.status("[bold yellow]🌦️ 下載即時降雨量觀測數據...[/bold yellow]"):
            try:
                weather_data = api.fetch_cwa_rain_data(api_key)
                cache.set(cache_key, weather_data, custom_expiry=cache_time)
            except api.WeatherApiError as e:
                console.print(f"[red]❌ API 錯誤：{e}[/red]")
                return

    with console.status("[bold cyan]📊 計算最近雨量觀測站...[/bold cyan]"):
        try:
            nearest_station, distance = api.find_nearest_rain_station(weather_data, resolved_lat, resolved_lon)
        except Exception as e:
            console.print(f"[red]❌ 測站計算錯誤：{e}[/red]")
            return

    st_name = nearest_station.get("StationName", "未知")
    st_id = nearest_station.get("StationId", "未知")
    obs_time = nearest_station.get("ObsTime", {}).get("DateTime", "未知")
    
    elements = nearest_station.get("RainfallElement", {})
    r_10m = elements.get("Past10Min", {}).get("Precipitation", "0.0")
    r_1h = elements.get("Past1hr", {}).get("Precipitation", "0.0")
    r_3h = elements.get("Past3hr", {}).get("Precipitation", "0.0")
    r_24h = elements.get("Past24hr", {}).get("Precipitation", "0.0")
    r_today = elements.get("Now", {}).get("Precipitation", "0.0")

    f_10m = api.format_rain_value(r_10m)
    f_1h = api.format_rain_value(r_1h)
    f_3h = api.format_rain_value(r_3h)
    f_24h = api.format_rain_value(r_24h)

    warning_name, warning_color = api.get_rain_alert_level(f_1h, f_3h, f_24h)
    intensity_label = api.get_rain_intensity_label(f_1h)

    # Fetch future weather forecast for rain outlook (using QPF estimates)
    fc_data = []
    try:
        town_dataset_id = api.COUNTY_DATASET_MAP.get(county)
        cache_key_fc = f"weather_qpf_forecast_{town_dataset_id}_{district}"
        fc_data = cache.get(cache_key_fc)
        if not fc_data:
            with console.status("[bold yellow]🔮 載入定量降水預估...[/bold yellow]"):
                fc_raw = api.fetch_cwa_weather(api_key, town_dataset_id, district, element_names="PoP3h,Wx")
                fc_data = api.parse_3h_forecast_for_rain(fc_raw, district)
                cache.set(cache_key_fc, fc_data, custom_expiry=cache_time)
    except Exception:
        pass

    console.print(f"\n[bold yellow]📡 觀測站資訊[/bold yellow]")
    console.print(f"• 站名: [bold]{st_name}[/bold] ({st_id})")
    console.print(f"• 距離: [bold]{distance:.2f} km[/bold]")
    console.print(f"• 觀測時間: {obs_time}")
    console.print("─" * 36)

    console.print(f"\n[bold yellow]💧 累積降雨量數據[/bold yellow]")
    console.print(f"• 10分鐘累積:  {api.display_rain_value(r_10m)}")
    console.print(f"• 過去1小時:   {api.display_rain_value(r_1h)}")
    console.print(f"• 過去3小時:   {api.display_rain_value(r_3h)}")
    console.print(f"• 過去24小時:  {api.display_rain_value(r_24h)}")
    console.print(f"• 今日日累積:  {api.display_rain_value(r_today)}")
    console.print(f"• 即時雨勢:    [bold cyan]{intensity_label}[/bold cyan]")
    console.print("─" * 36)

    console.print(f"\n[bold yellow]⚠️ 防災警戒分級[/bold yellow]")
    
    alert_styles = {
        "超大豪雨 (Extremely Torrential)": "[bold blink red]🔴 超大豪雨 (Extremely Torrential)[/bold blink red]",
        "大豪雨 (Torrential)": "[bold red]🔴 大豪雨 (Torrential)[/bold red]",
        "豪雨 (Extremely Heavy)": "[bold yellow]🟠 豪雨 (Extremely Heavy)[/bold yellow]",
        "大雨 (Heavy Rain)": "[bold yellow]🟡 大雨 (Heavy Rain)[/bold yellow]",
        "一般 (Normal)": "[bold green]🟢 一般 (Normal)[/bold green]"
    }
    styled_warning = alert_styles.get(warning_name, f"[white]{warning_name}[/white]")
    console.print(styled_warning)
    
    if warning_name != "一般 (Normal)":
        console.print("\n[bold red]⚠️ 警報：雨勢已達警戒標準，請密切注意低窪地區積水或防汛措施！[/bold red]")
    console.print("─" * 36)

    if fc_data:
        console.print(f"\n[bold yellow]🔮 未來兩日降雨預估[/bold yellow]")
        for item in fc_data[:4]:
            period = item.get("period_name", "未知時段")
            pop = item.get("pop", 0)
            wx = item.get("wx_summary", "未知")
            min_mm = item.get("min_mm", 0.0)
            max_mm = item.get("max_mm", 0.0)
            
            if pop >= 70:
                icon = "☔🔴"
            elif pop >= 30:
                icon = "☔"
            else:
                icon = "☀️"
            
            if max_mm <= 0.0:
                mm_str = "無雨 (0 mm)"
                mm_color = "green"
            elif min_mm == max_mm:
                mm_str = f"{min_mm:.1f} mm"
                mm_color = "yellow" if max_mm < 10.0 else "red"
            else:
                mm_str = f"{min_mm:.1f} ~ {max_mm:.1f} mm"
                mm_color = "yellow" if max_mm < 10.0 else "red"
                
            console.print(f"• {period}")
            console.print(f"  預報: {wx[:6]} ({pop}%) {icon}")
            console.print(f"  預估雨量: [{mm_color}]{mm_str}[/{mm_color}]")
        console.print("─" * 36)


@cli.command()
def clean():
    """\b
    🧹 清除本地天氣快取資料

    \b
    手動清除本地 SQLite 中的所有氣象 API 快取，
    強迫下次查詢直接向中央氣象署 (CWA) 要求
    最新即時數據。

    \b
    使用範例 Example:
      $ tw-weather clean
    """
    with console.status("[bold yellow]🧹 正在清除氣象快取資料...[/bold yellow]"):
        cache.clear()
    console.print("[bold green]✨ 快取資料已成功清除！[/bold green]")

if __name__ == "__main__":
    cli()
