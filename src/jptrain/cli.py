import click
import questionary
from typing import Dict, Any, List, Optional
from rich.console import Console
from jptrain import api
from jptrain.cache import SQLiteCache
from jptrain.formatter import (
    render_area_status,
    render_route_detail,
    to_traditional_chinese,
    get_status_info,
    render_route_search
)

console = Console()
# Delays change frequently, keep cache short (5 mins) for status, but areas can be cached longer
cache = SQLiteCache(expiration_seconds=300)

def fetch_areas_with_cache() -> List[Dict[str, Any]]:
    """Fetch all regions using cache first, then API."""
    cache_key = "regions"
    cached = cache.get(cache_key)
    if cached:
        return cached
        
    with console.status("[bold green]🔍 正在讀取日本鐵道區域資訊...[/bold green]"):
        areas = api.get_areas()
        
    if areas:
        # Cache the area list for 24 hours (86400 seconds)
        cache.set(cache_key, areas, custom_expiry=86400)
    return areas

def fetch_area_status_with_cache(area_code: str) -> Dict[str, Any]:
    """Fetch status for an area using cache first, then API."""
    cache_key = f"area:{area_code}"
    cached = cache.get(cache_key)
    if cached:
        return cached
        
    with console.status("[bold green]🚄 正在獲取鐵道運行狀態...[/bold green]"):
        status = api.get_area_status(area_code)
        
    if status:
        cache.set(cache_key, status)
    return status

def fetch_route_detail_with_cache(detail_path: str) -> Dict[str, Any]:
    """Fetch detailed delay description using cache first, then API."""
    cache_key = f"detail:{detail_path}"
    cached = cache.get(cache_key)
    if cached:
        return cached
        
    with console.status("[bold green]🔍 正在讀取詳細說明...[/bold green]"):
        detail = api.get_route_detail(detail_path)
        
    if detail:
        cache.set(cache_key, detail)
    return detail

def fetch_route_search_with_cache(from_station: str, to_station: str, date: Optional[str] = None, time: Optional[str] = None) -> Dict[str, Any]:
    """Fetch route search between two stations using cache first, then API."""
    cache_key = f"route_search:{from_station}:{to_station}:{date or ''}:{time or ''}"
    cached = cache.get(cache_key)
    if cached:
        result = cached
    else:
        with console.status("[bold green]🔍 正在查詢起訖站乘車路線與運行狀況...[/bold green]"):
            result = api.get_route_search(from_station, to_station, date, time)
        if result and not result.get("errors"):
            cache.set(cache_key, result)
            
    if result and not result.get("errors"):
        # Enrich any troubled lines with detailed delay description
        for r in result.get("routes", []):
            for s in r.get("segments", []):
                if s["type"] == "transport" and s["status"] != "平常運転" and s["detail_url"]:
                    detail = fetch_route_detail_with_cache(s["detail_url"])
                    if detail:
                        s["detail_desc"] = detail.get("description", "")
                        
    return result

def resolve_area(query: str, areas: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Resolve user query string (Japanese, Chinese, English or code) to an area."""
    query_clean = query.strip().lower()
    
    # Alias lookup
    aliases = {
        "關東": "関東", "kanto": "関東", "kantou": "関東",
        "關西": "近畿", "kansai": "近畿", "kinki": "近畿",
        "北海道": "北海道", "hokkaido": "北海道",
        "東北": "東北", "tohoku": "東北",
        "中部": "中部", "chubu": "中部",
        "中國": "中国", "chugoku": "中国", "中國地區": "中国",
        "四國": "四国", "shikoku": "四国",
        "九州": "九州", "kyushu": "九州"
    }
    
    target_name = aliases.get(query_clean, query_clean)
    
    for a in areas:
        if a["code"] == query_clean:
            return a
        if a["name"].lower() == target_name.lower():
            return a
        if target_name.lower() in a["name"].lower() or target_name.lower() in a["english"].lower():
            return a
            
    return None

@click.group(invoke_without_command=True)
@click.option("--mobile", is_flag=True, help="手機閱讀模式：最佳化排版以適合手機 38格寬度終端機。")
@click.pass_context
def cli(ctx, mobile):
    """
    🚄 日本鐵道即時運行狀況查詢工具 (Japan Train Status CLI)
    
    提供日本各地區（關東、關西、北海道等）鐵路、地鐵、新幹線的即時延誤與停駛資訊。
    支援中文、日文、英文地名地標與模糊搜尋，快取加速，最佳化排版。
    
    若直接執行不加子指令，將會開啟「互動引導選單」。
    
    \b
    使用範例 (Examples):
      $ uv run jptrain                               # 啟動互動引導選單
      $ uv run jptrain --mobile                      # 手機版互動選單
      $ uv run jptrain area "關東"                   # 查詢關東地區所有路線運行狀態
      $ uv run jptrain area "關西" --line "山手線"   # 查詢特定路線
      $ uv run jptrain info "山手線"                 # 查詢山手線詳細運行資訊
      $ uv run jptrain route "東京" "新宿"           # 查詢起訖站乘車路線 (轉乘最少優先)
      $ uv run jptrain route "荻窪" "白馬" --date "20261026" --time "0700" --show-stops  # 指定時間並顯示途中停靠站
      $ uv run jptrain clean                         # 清除本地快取
    """
    if ctx.invoked_subcommand is None:
        interactive_wizard(mobile)

def interactive_wizard(mobile: bool = False):
    """Start the interactive wizard."""
    console.print("\n[bold cyan]🚄 歡迎使用日本鐵道即時運行狀況查詢工具 (jptrain CLI)[/bold cyan]")
    console.print("[dim]本工具對接 Yahoo! 路線情報，提供全國鐵路延誤、停駛與營運概況。[/dim]\n")
    
    # Main Menu
    choice = questionary.select(
        "📝 請選擇查詢功能：",
        choices=[
            "1. 🗺️ 按地區查詢所有鐵路狀態 (Query by Region)",
            "2. 🔍 查詢起訖站間路線運行狀況 (Search Route between Stations)",
            "3. ❌ 退出 (Exit)"
        ],
        style=questionary.Style([
            ('pointer', 'fg:#00D7FF bold'),
            ('highlighted', 'fg:#00D7FF bold'),
        ])
    ).ask()
    
    if not choice or "退出" in choice:
        console.print("[dim]已退出。[/dim]")
        return
        
    if "查詢起訖站間路線" in choice:
        from_station = questionary.text("📝 請輸入起點站 (例如: 東京, 大原):").ask()
        if not from_station or not from_station.strip():
            return
            
        to_station = questionary.text("📝 請輸入終點站 (例如: 新宿, 上總中野):").ask()
        if not to_station or not to_station.strip():
            return
            
        specify_time = questionary.confirm("📅 是否需要指定出發日期與時間？(預設否/使用現在時間)", default=False).ask()
        date_input = None
        time_input = None
        if specify_time:
            date_input = questionary.text("📅 請輸入出發日期 (格式: YYYYMMDD, 例如 20260607, Enter 預設今天):").ask()
            time_input = questionary.text("⏰ 請輸入出發時間 (格式: HHMM, 例如 1045, Enter 預設現在):").ask()
            
            date_input = date_input.strip() if date_input and date_input.strip() else None
            time_input = time_input.strip() if time_input and time_input.strip() else None
            
        show_stops = questionary.confirm("🛤️ 是否要顯示列車途中停靠站點與時間？(預設否)", default=False).ask()
            
        result = fetch_route_search_with_cache(from_station.strip(), to_station.strip(), date_input, time_input)
        if result.get("errors"):
            for err in result["errors"]:
                console.print(f"[red]❌ {to_traditional_chinese(err)}[/red]")
            return
            
        render_route_search(from_station.strip(), to_station.strip(), result.get("routes", []), mobile=mobile, show_stops=show_stops)
        return
        
    areas = fetch_areas_with_cache()
    if not areas:
        console.print("[red]❌ 無法取得區域資訊，請檢查網路連線！[/red]")
        return
        
    # Region selection
    choices = []
    for a in areas:
        name_tc = to_traditional_chinese(a["name"])
        choices.append(questionary.Choice(
            title=f"{name_tc} ({a['english']})",
            value=a
        ))
    choices.append(questionary.Choice(title="❌ 退出 (Exit)", value=None))
    
    selected_area = questionary.select(
        "🗺️ 請選擇要查詢的地區：",
        choices=choices,
        style=questionary.Style([
            ('pointer', 'fg:#00D7FF bold'),
            ('highlighted', 'fg:#00D7FF bold'),
        ])
    ).ask()
    
    if not selected_area:
        console.print("[dim]已退出。[/dim]")
        return
        
    status_data = fetch_area_status_with_cache(selected_area["code"])
    if not status_data or not status_data.get("routes"):
        console.print("[red]❌ 無法取得該區域的鐵路路線，請稍後再試！[/red]")
        return
        
    routes = status_data.get("routes", [])
    update_time = status_data.get("update_time", "")
    
    # Show initial status
    render_area_status(selected_area["name"], routes, update_time=update_time, mobile=mobile)
    
    # Submenu loop for this area
    while True:
        action = questionary.select(
            "📊 請選擇後續操作：",
            choices=[
                "1. 🔍 查詢特定鐵路路線 (Search Route)",
                "2. ⚠️ 僅顯示有狀況的路線 (Troubled Only)",
                "3. 📋 顯示所有鐵路路線 (Show All)",
                "4. 🔙 返回區域選單 (Back to Regions)",
                "❌ 退出 (Exit)"
            ],
            style=questionary.Style([
                ('pointer', 'fg:#00D7FF bold'),
                ('highlighted', 'fg:#00D7FF bold'),
            ])
        ).ask()
        
        if not action or "退出" in action:
            console.print("[dim]已結束查詢。[/dim]")
            break
            
        elif "返回區域選單" in action:
            interactive_wizard(mobile)
            break
            
        elif "顯示所有" in action:
            render_area_status(selected_area["name"], routes, update_time=update_time, mobile=mobile)
            
        elif "僅顯示有狀況" in action:
            troubled = [r for r in routes if r["status"] != "平常運転"]
            if not troubled:
                console.print("\n[bold green]🟢 本區域目前沒有異常營運的路線！[/bold green]\n")
            else:
                render_area_status(selected_area["name"] + " - 異常簡報", troubled, update_time=update_time, mobile=mobile)
                
        elif "查詢特定鐵路路線" in action:
            search_query = questionary.text(
                "📝 請輸入路線名稱或鐵路公司 (例如: 山手線, JR, 東京地下鐵):"
            ).ask()
            
            if not search_query or not search_query.strip():
                continue
                
            q_clean = search_query.strip().lower()
            matches = []
            for r in routes:
                if (q_clean in r["route"].lower() or 
                    q_clean in r["operator"].lower() or 
                    to_traditional_chinese(q_clean) in to_traditional_chinese(r["route"]) or
                    to_traditional_chinese(q_clean) in to_traditional_chinese(r["operator"])):
                    matches.append(r)
                    
            if not matches:
                console.print(f"[yellow]⚠️ 找不到與「{search_query}」相關的路線！[/yellow]")
                continue
                
            # If multiple matches, ask user to choose
            if len(matches) > 1:
                route_choices = []
                for m in matches:
                    op_tc = to_traditional_chinese(m["operator"])
                    rt_tc = to_traditional_chinese(m["route"])
                    desc, emoji, _ = get_status_info(m["status"])
                    route_choices.append(questionary.Choice(
                        title=f"[{op_tc}] {rt_tc} ({emoji} {desc})",
                        value=m
                    ))
                route_choices.append(questionary.Choice(title="🔙 返回上層", value=None))
                
                selected_route = questionary.select(
                    "🔍 找到多個匹配路線，請選擇：",
                    choices=route_choices,
                    style=questionary.Style([
                        ('pointer', 'fg:#00D7FF bold'),
                        ('highlighted', 'fg:#00D7FF bold'),
                    ])
                ).ask()
                
                if not selected_route:
                    continue
            else:
                selected_route = matches[0]
                
            # Fetch and display detail
            if selected_route["detail_url"]:
                detail = fetch_route_detail_with_cache(selected_route["detail_url"])
                if not detail.get("update_time") and update_time:
                    detail["update_time"] = update_time
                render_route_detail(
                    selected_route["route"],
                    selected_route["operator"],
                    detail,
                    mobile=mobile
                )
            else:
                # Normal operation, no detail page
                detail = {
                    "status": selected_route["status"],
                    "description": selected_route["detail"],
                    "update_time": update_time
                }
                render_route_detail(
                    selected_route["route"],
                    selected_route["operator"],
                    detail,
                    mobile=mobile
                )

@cli.command()
@click.argument("region", required=True)
@click.option("--line", default="", help="篩選特定鐵路公司或路線名稱。")
@click.option("--mobile", is_flag=True, help="手機閱讀模式：最佳化排版以適合手機。")
@click.pass_context
def area(ctx, region, line, mobile):
    """
    查詢特定區域的鐵路運行狀態。
    
    [REGION] 可接受日文、中文、英文地區名稱或代碼 (如: 関東, kanto, 關西, 4)。
    """
    is_mobile = mobile or (ctx.parent.params.get("mobile") if ctx.parent else False)
    
    areas = fetch_areas_with_cache()
    if not areas:
        console.print("[red]❌ 無法取得區域資訊，請檢查網路連線。[/red]")
        return
        
    resolved = resolve_area(region, areas)
    if not resolved:
        console.print(f"[red]❌ 找不到地區「{region}」。可選區域：[/red]")
        for a in areas:
            console.print(f"  - {a['name']} ({a['english']}, 代碼: {a['code']})")
        return
        
    status_data = fetch_area_status_with_cache(resolved["code"])
    if not status_data or not status_data.get("routes"):
        console.print(f"[red]❌ 無法取得「{resolved['name']}」的運行狀態。[/red]")
        return
        
    routes = status_data.get("routes", [])
    update_time = status_data.get("update_time", "")
    
    if line:
        q_clean = line.strip().lower()
        filtered = []
        for r in routes:
            if (q_clean in r["route"].lower() or 
                q_clean in r["operator"].lower() or 
                to_traditional_chinese(q_clean) in to_traditional_chinese(r["route"]) or
                to_traditional_chinese(q_clean) in to_traditional_chinese(r["operator"])):
                filtered.append(r)
        if not filtered:
            console.print(f"[yellow]⚠️ 在「{resolved['name']}」中找不到與「{line}」相關的路線。[/yellow]")
            return
        render_area_status(f"{resolved['name']} - 篩選: {line}", filtered, update_time=update_time, mobile=is_mobile)
    else:
        render_area_status(resolved["name"], routes, update_time=update_time, mobile=is_mobile)

@cli.command()
@click.argument("route", required=True)
@click.option("--mobile", is_flag=True, help="手機閱讀模式：最佳化排版。")
@click.pass_context
def info(ctx, route, mobile):
    """
    查詢特定路線的詳細運行狀態與延誤原因。
    
    [ROUTE] 路線名稱 (如: 山手線, 京王線, 小田急)。
    """
    is_mobile = mobile or (ctx.parent.params.get("mobile") if ctx.parent else False)
    
    areas = fetch_areas_with_cache()
    if not areas:
        console.print("[red]❌ 無法取得區域資訊，請檢查網路連線。[/red]")
        return
        
    # Search for this route across all regions
    matches = []
    
    with console.status("[bold green]🔍 正在日本全國區域搜尋路線...[/bold green]"):
        for a in areas:
            # Check cached area statuses first to be very fast
            # If not cached, we'll fetch them, which might do API calls, but caching makes it fast
            status_data = fetch_area_status_with_cache(a["code"])
            routes = status_data.get("routes", []) if status_data else []
            area_update_time = status_data.get("update_time", "") if status_data else ""
            for r in routes:
                q_clean = route.strip().lower()
                if (q_clean in r["route"].lower() or
                    to_traditional_chinese(q_clean) in to_traditional_chinese(r["route"])):
                    # Avoid adding duplicates (sometimes a route is listed in multiple areas, though rare)
                    if not any(m["route"] == r["route"] and m["operator"] == r["operator"] for m in matches):
                        r_copy = r.copy()
                        r_copy["area_update_time"] = area_update_time
                        matches.append(r_copy)
                        
    if not matches:
        console.print(f"[red]❌ 在全國區域中找不到任何與「{route}」相符的路線。[/red]")
        return
        
    # If multiple matches, prompt user to select
    selected_route = None
    if len(matches) > 1:
        choices = []
        for m in matches:
            op_tc = to_traditional_chinese(m["operator"])
            rt_tc = to_traditional_chinese(m["route"])
            desc, emoji, _ = get_status_info(m["status"])
            choices.append(questionary.Choice(
                title=f"[{op_tc}] {rt_tc} ({emoji} {desc})",
                value=m
            ))
        choices.append(questionary.Choice(title="❌ 取消", value=None))
        
        selected_route = questionary.select(
            "🔍 找到多個同名或相似路線，請選擇要查詢的目標：",
            choices=choices,
            style=questionary.Style([
                ('pointer', 'fg:#00D7FF bold'),
                ('highlighted', 'fg:#00D7FF bold'),
            ])
        ).ask()
        
        if not selected_route:
            return
    else:
        selected_route = matches[0]
        
    # Fetch detail
    if selected_route["detail_url"]:
        detail = fetch_route_detail_with_cache(selected_route["detail_url"])
        if not detail.get("update_time") and selected_route.get("area_update_time"):
            detail["update_time"] = selected_route["area_update_time"]
        render_route_detail(
            selected_route["route"],
            selected_route["operator"],
            detail,
            mobile=is_mobile
        )
    else:
        detail = {
            "status": selected_route["status"],
            "description": selected_route["detail"],
            "update_time": selected_route.get("area_update_time", "")
        }
        render_route_detail(
            selected_route["route"],
            selected_route["operator"],
            detail,
            mobile=is_mobile
        )

@cli.command()
@click.argument("from_station", required=True)
@click.argument("to_station", required=True)
@click.option("--date", "-d", default=None, help="指定出發日期 (格式: YYYYMMDD，如 20260607)。預設使用今日。")
@click.option("--time", "-t", default=None, help="指定出發時間 (格式: HHMM，如 1045)。預設使用現在時間。")
@click.option("--show-stops", "-s", is_flag=True, help="顯示列車中途停靠站點與抵達時間。預設不顯示。")
@click.option("--mobile", is_flag=True, help="手機閱讀模式：最佳化排版。")
@click.pass_context
def route(ctx, from_station, to_station, date, time, show_stops, mobile):
    """
    查詢起訖站之間的乘車路線與鐵路運行狀況。
    
    [FROM_STATION] 出發站 (如: 東京, 上野)。
    [TO_STATION] 目的地站 (如: 新宿, 横浜)。
    
    \b
    特色說明 (Features):
      * 🔄 轉乘優先排序：乘車路線優先以「轉乘次數最少」進行排序。
      * ✈️ 智慧交通篩選：預設排除飛機與渡輪；若查無路線則自動啟用飛機與渡輪重新搜尋 (如往返沖繩或離島)。
      * 🛤️ 途中停靠站點：可指定 -s 顯示途中經過站點與各站抵達時間。
      * 📅 指定出發時間：可指定 -d 日期與 -t 時間查詢未來行程。
    """
    is_mobile = mobile or (ctx.parent.params.get("mobile") if ctx.parent else False)
    
    result = fetch_route_search_with_cache(from_station, to_station, date, time)
    if result.get("errors"):
        for err in result["errors"]:
            console.print(f"[red]❌ {to_traditional_chinese(err)}[/red]")
        return
        
    render_route_search(from_station, to_station, result.get("routes", []), mobile=is_mobile, show_stops=show_stops)

@cli.command()
def clean():
    """
    清除本地快取資料。
    """
    cache.clear()
    console.print("[bold green]✨ 本地鐵道運行與地區快取資料已成功清除！[/bold green]")

if __name__ == "__main__":
    cli()
