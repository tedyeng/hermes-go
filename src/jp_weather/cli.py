import click
import questionary
from typing import Dict, Any, Optional
from rich.console import Console
from jp_weather import api
from jp_weather.cache import SQLiteCache
from jp_weather.formatter import (
    select_location_interactive,
    render_current_weather,
    render_forecast_weather,
    format_location_title,
    render_golden_hour
)

console = Console()
cache = SQLiteCache(expiration_seconds=900) # Weather cache defaults to 15 mins

def get_location_or_prompt(query: str, interactive: bool = True) -> Optional[Dict[str, Any]]:
    """
    Resolve location from query (using cache first, then API).
    If multiple locations are found and interactive is True, prompts user to select.
    """
    if not query:
        return None
        
    cache_key = f"geo:{query.lower()}"
    cached_locs = cache.get(cache_key)
    
    if cached_locs:
        locations = cached_locs
    else:
        with console.status("[bold green]🔍 正在搜尋地點 Geocoding...[/bold green]"):
            locations = api.geocode(query)
        if locations:
            # Cache geocoding results for 24 hours (86400 seconds)
            cache.set(cache_key, locations, custom_expiry=86400)
            
    if not locations:
        return None
        
    if len(locations) == 1:
        return locations[0]
        
    if interactive:
        return select_location_interactive(locations)
    else:
        # Non-interactive: pick the top match
        return locations[0]

def fetch_weather_with_cache(loc: dict) -> Optional[Dict[str, Any]]:
    """Fetch weather data for a location using cache first, then the API.

    Returns ``None`` if the API request fails.
    """
    lat = loc.get("latitude")
    lon = loc.get("longitude")
    timezone = loc.get("timezone", "Asia/Tokyo")

    cache_key = f"weather:{lat:.4f}:{lon:.4f}"
    cached_weather = cache.get(cache_key)
    if cached_weather:
        return cached_weather

    with console.status("[bold green]🌤️ 正在取得氣象預報...[/bold green]"):
        weather = api.get_weather(lat, lon, timezone)

    # ``weather`` may be ``None`` if the request failed.
    if weather:
        cache.set(cache_key, weather)
        return weather
    else:
        return None

@click.group(invoke_without_command=True)
@click.option("--mobile", is_flag=True, help="手機閱讀模式：最佳化排版以適合手機 (如 iPhone 16 Pro) 38格寬度終端機。")
@click.pass_context
def cli(ctx, mobile):
    """
    🇯🇵 日本與全球氣象天氣查詢 CLI 工具 (Japan & Global Weather CLI)
    
    支援中英日地名地標、日本行政區智慧補全、日本郵遞區號以及 GPS 十進位/DMS 度分秒座標直查。
    優先調用日本氣象廳 (JMA) 高解析度網格，並自動 Fallback 支援全球無縫高解析度氣象模型。
    
    若直接執行不加子指令，將會開啟「互動引導模式」。
    
    \b
    使用範例 (Examples):
      $ uv run jp-weather                                                 # 啟動互動引導選單
      $ uv run jp-weather --mobile                                        # 啟動手機版引導選單
      $ uv run jp-weather current "東京"                                  # 查詢東京即時天氣
      $ uv run jp-weather current "東京" --mobile                         # 手機版查詢即時天氣
      $ uv run jp-weather forecast "Kyoto"                                # 查詢京都一週預報
      $ uv run jp-weather golden "東京"                                   # 查詢黃金/藍調拍攝時刻
      $ uv run jp-weather golden "京都" --week                            # 查詢一週光影預報
      $ uv run jp-weather current "東京" --no-interactive                 # 靜態模式 (跳過地點選擇)
      $ uv run jp-weather current "100-0001"                              # 查詢日本郵遞區號
      $ uv run jp-weather current "35.68,139.6"                           # 查詢 GPS 十進位座標
      $ uv run jp-weather current "北緯25°5′0″ 東經121°34′43″"            # 查詢度分秒座標
      $ uv run jp-weather clean                                           # 清除本地 SQLite 快取
    """
    if ctx.invoked_subcommand is None:
        interactive_wizard(mobile)

def interactive_wizard(mobile: bool = False):
    """Default interactive wizard when running without subcommands."""
    console.print("\n[bold cyan]🇯🇵 歡迎使用日本天氣查詢工具 (Japan Weather CLI)[/bold cyan]")
    console.print("[dim]本工具對接日本氣象廳 (JMA) 相關模型與 Open-Meteo API，免金鑰且快取加速。[/dim]\n")
    
    query = questionary.text(
        "📝 請輸入日本地名、地址或郵遞區號 (如: 東京, 京都, 100-0001):",
        style=questionary.Style([
            ('question', 'bold fg:#ffffff'),
        ])
    ).ask()
    
    if not query or not query.strip():
        console.print("[red]❌ 輸入不能為空！[/red]")
        return
        
    loc = get_location_or_prompt(query, interactive=True)
    if not loc:
        console.print(f"[red]❌ 找不到與「{query}」相關的日本地點，請換個詞試試！[/red]")
        return
    if isinstance(loc, dict) and loc.get("cancelled"):
        console.print("[dim]已取消查詢。[/dim]")
        return
        
    weather = fetch_weather_with_cache(loc)
    if not weather:
        console.print("[red]❌ 無法取得天氣預報資料，請稍後再試！[/red]")
        return
        
    # Interactive query type
    qtype = questionary.select(
        "📊 請選擇要查詢的天氣類型：",
        choices=[
            "1. ☀️ 即時天氣狀態 (Current Weather)",
            "2. 📅 7 天天氣預報 (7-Day Forecast)",
            "3. 🌟 兩者皆顯示 (Both)",
            "4. 📸 黃金/藍調拍照時刻 (Golden/Blue Hour)",
            "❌ 退出 (Exit)"
        ],
        style=questionary.Style([
            ('pointer', 'fg:#00D7FF bold'),
            ('highlighted', 'fg:#00D7FF bold'),
        ])
    ).ask()
    
    if qtype and "1." in qtype:
        render_current_weather(loc, weather, mobile=mobile)
    elif qtype and "2." in qtype:
        render_forecast_weather(loc, weather, mobile=mobile)
    elif qtype and "3." in qtype:
        render_current_weather(loc, weather, mobile=mobile)
        render_forecast_weather(loc, weather, mobile=mobile)
    elif qtype and "4." in qtype:
        period = questionary.select(
            "📅 請選擇查詢範圍：",
            choices=[
                "1. 今日光影時刻 (Today Only)",
                "2. 未來一週光影預報 (7-Day Outlook)"
            ],
            style=questionary.Style([
                ('pointer', 'fg:#00D7FF bold'),
                ('highlighted', 'fg:#00D7FF bold'),
            ])
        ).ask()
        
        if period and "1." in period:
            render_golden_hour(loc, weather, week=False, mobile=mobile)
        elif period and "2." in period:
            render_golden_hour(loc, weather, week=True, mobile=mobile)
    else:
        console.print("[dim]已退出。[/dim]")

@cli.command()
@click.argument("location", required=True)
@click.option("--no-interactive", is_flag=True, help="非互動模式：自動選取第一個匹配的地點。")
@click.option("--mobile", is_flag=True, help="手機閱讀模式：最佳化排版以適合手機 (如 iPhone 16 Pro) 38格寬度終端機。")
@click.pass_context
def current(ctx, location, no_interactive, mobile):
    """
    查詢目前即時天氣狀況與未來 24 小時的 3 小時預報走勢。
    
    [LOCATION] 可接受地名、地標景區、日本郵遞區號、GPS十進位座標或 DMS 度分秒座標。
    
    \b
    使用範例 (Examples):
      $ uv run jp-weather current "東京"
      $ uv run jp-weather current "100-0001"
      $ uv run jp-weather current "35.6895, 139.6917"             # GPS 十進位
      $ uv run jp-weather current "北緯25°5′0″ 東經121°34′43″"    # DMS 度分秒
      $ uv run jp-weather current "東京" --no-interactive          # 腳本靜態模式
    """
    is_mobile = mobile or (ctx.parent.params.get("mobile") if ctx.parent else False)
    
    loc = get_location_or_prompt(location, interactive=not no_interactive)
    if not loc:
        console.print(f"[red]❌ 找不到與「{location}」相關的日本地點。[/red]")
        return
    if isinstance(loc, dict) and loc.get("cancelled"):
        console.print("[dim]已取消查詢。[/dim]")
        return
        
    weather = fetch_weather_with_cache(loc)
    if not weather:
        console.print("[red]❌ 無法取得天氣資料。[/red]")
        return
        
    render_current_weather(loc, weather, mobile=is_mobile)

@cli.command()
@click.argument("location", required=True)
@click.option("--no-interactive", is_flag=True, help="非互動模式：自動選取第一個匹配的地點。")
@click.option("--mobile", is_flag=True, help="手機閱讀模式：最佳化排版以適合手機 (如 iPhone 16 Pro) 38格寬度終端機。")
@click.pass_context
def forecast(ctx, location, no_interactive, mobile):
    """
    查詢一週 (7天) 天氣預報（氣溫變化、降雨機率、紫外線 UV 等）。
    
    [LOCATION] 可接受地名、地標景區、日本郵遞區號、GPS十進位座標或 DMS 度分秒座標。
    
    \b
    使用範例 (Examples):
      $ uv run jp-weather forecast "大阪"
      $ uv run jp-weather forecast "Kyoto"
      $ uv run jp-weather forecast "35.6895, 139.6917"             # GPS 十進位
      $ uv run jp-weather forecast "北緯25°5′0″ 東經121°34′43″"    # DMS 度分秒
      $ uv run jp-weather forecast "京都" --no-interactive          # 腳本靜態模式
    """
    is_mobile = mobile or (ctx.parent.params.get("mobile") if ctx.parent else False)
    
    loc = get_location_or_prompt(location, interactive=not no_interactive)
    if not loc:
        console.print(f"[red]❌ 找不到與「{location}」相關的日本地點。[/red]")
        return
    if isinstance(loc, dict) and loc.get("cancelled"):
        console.print("[dim]已取消查詢。[/dim]")
        return
        
    weather = fetch_weather_with_cache(loc)
    if not weather:
        console.print("[red]❌ 無法取得天氣資料。[/red]")
        return
        
    render_forecast_weather(loc, weather, mobile=is_mobile)

@cli.command()
def clean():
    """
    清除本地快取資料。
    """
    cache.clear()
    console.print("[bold green]✨ 本地天氣與地名快取資料已成功清除！[/bold green]")

@cli.command()
@click.argument("location", required=True)
@click.option("--week", is_flag=True, help="顯示未來一週 (7天) 的黃金與藍調時刻預報。")
@click.option("--no-interactive", is_flag=True, help="非互動模式：自動選取第一個匹配的地點。")
@click.option("--mobile", is_flag=True, help="手機閱讀模式：最佳化排版以適合手機 (如 iPhone 16 Pro) 38格寬度終端機。")
@click.pass_context
def golden(ctx, location, week, no_interactive, mobile):
    """
    📸 查詢黃金時刻（Golden Hour）與藍調時刻（Blue Hour）起訖時間與攝影推薦指數。
    
    [LOCATION] 可接受地名、地標景區、日本郵遞區號、GPS十進位座標或 DMS 度分秒座標。
    
    \b
    使用範例 (Examples):
      $ uv run jp-weather golden "東京"
      $ uv run jp-weather golden "京都" --week
      $ uv run jp-weather golden "富士山" --mobile
      $ uv run jp-weather golden "35.68,139.69" --no-interactive
    """
    is_mobile = mobile or (ctx.parent.params.get("mobile") if ctx.parent else False)
    
    loc = get_location_or_prompt(location, interactive=not no_interactive)
    if not loc:
        console.print(f"[red]❌ 找不到與「{location}」相關的日本地點。[/red]")
        return
    if isinstance(loc, dict) and loc.get("cancelled"):
        console.print("[dim]已取消查詢。[/dim]")
        return
        
    weather = fetch_weather_with_cache(loc)
    if not weather:
        console.print("[red]❌ 無法取得天氣資料。[/red]")
        return
        
    render_golden_hour(loc, weather, week=week, mobile=is_mobile)

if __name__ == "__main__":
    cli()
