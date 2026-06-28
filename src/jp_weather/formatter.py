from datetime import datetime
from typing import Dict, Any, List, Optional
import questionary
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.columns import Columns
from rich.text import Text
from rich.box import ROUNDED

console = Console()

# Weather Code (WMO) Mapping to (Description, Emoji, Color)
WMO_CODES = {
    0: ("晴天 / Clear Sky", "☀️", "yellow"),
    1: ("晴間 / Mainly Clear", "🌤️", "yellow"),
    2: ("多雲 / Partly Cloudy", "⛅", "bright_blue"),
    3: ("陰天 / Overcast", "☁️", "grey53"),
    45: ("有霧 / Fog", "🌫️", "grey70"),
    48: ("霧淞 / Depositing Rime Fog", "🌫️", "grey70"),
    51: ("輕微毛毛雨 / Light Drizzle", "🌧️", "cyan"),
    53: ("中度毛毛雨 / Moderate Drizzle", "🌧️", "cyan"),
    55: ("重度毛毛雨 / Dense Drizzle", "🌧️", "cyan"),
    56: ("輕微凍雨 / Light Freezing Drizzle", "🌨️", "blue"),
    57: ("重度凍雨 / Dense Freezing Drizzle", "🌨️", "blue"),
    61: ("微雨 / Slight Rain", "🌧️", "sky_blue1"),
    63: ("中雨 / Moderate Rain", "🌧️", "dodger_blue1"),
    65: ("大雨 / Heavy Rain", "🌧️", "blue1"),
    66: ("微凍雨 / Light Freezing Rain", "🌨️", "blue"),
    67: ("大凍雨 / Heavy Freezing Rain", "🌨️", "blue"),
    71: ("微雪 / Slight Snow", "❄️", "bright_white"),
    73: ("中雪 / Moderate Snow", "❄️", "bright_white"),
    75: ("大雪 / Heavy Snow", "❄️", "bright_white"),
    77: ("雪粒 / Snow Grains", "❄️", "bright_white"),
    80: ("微陣雨 / Slight Rain Showers", "🌦️", "cyan"),
    81: ("中陣雨 / Moderate Rain Showers", "🌦️", "dodger_blue1"),
    82: ("暴陣雨 / Violent Rain Showers", "⛈️", "purple"),
    85: ("微陣雪 / Slight Snow Showers", "🌨️", "bright_white"),
    86: ("大陣雪 / Heavy Snow Showers", "🌨️", "bright_white"),
    95: ("雷雨 / Thunderstorm", "⛈️", "red"),
    96: ("雷雨伴有微冰雹 / Thunderstorm with Hail", "⛈️", "red"),
    99: ("雷雨伴有大冰雹 / Thunderstorm with Heavy Hail", "⛈️", "red"),
}

def get_weather_info(code: int) -> tuple:
    """Return description, emoji, and color for a WMO weather code."""
    desc, emoji, color = WMO_CODES.get(code, ("未知天氣 / Unknown", "❓", "white"))
    if isinstance(emoji, str):
        emoji = emoji.replace("\ufe0f", "")
    return desc, emoji, color

def get_wind_direction_arrow(degrees: float) -> str:
    """Convert wind degrees to a directional arrow icon."""
    if degrees is None:
        return ""
    arrows = ["↓", "↙", "←", "↖", "↑", "↗", "→", "↘"]
    idx = int((degrees + 22.5) / 45) % 8
    return arrows[idx]

def get_uv_level(uv: float) -> tuple:
    """Get UV hazard text and color."""
    if uv is None:
        return "未知", "white"
    if uv < 3:
        return "低 / Low", "green"
    elif uv < 6:
        return "中 / Moderate", "yellow"
    elif uv < 8:
        return "高 / High", "orange1"
    elif uv < 11:
        return "甚高 / Very High", "red"
    else:
        return "極高 / Extreme", "purple"

def get_weekday_ch(date_str: str) -> str:
    """Get Chinese weekday abbreviation."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        weekdays = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
        return weekdays[dt.weekday()]
    except Exception:
        return ""

def to_traditional_chinese(text: str) -> str:
    """Convert common geocoding Simplified Chinese/Japanese Kanji characters to Traditional Chinese."""
    if not isinstance(text, str):
        return text
    
    mapping = {
        "台湾": "台灣",
        "湾": "灣",
        "县": "縣",
        "区": "區",
        "东": "東",
        "国": "國",
        "气": "氣",
        "温": "溫",
        "风": "風",
        "云": "雲",
        "阴": "陰",
        "雾": "霧",
        "广": "廣",
        "岛": "島",
        "爱": "愛",
        "静": "靜",
        "冈": "岡",
        "福": "福",
        "丰": "豐",
        "阪": "阪",
        "叶": "葉",
        "号": "號",
    }
    
    for s, t in mapping.items():
        text = text.replace(s, t)
    return text

def format_location_title(loc: Dict[str, Any]) -> str:
    """Generate a clean, beautiful display name for a location."""
    name = loc.get("name")
    admin1 = loc.get("admin1")
    country = loc.get("country", "日本")
    
    parts = []
    if name:
        parts.append(name)
    if admin1 and admin1 != name:
        parts.append(admin1)
    if country:
        parts.append(country)
        
    raw_title = ", ".join(parts)
    return to_traditional_chinese(raw_title)

def select_location_interactive(locations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Prompt the user to select from multiple locations using questionary.
    """
    choices = []
    for loc in locations:
        title = format_location_title(loc)
        lat = loc.get("latitude", 0.0)
        lon = loc.get("longitude", 0.0)
        timezone = loc.get("timezone", "Asia/Tokyo")
        population = loc.get("population")
        
        pop_str = f" | 人口: {population:,}" if population else ""
        display_str = f"{title} (緯度: {lat:.2f}, 經度: {lon:.2f}{pop_str})"
        
        choices.append(questionary.Choice(title=display_str, value=loc))
        
    # Add a cancel option
    choices.append(questionary.Choice(title="❌ 取消查詢 / Cancel", value=None))
    
    selected = questionary.select(
        "🔍 找到多個地點，請選擇正確的查詢目標：",
        choices=choices,
        style=questionary.Style([
            ('qmark', 'fg:#FF9D00 bold'),
            ('question', 'bold fg:#ffffff'),
            ('pointer', 'fg:#00D7FF bold'),
            ('highlighted', 'fg:#00D7FF bold'),
            ('selected', 'fg:#00FF66'),
        ])
    ).ask()
    
    if not isinstance(selected, dict):
        return {"cancelled": True}
    return selected

def render_current_weather(loc: Dict[str, Any], weather_data: Dict[str, Any], mobile: bool = False):
    """
    Render a stunning visual panel for the current weather.
    """
    if mobile:
        mobile_console = Console(width=38)
        
        current = weather_data.get("current", {})
        temp = current.get("temperature_2m")
        humidity = current.get("relative_humidity_2m")
        apparent = current.get("apparent_temperature")
        precip = current.get("precipitation", 0.0)
        wcode = current.get("weather_code", 0)
        wind_spd = current.get("wind_speed_10m")
        wind_dir = current.get("wind_direction_10m")
        
        desc, emoji, color = get_weather_info(wcode)
        loc_title = format_location_title(loc)
        tz = weather_data.get("timezone", loc.get("timezone", "Asia/Tokyo"))
        
        # Stacking all text vertically to fit inside 38 columns (content width 32)
        full_text = Text()
        full_text.append(strip_vs16(f"📍 {loc_title}\n"), style="bold cyan")
        full_text.append(strip_vs16(f"🌐 緯度: {loc.get('latitude'):.2f} 經度: {loc.get('longitude'):.2f}\n"), style="dim")
        full_text.append(strip_vs16(f"⏰ 時區: {tz}\n\n"), style="dim")
        full_text.append(strip_vs16(f"{emoji}  {temp}°C  {desc.split(' / ')[0]}\n\n"), style=f"bold {color}")
        
        full_text.append(strip_vs16(f"體感 Apparent : {apparent}°C\n"), style="white")
        full_text.append(strip_vs16(f"濕度 Humidity : {humidity}%\n"), style="white")
        
        wind_arrow = get_wind_direction_arrow(wind_dir)
        full_text.append(strip_vs16(f"風速 Wind Spd : {wind_spd} m/s {wind_arrow}\n"), style="white")
        full_text.append(strip_vs16(f"降雨 Rain     : {precip} mm\n"), style="white")
        
        # Print a beautiful bold title directly as text, and output the clean borderless content
        mobile_title = to_traditional_chinese(f"🌦️ {loc.get('name', 'GPS')} 目前天氣 Current Weather")
        mobile_console.print(strip_vs16(f"\n[bold yellow]{mobile_title}[/bold yellow]\n"))
        mobile_console.print(full_text)
        
        # Hourly forecast (narrow table)
        hourly = weather_data.get("hourly", {})
        if hourly and "time" in hourly:
            current_time = current.get("time")
            times = hourly.get("time", [])
            
            start_idx = 0
            current_hour_time = current_time
            if current_time and len(current_time) >= 16:
                current_hour_time = current_time[:14] + "00"
                
            if current_hour_time in times:
                start_idx = times.index(current_hour_time)
                
            mobile_console.print("\n[bold yellow]🕒 3小時預報 Hourly Forecast[/bold yellow]")
            
            for step in range(8):
                idx = start_idx + (step * 3)
                if idx >= len(times):
                    break
                    
                time_str = times[idx]
                temp_val = hourly.get("temperature_2m", [])[idx]
                wcode_val = hourly.get("weather_code", [])[idx]
                pop_val = hourly.get("precipitation_probability", [])[idx]
                
                try:
                    dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
                    t_lbl = dt.strftime("%H:%M")
                except Exception:
                    t_lbl = time_str
                    
                if step == 0:
                    time_display = f"{t_lbl}*"
                else:
                    time_display = t_lbl
                    
                desc_val, emoji_val, color_val = get_weather_info(wcode_val)
                weather_display = f"{emoji_val} {desc_val.split(' / ')[0]}"
                temp_display = f"{temp_val:.1f}°C"
                pop_display = f"{pop_val}%" if pop_val is not None else "-"
                
                # Format as a clean, compact single line
                line = Text()
                line.append(f"● {time_display} ", style="cyan")
                line.append(f"{weather_display} ", style=color_val)
                line.append(f"{temp_display} ", style="white")
                line.append(f"{pop_display}", style="grey70")
                
                mobile_console.print(strip_vs16(line))
        return

    current = weather_data.get("current", {})
    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    apparent = current.get("apparent_temperature")
    precip = current.get("precipitation", 0.0)
    wcode = current.get("weather_code", 0)
    wind_spd = current.get("wind_speed_10m")
    wind_dir = current.get("wind_direction_10m")
    
    desc, emoji, color = get_weather_info(wcode)
    loc_title = format_location_title(loc)
    tz = weather_data.get("timezone", loc.get("timezone", "Asia/Tokyo"))
    
    # 1. Location Header (Clean separate block)
    header_text = Text()
    header_text.append(f"\n📍 {loc_title}\n", style="bold cyan")
    gps_info = f"🌐 緯度: {loc.get('latitude'):.4f}  經度: {loc.get('longitude'):.4f}"
    if loc.get("elevation"):
        gps_info += f"  海拔: {loc.get('elevation')}m"
    gps_info += f"  時區: {tz}"
    header_text.append(gps_info, style="dim")
    console.print(header_text)
    
    # 2. Main Weather Status Panel (Clean compact side-by-side layout)
    # Left column: Temp & Weather description
    temp_text = Text()
    temp_text.append(f"\n  {emoji}  {temp}°C\n\n", style=f"bold {color}")
    temp_text.append(f"  目前天氣：\n  {desc}\n", style=f"bold {color}")
    
    # Right column: Stats table
    # Right column: Stats table
    wind_arrow = get_wind_direction_arrow(wind_dir)
    stats_table = Table.grid(padding=(0, 1))
    stats_table.add_column(style="dim", width=26)
    stats_table.add_column(style="bold white", width=12)
    
    stats_table.add_row("體感溫度 Apparent Temp :", f"{apparent}°C")
    stats_table.add_row("相對濕度 Humidity      :", f"{humidity}%")
    stats_table.add_row("風速風向 Wind Speed    :", f"{wind_spd} m/s {wind_arrow}")
    stats_table.add_row("目前降雨 Precipitation :", f"{precip} mm")
    
    # Layout Grid to align Left and Right side-by-side inside the panel
    layout_grid = Table.grid(padding=(0, 2))
    layout_grid.add_column(width=22)
    layout_grid.add_column(width=38)
    layout_grid.add_row(temp_text, stats_table)
    
    panel = Panel(
        layout_grid,
        title=strip_vs16("[bold yellow]🌦️ 目前天氣狀態 Current Weather[/bold yellow]"),
        border_style="bright_blue",
        box=ROUNDED,
        width=68,
        padding=(1, 2)
    )
    console.print(panel)
    
    # Render Hourly Table if data is available
    hourly = weather_data.get("hourly", {})
    if hourly and "time" in hourly:
        current_time = current.get("time")  # e.g. "2026-05-31T11:45"
        times = hourly.get("time", [])
        
        # Open-Meteo current time has 15-minute intervals (e.g. 11:45), 
        # while hourly times are on the hour (e.g. 11:00). We normalize to clean hour.
        start_idx = 0
        current_hour_time = current_time
        if current_time and len(current_time) >= 16:
            current_hour_time = current_time[:14] + "00"
            
        if current_hour_time in times:
            start_idx = times.index(current_hour_time)
            
        console.print("\n[bold yellow]🕒 近期每 3 小時預報 Hourly Forecast (Next 24h)[/bold yellow]")
        
        hourly_table = Table(box=ROUNDED, border_style="bright_blue", header_style="bold cyan")
        hourly_table.add_column("時間 Time", justify="left")
        hourly_table.add_column("天氣 Weather", justify="left")
        hourly_table.add_column("氣溫 Temp", justify="right")
        hourly_table.add_column("降雨機率 Pop", justify="right")
        
        for step in range(8):
            idx = start_idx + (step * 3)
            if idx >= len(times):
                break
                
            time_str = times[idx]
            temp = hourly.get("temperature_2m", [])[idx]
            wcode = hourly.get("weather_code", [])[idx]
            pop = hourly.get("precipitation_probability", [])[idx]
            
            try:
                dt = datetime.strptime(time_str, "%Y-%m-%dT%H:%M")
                t_lbl = dt.strftime("%H:%M")
            except Exception:
                t_lbl = time_str
                
            if step == 0:
                time_display = f"{t_lbl} [bold yellow](現在)[/bold yellow]"
            else:
                time_display = f"{t_lbl} [dim](+{step * 3}h)[/dim]"
                
            desc, emoji, color = get_weather_info(wcode)
            weather_display = f"{emoji} [bold {color}]{desc}[/bold {color}]"
            temp_display = f"[bold white]{temp:.1f}°C[/bold white]"
            
            if pop is not None:
                if pop >= 70:
                    pop_display = f"[bold dodger_blue1]{pop}% 🌧️[/bold dodger_blue1]"
                elif pop >= 30:
                    pop_display = f"[sky_blue1]{pop}% 🌦️[/sky_blue1]"
                else:
                    pop_display = f"[grey53]{pop}%[/grey53]"
            else:
                pop_display = "[dim]-[/dim]"
                
            hourly_table.add_row(
                strip_vs16(time_display),
                strip_vs16(weather_display),
                strip_vs16(temp_display),
                strip_vs16(pop_display)
            )
            
        console.print(hourly_table)

def strip_vs16(text: str) -> str:
    """Strip variation selector-16 (U+FE0F) which causes terminal border misalignment."""
    if isinstance(text, str):
        return text.replace("\ufe0f", "")
    return text

def render_forecast_weather(loc: Dict[str, Any], weather_data: Dict[str, Any], mobile: bool = False):
    """
    Render a stunning visual table for the 7-day forecast.
    Includes visual temperature bars.
    """
    daily = weather_data.get("daily", {})
    if not daily:
        console.print("[red]無法取得預報資料！[/red]")
        return
        
    loc_title = format_location_title(loc)
    
    if mobile:
        mobile_console = Console(width=38)
        mobile_console.print(f"\n[bold yellow]📅 7 天天氣預報 7-Day Outlook[/bold yellow]")
        mobile_console.print(f"[cyan]📍 {loc_title}[/cyan]")
        mobile_console.print(f"更新: {datetime.now().strftime('%m-%d %H:%M')}\n")
        
        for i in range(len(daily.get("time", []))):
            date_str = daily["time"][i]
            wcode = daily["weather_code"][i]
            tmin = daily["temperature_2m_min"][i]
            tmax = daily["temperature_2m_max"][i]
            precip_sum = daily["precipitation_sum"][i]
            pop = daily.get("precipitation_probability_max", [None])[i]
            uv = daily.get("uv_index_max", [None])[i]
            
            weekday = get_weekday_ch(date_str)
            desc, emoji, color = get_weather_info(wcode)
            
            card = Text()
            card.append(f"● {date_str} ({weekday}) {emoji} {desc.split(' / ')[0]}\n", style=f"bold {color}")
            
            card.append("  🌡️ 氣溫: ")
            card.append(f"{tmin:.1f}°C", style="blue")
            card.append(" ~ ")
            card.append(f"{tmax:.1f}°C", style="red")
            card.append("\n")
            
            pop_str = f"{pop}%" if pop is not None else "-"
            rain_str = f"{precip_sum:.1f} mm" if precip_sum > 0 else "0.0 mm"
            card.append(f"  🌧️ 降雨: {pop_str} | {rain_str}\n")
            
            card.append("  ☀️ 紫外線: ")
            if uv is not None:
                uv_lbl, uv_color = get_uv_level(uv)
                card.append(f"{uv:.1f} ({uv_lbl.split(' / ')[0]})", style=uv_color)
            else:
                card.append("-")
            
            # Print as beautiful borderless paragraph blocks with a separating newline
            mobile_console.print(card)
            mobile_console.print()
        return
    
    # Title Header
    tz = weather_data.get("timezone", loc.get("timezone", "Asia/Tokyo"))
    console.print(f"\n[bold yellow]📅 7 天天氣預報 7-Day Outlook[/bold yellow] : [cyan]{loc_title}[/cyan]")
    console.print(f"時區 Timezone: {tz} | 更新時間 Update Time: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
    
    table = Table(box=ROUNDED, border_style="bright_blue", header_style="bold cyan")
    table.add_column("日期 Date", justify="left")
    table.add_column("天氣 Weather", justify="left")
    table.add_column("降雨機率 Pop", justify="right")
    table.add_column("累積降雨 Rain", justify="right")
    table.add_column("紫外線 UV", justify="center")
    table.add_column("氣溫變化 Temp Range", justify="center")
    

        
    for i in range(len(daily.get("time", []))):
        date_str = daily["time"][i]
        wcode = daily["weather_code"][i]
        tmin = daily["temperature_2m_min"][i]
        tmax = daily["temperature_2m_max"][i]
        precip_sum = daily["precipitation_sum"][i]
        pop = daily.get("precipitation_probability_max", [None])[i] # Some models might have None
        uv = daily.get("uv_index_max", [None])[i]
        
        # Format Date
        weekday = get_weekday_ch(date_str)
        date_display = f"{date_str} ({weekday})"
        
        # Format Weather
        desc, emoji, color = get_weather_info(wcode)
        weather_display = f"{emoji} [bold {color}]{desc}[/bold {color}]"
        
        # Format POP (Precipitation Probability)
        if pop is not None:
            if pop >= 70:
                pop_display = f"[bold dodger_blue1]{pop}% 🌧️[/bold dodger_blue1]"
            elif pop >= 30:
                pop_display = f"[sky_blue1]{pop}% 🌦️[/sky_blue1]"
            else:
                pop_display = f"[grey53]{pop}%[/grey53]"
        else:
            pop_display = "[dim]-[/dim]"
            
        # Format Precipitation Sum
        if precip_sum > 0:
            precip_display = f"[bold cyan]{precip_sum:.1f} mm[/bold cyan]"
        else:
            precip_display = "[dim]0.0 mm[/dim]"
            
        # Format UV
        if uv is not None:
            uv_lbl, uv_color = get_uv_level(uv)
            uv_display = f"[{uv_color}]{uv:.1f} ({uv_lbl})[/{uv_color}]"
        else:
            uv_display = "[dim]-[/dim]"
            
        # Format Temperature Range
        temp_bar = f"[blue]{tmin:.1f}°C[/blue] [dim]~[/dim] [red]{tmax:.1f}°C[/red]"
        
        table.add_row(
            strip_vs16(date_display),
            strip_vs16(weather_display),
            strip_vs16(pop_display),
            strip_vs16(precip_display),
            strip_vs16(uv_display),
            strip_vs16(temp_bar)
        )
        
    console.print(table)

def render_golden_hour(
    loc: Dict[str, Any],
    weather_data: Dict[str, Any],
    week: bool = False,
    mobile: bool = False
):
    """
    Render the Golden & Blue Hour information for today or the upcoming week.
    """
    from jp_weather.suncalc import get_sun_times
    from jp_weather.api import calculate_photography_rating
    from datetime import timezone
    from zoneinfo import ZoneInfo
    
    loc_title = format_location_title(loc)
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    timezone_str = weather_data.get("timezone", loc.get("timezone", "Asia/Tokyo"))
    
    try:
        local_tz = ZoneInfo(timezone_str)
    except Exception:
        local_tz = timezone.utc

    hourly_data = weather_data.get("hourly", {})
    
    def format_time(dt: Optional[datetime]) -> str:
        if not dt:
            return "--:--"
        local_dt = dt.astimezone(local_tz)
        return local_dt.strftime("%H:%M")
        
    def get_stars_str(stars: int) -> str:
        return "★" * stars + "☆" * (5 - stars)

    # In Python CJK environments, strip_vs16 is helper function already defined in formatter.py
    # We will use it directly.

    if week:
        daily = weather_data.get("daily", {})
        if not daily or "time" not in daily:
            console.print("[red]❌ 無法取得一週的預報資料！[/red]")
            return

        dates = daily.get("time", [])
        
        if mobile:
            mobile_console = Console(width=38)
            mobile_console.print(f"\n[bold yellow]📸 一週光影預報 Weekly Golden Hour[/bold yellow]")
            mobile_console.print(strip_vs16(f"📍 {loc_title}\n"))
            
            for date_str in dates:
                try:
                    dt_parsed = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=local_tz)
                except Exception:
                    continue
                
                s_times = get_sun_times(lat, lon, dt_parsed)
                polar = s_times.get("polar_status", "normal")
                weekday = get_weekday_ch(date_str)
                
                card = Text()
                if polar == "polar_day":
                    card.append(f"● {date_str} ({weekday}) [極晝 ☀️]\n", style="bold yellow")
                    card.append("  ☀️ 太陽終日不落，全天極晝\n", style="yellow")
                    card.append("  💡 建議: 適合全天拍攝，但無傳統黃金/藍調時刻。\n")
                elif polar == "polar_night":
                    card.append(f"● {date_str} ({weekday}) [極夜 🌑]\n", style="bold blue")
                    card.append("  🌑 太陽終日不出，全天極夜\n", style="bright_blue")
                    card.append("  💡 建議: 全天處於黑夜，無傳統黃金/藍調時刻。\n")
                else:
                    stars, desc = calculate_photography_rating(
                        s_times.get("golden_hour_pm_start"),
                        s_times.get("golden_hour_pm_end"),
                        hourly_data,
                        timezone_str
                    )
                    stars_str = get_stars_str(stars)
                    card.append(f"● {date_str} ({weekday}) {stars_str}\n", style="bold yellow")
                    card.append(f"  🌅 晨光: {format_time(s_times.get('blue_hour_am_start'))} ~ {format_time(s_times.get('golden_hour_am_end'))}\n", style="cyan")
                    card.append(f"  🌇 昏光: {format_time(s_times.get('golden_hour_pm_start'))} ~ {format_time(s_times.get('blue_hour_pm_end'))}\n", style="orange1")
                    card.append(f"  💡 建議: {desc}\n")
                
                mobile_console.print(strip_vs16(card))
            return

        # Desktop Table Rendering
        console.print(f"\n[bold yellow]📸 一週光影預報 Weekly Golden Hour[/bold yellow] : [cyan]{loc_title}[/cyan]")
        console.print(f"緯度 Lat: {lat:.4f} | 經度 Lon: {lon:.4f} | 時區 TZ: {timezone_str}\n")
        
        table = Table(box=ROUNDED, border_style="bright_blue", header_style="bold cyan")
        table.add_column("日期 Date", justify="left")
        table.add_column("晨間藍調 Blue AM", justify="center", style="cyan")
        table.add_column("晨間黃金 Golden AM", justify="center", style="yellow")
        table.add_column("日出/日落 Sunrise/set", justify="center")
        table.add_column("傍晚黃金 Golden PM", justify="center", style="orange1")
        table.add_column("傍晚藍調 Blue PM", justify="center", style="bold blue")
        table.add_column("攝影指數 Rating & Guide", justify="left")
        
        for date_str in dates:
            try:
                dt_parsed = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=local_tz)
            except Exception:
                continue
            
            s_times = get_sun_times(lat, lon, dt_parsed)
            polar = s_times.get("polar_status", "normal")
            weekday = get_weekday_ch(date_str)
            date_display = f"{date_str} ({weekday})"
            
            if polar == "polar_day":
                table.add_row(
                    strip_vs16(date_display),
                    strip_vs16("[yellow]極晝 Polar Day[/yellow]"),
                    strip_vs16("[yellow]終日不落[/yellow]"),
                    strip_vs16("☀️ Midnight Sun"),
                    strip_vs16("[yellow]終日不落[/yellow]"),
                    strip_vs16("[yellow]極晝 Polar Day[/yellow]"),
                    strip_vs16("☀️ 24小時日光，無黃金/藍調時刻")
                )
            elif polar == "polar_night":
                table.add_row(
                    strip_vs16(date_display),
                    strip_vs16("[blue]極夜 Polar Night[/blue]"),
                    strip_vs16("[blue]終日不出[/blue]"),
                    strip_vs16("🌑 Polar Night"),
                    strip_vs16("[blue]終日不出[/blue]"),
                    strip_vs16("[blue]極夜 Polar Night[/blue]"),
                    strip_vs16("🌑 24小時黑暗，無黃金/藍調時刻")
                )
            else:
                stars, desc = calculate_photography_rating(
                    s_times.get("golden_hour_pm_start"),
                    s_times.get("golden_hour_pm_end"),
                    hourly_data,
                    timezone_str
                )
                
                blue_am = f"{format_time(s_times.get('blue_hour_am_start'))} - {format_time(s_times.get('blue_hour_am_end'))}"
                gold_am = f"{format_time(s_times.get('golden_hour_am_start'))} - {format_time(s_times.get('golden_hour_am_end'))}"
                sun_rise_set = f"🌅 {format_time(s_times.get('sunrise'))} / 🌇 {format_time(s_times.get('sunset'))}"
                gold_pm = f"{format_time(s_times.get('golden_hour_pm_start'))} - {format_time(s_times.get('golden_hour_pm_end'))}"
                blue_pm = f"{format_time(s_times.get('blue_hour_pm_start'))} - {format_time(s_times.get('blue_hour_pm_end'))}"
                
                color_tag = "bold green" if stars >= 4 else ("yellow" if stars >= 3 else "grey53")
                rating_display = f"[{color_tag}]{get_stars_str(stars)}[/{color_tag}] {desc}"
                
                table.add_row(
                    strip_vs16(date_display),
                    strip_vs16(blue_am),
                    strip_vs16(gold_am),
                    strip_vs16(sun_rise_set),
                    strip_vs16(gold_pm),
                    strip_vs16(blue_pm),
                    strip_vs16(rating_display)
                )
            
        console.print(table)
        return

    # Single Day Rendering (Default today)
    today = datetime.now(timezone.utc)
    s_times = get_sun_times(lat, lon, today)
    polar = s_times.get("polar_status", "normal")
    
    stars_am, desc_am = (3, "")
    stars_pm, desc_pm = (3, "")
    if polar == "normal":
        stars_am, desc_am = calculate_photography_rating(
            s_times.get("golden_hour_am_start"),
            s_times.get("golden_hour_am_end"),
            hourly_data,
            timezone_str
        )
        
        stars_pm, desc_pm = calculate_photography_rating(
            s_times.get("golden_hour_pm_start"),
            s_times.get("golden_hour_pm_end"),
            hourly_data,
            timezone_str
        )

    if mobile:
        mobile_console = Console(width=38)
        mobile_console.print(f"\n[bold yellow]📸 今日光影時刻 Golden Hour[/bold yellow]\n")
        
        full_text = Text()
        full_text.append(strip_vs16(f"📍 {loc_title}\n"), style="bold cyan")
        full_text.append(strip_vs16(f"🌐 緯度: {lat:.2f} 經度: {lon:.2f}\n"), style="dim")
        full_text.append(strip_vs16(f"⏰ 時區: {timezone_str}\n\n"), style="dim")
        
        if polar == "polar_day":
            full_text.append("☀️ 極晝狀態 Polar Day\n", style="bold yellow")
            full_text.append("  此區域目前處於極晝 (太陽終日不落)。\n", style="yellow")
            full_text.append("  全天均有日光，無傳統的日出/日落黃金與藍調光影。\n")
        elif polar == "polar_night":
            full_text.append("🌑 極夜狀態 Polar Night\n", style="bold blue")
            full_text.append("  此區域目前處於極夜 (太陽終日不出)。\n", style="bright_blue")
            full_text.append("  全天均為黑夜，無傳統的日出/日落黃金與藍調光影。\n")
        else:
            full_text.append("🌅 晨間晨光 Morning Light\n", style="bold cyan")
            full_text.append(f"  藍調 Blue  : {format_time(s_times.get('blue_hour_am_start'))} ~ {format_time(s_times.get('blue_hour_am_end'))}\n")
            full_text.append(f"  黃金 Gold  : {format_time(s_times.get('golden_hour_am_start'))} ~ {format_time(s_times.get('golden_hour_am_end'))}\n")
            full_text.append(f"  日出 Rise  : {format_time(s_times.get('sunrise'))}\n")
            full_text.append(f"  評估 Rate  : {get_stars_str(stars_am)}\n")
            full_text.append(f"  指引 Info  : {desc_am.split('！')[-1]}\n\n")
            
            full_text.append("🌇 傍晚暮光 Evening Light\n", style="bold orange1")
            full_text.append(f"  日落 Set   : {format_time(s_times.get('sunset'))}\n")
            full_text.append(f"  黃金 Gold  : {format_time(s_times.get('golden_hour_pm_start'))} ~ {format_time(s_times.get('golden_hour_pm_end'))}\n")
            full_text.append(f"  藍調 Blue  : {format_time(s_times.get('blue_hour_pm_start'))} ~ {format_time(s_times.get('blue_hour_pm_end'))}\n")
            full_text.append(f"  評估 Rate  : {get_stars_str(stars_pm)}\n")
            full_text.append(f"  指引 Info  : {desc_pm.split('！')[-1]}\n")
        
        mobile_console.print(strip_vs16(full_text))
        return

    # Desktop Card Rendering
    console.print(f"\n📍 {loc_title}", style="bold cyan")
    gps_info = f"🌐 緯度: {lat:.4f}  經度: {lon:.4f}  時區: {timezone_str}"
    console.print(gps_info, style="dim")
    
    if polar == "polar_day":
        polar_grid = Table.grid(padding=(0, 1))
        polar_grid.add_column(style="yellow")
        polar_grid.add_row("☀️ [bold]極晝狀態 (Polar Day) / Midnight Sun[/bold]")
        polar_grid.add_row("此地太陽今日終日不落。")
        polar_grid.add_row("整日均為白晝，可全天進行戶外拍攝，但無傳統日出/日落的黃金與藍調時刻。")
        polar_panel = Panel(polar_grid, border_style="yellow", width=108, title="☀️ 極晝狀態 Polar Day")
        
        container = Panel(
            polar_panel,
            title=strip_vs16("[bold yellow]📸 黃金時刻與藍調時刻 Golden & Blue Hour[/bold yellow]"),
            border_style="bright_blue",
            box=ROUNDED,
            width=112,
            padding=(1, 2)
        )
        console.print(container)
        return
    elif polar == "polar_night":
        polar_grid = Table.grid(padding=(0, 1))
        polar_grid.add_column(style="bright_blue")
        polar_grid.add_row("🌑 [bold]極夜狀態 (Polar Night) / Polar Night[/bold]")
        polar_grid.add_row("此地太陽今日終日不出。")
        polar_grid.add_row("整日均為黑夜，無傳統日出/日落的黃金與藍調時刻。")
        polar_panel = Panel(polar_grid, border_style="bright_blue", width=108, title="🌑 極夜狀態 Polar Night")
        
        container = Panel(
            polar_panel,
            title=strip_vs16("[bold yellow]📸 黃金時刻與藍調時刻 Golden & Blue Hour[/bold yellow]"),
            border_style="bright_blue",
            box=ROUNDED,
            width=112,
            padding=(1, 2)
        )
        console.print(container)
        return

    # Morning Light Table
    morning_table = Table.grid(padding=(0, 1), expand=True)
    morning_table.add_column(style="dim", width=22, min_width=22, no_wrap=True)
    morning_table.add_column(style="bold cyan", width=24, min_width=18)
    morning_table.add_row("晨間藍調 Blue Hour   :", f"{format_time(s_times.get('blue_hour_am_start'))} - {format_time(s_times.get('blue_hour_am_end'))}")
    morning_table.add_row("晨間黃金 Golden Hour :", f"{format_time(s_times.get('golden_hour_am_start'))} - {format_time(s_times.get('golden_hour_am_end'))}")
    morning_table.add_row("日出時刻 Sunrise     :", f"🌅 {format_time(s_times.get('sunrise'))}")
    
    color_tag_am = "bold green" if stars_am >= 4 else ("yellow" if stars_am >= 3 else "grey53")
    morning_table.add_row("晨間攝影推薦指數     :", f"[{color_tag_am}]{get_stars_str(stars_am)}[/{color_tag_am}]")
    morning_table.add_row("天氣實況與指引       :", f"[dim]{desc_am}[/dim]")
    
    # Evening Light Table
    evening_table = Table.grid(padding=(0, 1), expand=True)
    evening_table.add_column(style="dim", width=22, min_width=22, no_wrap=True)
    evening_table.add_column(style="bold orange1", width=24, min_width=18)
    evening_table.add_row("日落時刻 Sunset      :", f"🌇 {format_time(s_times.get('sunset'))}")
    evening_table.add_row("傍晚黃金 Golden Hour :", f"{format_time(s_times.get('golden_hour_pm_start'))} - {format_time(s_times.get('golden_hour_pm_end'))}")
    evening_table.add_row("傍晚藍調 Blue Hour   :", f"{format_time(s_times.get('blue_hour_pm_start'))} - {format_time(s_times.get('blue_hour_pm_end'))}")
    
    color_tag_pm = "bold green" if stars_pm >= 4 else ("yellow" if stars_pm >= 3 else "grey53")
    evening_table.add_row("傍晚攝影推薦指數     :", f"[{color_tag_pm}]{get_stars_str(stars_pm)}[/{color_tag_pm}]")
    evening_table.add_row("天氣實況與指引       :", f"[dim]{desc_pm}[/dim]")
    
    # Responsive design based on terminal width
    terminal_width = console.width
    
    # We need at least 112 cells to render side-by-side cleanly
    if terminal_width < 112:
        # Stack vertically
        layout_grid = Table.grid(padding=(1, 0))
        layout_grid.add_column(width=52)
        
        am_panel = Panel(morning_table, title="🌅 晨間光影 Morning Light", border_style="cyan", width=52)
        pm_panel = Panel(evening_table, title="🌇 傍晚光影 Evening Light", border_style="orange1", width=52)
        
        layout_grid.add_row(am_panel)
        layout_grid.add_row(pm_panel)
        
        container_width = 56
    else:
        # Render side-by-side
        layout_grid = Table.grid(padding=(0, 4))
        layout_grid.add_column(width=52)
        layout_grid.add_column(width=52)
        
        am_panel = Panel(morning_table, title="🌅 晨間光影 Morning Light", border_style="cyan", width=52)
        pm_panel = Panel(evening_table, title="🌇 傍晚光影 Evening Light", border_style="orange1", width=52)
        
        layout_grid.add_row(am_panel, pm_panel)
        
        container_width = 112
        
    container = Panel(
        layout_grid,
        title=strip_vs16("[bold yellow]📸 黃金時刻與藍調時刻 Golden & Blue Hour[/bold yellow]"),
        border_style="bright_blue",
        box=ROUNDED,
        width=container_width,
        padding=(1, 2)
    )
    console.print(container)
