from typing import Dict, Any, List, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.box import ROUNDED
import re

console = Console()

# Translation dictionary from Japanese to Traditional Chinese for railway terms
TRANSLATION_MAP = {
    # Status
    "平常運転": "正常營運",
    "列車遅延": "列車延誤",
    "運転見合わせ": "暫停營運",
    "運転計画": "運行計畫",
    "運転再開": "恢復營運",
    "一部運休": "部分停駛",
    "運休": "停駛",
    "直通運転中止": "直通運轉中止",
    "ダイヤ乱れ": "時刻表混亂",
    "その他": "其他狀況",
    
    # Operators and general terms
    "電鉄": "電鐵",
    "鉄道": "鐵路",
    "急行": "急行",
    "高速": "高速",
    "地下鉄": "地下鐵",
    "都営": "都營",
    "市営": "市營",
    "新交通": "新交通",
    "モノレール": "單軌電車",
    "シーサイドライン": "海岸線",
    "ゆりかもめ": "百合鷗號",
    "ニューシャトル": "New Shuttle",
    "みなとみらい": "港未來",
    "ライトレール": "輕軌",
    "つくばエクスプレス": "筑波快線",
    
    # Common words in descriptions
    "影響": "影響",
    "遅れ": "延誤",
    "見合わせています": "暫停營運中",
    "事故": "事故",
    "大雪": "大雪",
    "強風": "強風",
    "地震": "地震",
    "台風": "颱風",
    "人身事故": "人身事故",
    "車両点検": "車輛檢修",
    "線路点検": "軌道檢修",
    "安全確認": "安全確認",
    "信号点検": "信號檢修",
    "停電": "停電",
    "架線トラブル": "電車線故障",
    "故障": "故障",
    "ドア点検": "車門檢修",
    "荷物挟まり": "夾物",
    "急病人の救護": "救護急病患者",
    "異音の確認": "確認異音",
    "倒木": "倒木",
    "土砂崩れ": "土石流",
    "大雨": "大雨",
    "規制": "管制",
    "見合わせ中": "暫停中",
    "一部": "部分",
    "区間": "區間",
    "見合わせ": "暫停",
    "に該当する出発地はありませんでした。": "的出發地不存在。",
    "に該当する目的地はありませんでした。": "的目的地不存在。",
    "出発地と目的地が同じです。": "出發地與目的地不能相同。",
    "出発地と目的地が同じ地点です。": "出發地與目的地不能為相同地點。",
    "経路検索ができませんでした。": "無法進行乘車路線查詢。",
}

STATUS_STYLING = {
    "平常運転": {"desc": "正常營運", "emoji": "🟢", "color": "green"},
    "列車遅延": {"desc": "列車延誤", "emoji": "🟡", "color": "yellow"},
    "運転見合わせ": {"desc": "暫停營運", "emoji": "🔴", "color": "red"},
    "運転計画": {"desc": "運行計畫", "emoji": "🔵", "color": "blue"},
    "その他": {"desc": "其他狀況", "emoji": "⚪", "color": "white"},
    "一部運休": {"desc": "部分停駛", "emoji": "🟠", "color": "orange1"},
    "直通運転中止": {"desc": "直通中止", "emoji": "🟠", "color": "orange1"},
    "ダイヤ乱れ": {"desc": "班次混亂", "emoji": "🟡", "color": "yellow"},
}

def to_traditional_chinese(text: str) -> str:
    """Translate Japanese railway terms and characters to Traditional Chinese."""
    if not isinstance(text, str):
        return text
        
    # Strip variation selector-16 first to ensure clean translations and alignment
    translated = text.replace("\ufe0f", "")
    
    # Translate known words/phrases first
    for jp, tc in TRANSLATION_MAP.items():
        translated = translated.replace(jp, tc)
        
    # Replace other specific characters
    char_map = {
        "駅": "車站",
        "線": "線",
        "区": "區",
        "東": "東",
        "西": "西",
        "南": "南",
        "北": "北",
        "国": "國",
        "鉄": "鐵",
        "乗": "乘",
        "車": "車",
        "発": "發",
        "広": "廣",
        "島": "島",
        "豊": "豐",
        "号": "號",
        "満": "滿",
        "風": "風",
        "雨": "雨",
        "雪": "雪",
        "強": "強",
        "遅": "遲",
    }
    for jp, tc in char_map.items():
        translated = translated.replace(jp, tc)
        
    # Replace wave dash and tilde which cause terminal character width mismatches
    translated = translated.replace("〜", "-").replace("～", "-")
    return translated

def strip_vs16(text: str) -> str:
    """Strip variation selector-16 (U+FE0F) to prevent terminal misalignment."""
    if isinstance(text, str):
        return text.replace("\ufe0f", "")
    return text

def get_status_info(status: str) -> tuple:
    """Get Chinese description, emoji, and color for a status."""
    info = STATUS_STYLING.get(status)
    if not info:
        # Check substring matches
        for key, val in STATUS_STYLING.items():
            if key in status:
                return val["desc"], val["emoji"], val["color"]
        return to_traditional_chinese(status), "⚠️", "white"
    return info["desc"], info["emoji"], info["color"]

def render_area_status(area_name: str, routes: List[Dict[str, Any]], update_time: str = "", mobile: bool = False):
    """Render the status list for a specific area."""
    if not routes:
        console.print("[red]❌ 無法取得該區域的鐵路運行狀況，請稍後再試！[/red]")
        return

    # Count statistics
    total = len(routes)
    troubled = [r for r in routes if r["status"] != "平常運転"]
    troubled_count = len(troubled)
    normal_count = total - troubled_count

    area_tc = to_traditional_chinese(area_name)
    title_text = f"🇯🇵 日本鐵路運行狀況 ({area_tc}地區)"
    
    update_time_tc = to_traditional_chinese(update_time)
    
    if mobile:
        mobile_console = Console(width=38)
        mobile_console.print(f"\n[bold yellow]🚄 {title_text}[/bold yellow]")
        time_str = f" 更新: {update_time_tc}" if update_time_tc else ""
        mobile_console.print(f"[dim]📊 總共: {total} 正常: {normal_count} 異常: {troubled_count}{time_str}[/dim]\n")
        
        # Display troubled ones first
        if troubled:
            mobile_console.print("[bold red]⚠️ 異常路線 Service Alert[/bold red]")
            for r in troubled:
                desc, emoji, color = get_status_info(r["status"])
                route_tc = to_traditional_chinese(r["route"])
                operator_tc = to_traditional_chinese(r["operator"])
                detail_tc = to_traditional_chinese(r["detail"])
                
                line = Text()
                line.append(f"● [{operator_tc}] {route_tc}\n", style=f"bold {color}")
                line.append(f"  狀態: {emoji} {desc}\n", style=color)
                line.append(f"  詳情: {detail_tc}\n", style="white")
                mobile_console.print(strip_vs16(line))
        else:
            mobile_console.print("[bold green]🟢 所有路線營運正常。[/bold green]\n")
            
        return

    # Desktop presentation
    console.print(f"\n[bold yellow]🚄 {title_text}[/bold yellow]")
    time_str = f" | ⏰ 數據時間: {update_time_tc}" if update_time_tc else ""
    console.print(f"📊 營運統計: [bold]{total}[/bold] 條路線 | [bold green]{normal_count}[/bold green] 條正常 | [bold red]{troubled_count}[/bold red] 條異常{time_str}\n")

    # If there are troubled lines, show a alert panel
    if troubled:
        trouble_table = Table(box=ROUNDED, border_style="red", header_style="bold red", width=95)
        trouble_table.add_column("鐵路公司 / 路線 Operator & Line")
        trouble_table.add_column("狀態 Status", justify="center")
        trouble_table.add_column("說明 Description", overflow="fold")
        
        for r in troubled:
            desc, emoji, color = get_status_info(r["status"])
            route_tc = to_traditional_chinese(r["route"])
            operator_tc = to_traditional_chinese(r["operator"])
            detail_tc = to_traditional_chinese(r["detail"])
            
            line_display = f"[bold]{operator_tc}[/bold]\n[dim]{route_tc}[/dim]"
            status_display = f"[{color}]{emoji} {desc}[/{color}]"
            
            trouble_table.add_row(
                strip_vs16(line_display),
                strip_vs16(status_display),
                strip_vs16(detail_tc)
            )
            
        panel = Panel(
            trouble_table,
            title=strip_vs16("⚠️ [bold red]異常運行狀況運行中 Service Interruptions[/bold red]"),
            border_style="red",
            expand=False
        )
        console.print(panel)
        console.print()

    # Show all lines grouped by operator
    table = Table(box=ROUNDED, border_style="bright_blue", header_style="bold cyan", width=95)
    table.add_column("鐵路公司 Operator")
    table.add_column("路線 Route Line")
    table.add_column("狀態 Status", justify="center")
    table.add_column("概況 Details", overflow="fold")

    for r in routes:
        desc, emoji, color = get_status_info(r["status"])
        route_tc = to_traditional_chinese(r["route"])
        operator_tc = to_traditional_chinese(r["operator"])
        detail_tc = to_traditional_chinese(r["detail"])
        
        status_display = f"[{color}]{emoji} {desc}[/{color}]"
        
        table.add_row(
            strip_vs16(operator_tc),
            strip_vs16(route_tc),
            strip_vs16(status_display),
            strip_vs16(detail_tc)
        )
        
    console.print(table)

def render_route_detail(route_name: str, operator: str, detail: Dict[str, Any], mobile: bool = False):
    """Render a detailed panel for a specific railway line."""
    status_raw = detail.get("status", "未知")
    desc_raw = detail.get("description", "無詳細說明。")
    time_raw = detail.get("update_time", "")
    
    desc_tc, emoji, color = get_status_info(status_raw)
    route_tc = to_traditional_chinese(route_name)
    operator_tc = to_traditional_chinese(operator)
    desc_tc_full = to_traditional_chinese(desc_raw)
    time_tc = to_traditional_chinese(time_raw)
    
    if mobile:
        mobile_console = Console(width=38)
        mobile_console.print(f"\n[bold yellow]🚄 路線詳細運行資訊[/bold yellow]")
        
        info_text = Text()
        info_text.append(strip_vs16(f"📍 路線: [{operator_tc}] {route_tc}\n"), style="bold cyan")
        info_text.append(strip_vs16(f"📊 狀態: {emoji} {desc_tc}\n"), style=f"bold {color}")
        if time_tc:
            info_text.append(strip_vs16(f"⏰ 更新: {time_tc}\n"), style="dim")
        info_text.append(strip_vs16("\n詳細內容:\n"), style="bold white")
        info_text.append(strip_vs16(f"{desc_tc_full}\n"), style="white")
        
        if status_raw != "平常運転":
            info_text.append(strip_vs16("\n💡 提示:\n"), style="bold yellow")
            info_text.append(strip_vs16("建議提早出門，使用地鐵/私鐵等替代路網，或利用乘換案內尋找迂迴路線。\n"), style="yellow")
            
        mobile_console.print(strip_vs16(info_text))
        return

    # Desktop Card
    main_text = Text()
    main_text.append(strip_vs16(f"📍 鐵道公司: {operator_tc}\n"), style="cyan")
    main_text.append(strip_vs16(f"🛤️  運行路線: {route_tc}\n"), style="cyan")
    main_text.append(strip_vs16(f"📊 營運狀態: {emoji} {desc_tc}\n"), style=f"bold {color}")
    if time_tc:
        main_text.append(strip_vs16(f"⏰ 資訊發布: {time_tc}\n"), style="dim")
        
    main_text.append(strip_vs16("\n詳細情況 Description:\n"), style="bold white")
    main_text.append(strip_vs16(f"{desc_tc_full}\n"), style="white")
    
    # Suggestion box if not running normally
    if status_raw != "平常運転":
        main_text.append(strip_vs16("\n" + "="*50 + "\n"))
        main_text.append(strip_vs16("💡 Antigravity 乘車叮嚀 (Travel Tips):\n"), style="yellow")
        main_text.append(strip_vs16("• 列車可能出現大幅度延誤或臨時停駛，請預留充足轉乘時間。\n"), style="yellow")
        main_text.append(strip_vs16("• 請檢查車站電子看板以獲得最新班次，或詢問站務人員。\n"), style="yellow")
        main_text.append(strip_vs16("• 若需趕往機場，建議優先選擇京成 Skyliner/利木津巴士等替代交通工具。\n"), style="yellow")
        
    panel = Panel(
        main_text,
        title=strip_vs16(f"[bold yellow]🚄 {operator_tc} - {route_tc} 運行詳情[/bold yellow]"),
        border_style=color,
        box=ROUNDED,
        width=80,
        padding=(1, 2)
    )
    console.print(panel)

def translate_route_summary_text(text: str) -> str:
    """Translate Japanese terms in route summary to Traditional Chinese."""
    if not text:
        return ""
    text = text.replace("発→", " 出發 →")
    text = text.replace("着", " 抵達")
    text = text.replace("分", "分鐘")
    text = text.replace("時間", "小時")
    text = text.replace("（乗車", "（乘車")
    text = text.replace("乗換：", "轉乘：")
    text = text.replace("回", "次")
    text = text.replace("IC優先：", "IC卡優先：")
    text = text.replace("円", "日圓")
    return to_traditional_chinese(text)

def format_destination(dest: str) -> str:
    """Format and translate route destination suffix and prefixes."""
    if not dest:
        return ""
    dest = dest.replace("当駅始発", "當站始發")
    if dest.endswith("行"):
        dest = dest[:-1]
    return to_traditional_chinese(dest)

def render_route_search(from_station: str, to_station: str, routes: List[Dict[str, Any]], mobile: bool = False, show_stops: bool = False):
    """Render route search options between two stations."""
    if not routes:
        console.print("[red]❌ 無法取得任何乘車路線資訊，請確認起訖站名稱是否正確。[/red]")
        return

    from_tc = to_traditional_chinese(from_station)
    to_tc = to_traditional_chinese(to_station)
    title_text = f"🔍 乘車路線與運行狀況查詢：{from_tc} → {to_tc}"

    priority_map = {"早": "⏱️ 最快", "楽": "😌 最方便", "安": "💰 最便宜"}

    if mobile:
        mobile_console = Console(width=38)
        mobile_console.print(f"\n[bold yellow]{title_text}[/bold yellow]\n")
        
        for idx, r in enumerate(routes, 1):
            title_zh = r["title"].replace("ルート", "方案")
            # Format priorities
            pri_strs = [priority_map.get(p, p) for p in r["priorities"]]
            pri_info = f" ({' '.join(pri_strs)})" if pri_strs else ""
            
            # Clean summary info
            time_clean = translate_route_summary_text(r["time"])
            transfer_clean = translate_route_summary_text(r["transfer"])
            fare_clean = translate_route_summary_text(r["fare"])
            
            mobile_console.print(f"[bold cyan]■ {title_zh}{pri_info}[/bold cyan]")
            mobile_console.print(f"[dim]時間: {time_clean}[/dim]")
            mobile_console.print(f"[dim]{transfer_clean} | 票價: {fare_clean}[/dim]\n")
            
            # Print vertical timeline
            for s in r["segments"]:
                if s["type"] == "station":
                    st_name = to_traditional_chinese(s["name"])
                    st_status = "出發" if s["status"] == "発" else ("抵達" if s["status"] == "着" else to_traditional_chinese(s["status"]))
                    mobile_console.print(f" ● {st_name} [{s['time']}] ({st_status})")
                else:
                    line_name = to_traditional_chinese(s["name"])
                    desc, emoji, color = get_status_info(s["status"])
                    dest_info = f" (往 {format_destination(s['destination'])})" if s["destination"] else ""
                    mobile_console.print(f"   ↓ [{color}]{line_name}[/{color}]{dest_info} [{color}]{emoji} {desc}[/{color}]")
                    if show_stops and s.get("stops"):
                        for stop_idx, stop in enumerate(s["stops"]):
                            stop_name_tc = to_traditional_chinese(stop["name"])
                            is_last = (stop_idx == len(s["stops"]) - 1)
                            branch = "└─" if is_last else "├─"
                            mobile_console.print(f"     [dim]{branch} {stop_name_tc} [{stop['time']}][/dim]")
                    if s.get("detail_desc"):
                        detail_tc = to_traditional_chinese(s["detail_desc"])
                        mobile_console.print(f"     [yellow]⚠️ 詳情: {detail_tc}[/yellow]")
            mobile_console.print("\n" + "-"*36 + "\n")
        return

    # Desktop presentation
    console.print(f"\n[bold yellow]🚄 {title_text}[/bold yellow]\n")

    for idx, r in enumerate(routes, 1):
        title_zh = r["title"].replace("ルート", "方案")
        pri_strs = [priority_map.get(p, p) for p in r["priorities"]]
        pri_info = f"  [{' '.join(pri_strs)}]" if pri_strs else ""
        
        # Clean summary info
        time_clean = translate_route_summary_text(r["time"])
        transfer_clean = translate_route_summary_text(r["transfer"])
        fare_clean = translate_route_summary_text(r["fare"])
        dist_clean = translate_route_summary_text(r["distance"])
        
        # Build segment flow
        flow_text = Text()
        flow_text.append("📊 乘車時間：", style="bold yellow")
        flow_text.append(f"{time_clean}\n", style="bold white")
        flow_text.append("-" * 70 + "\n\n", style="dim")
        
        for s in r["segments"]:
            if s["type"] == "station":
                st_name = to_traditional_chinese(s["name"])
                st_status = "出發" if s["status"] == "発" else ("抵達" if s["status"] == "着" else to_traditional_chinese(s["status"]))
                flow_text.append(f" ● {st_name}", style="bold cyan")
                if s["time"]:
                    flow_text.append(f" [{s['time']}]", style="green")
                flow_text.append(f" ({st_status})\n", style="dim")
            else:
                line_name = to_traditional_chinese(s["name"])
                desc, emoji, color = get_status_info(s["status"])
                dest_info = f" → 往 {format_destination(s['destination'])}" if s["destination"] else ""
                
                flow_text.append("   │\n", style="dim")
                flow_text.append("   │   ", style="dim")
                flow_text.append(f"[{line_name}]", style=f"bold {color}")
                flow_text.append(dest_info, style="white")
                flow_text.append(f"  ({strip_vs16(emoji)} {desc})\n", style=f"bold {color}")
                
                if show_stops and s.get("stops"):
                    flow_text.append("   │      (途中停靠):\n", style="dim")
                    for stop_idx, stop in enumerate(s["stops"]):
                        stop_name_tc = to_traditional_chinese(stop["name"])
                        is_last = (stop_idx == len(s["stops"]) - 1)
                        branch = "      └─" if is_last else "      ├─"
                        flow_text.append(f"   │   {branch} {stop_name_tc}", style="dim")
                        flow_text.append(f" [{stop['time']}]\n", style="green")
                        
                if s.get("detail_desc"):
                    detail_tc = to_traditional_chinese(s["detail_desc"])
                    flow_text.append("   │   ", style="dim")
                    flow_text.append(strip_vs16("⚠️ 運行詳情: "), style="yellow")
                    flow_text.append(f"{detail_tc}\n", style="yellow")
                flow_text.append("   │\n", style="dim")
                
        summary_bottom = f"🔄 {transfer_clean}  |  💰 {fare_clean}  |  📏 {dist_clean}"
                
        panel = Panel(
            strip_vs16(flow_text),
            title=strip_vs16(f"[bold yellow]🚄 {title_zh}{pri_info}[/bold yellow]"),
            subtitle=strip_vs16(f"[bold white]{summary_bottom}[/bold white]"),
            border_style="bright_blue",
            box=ROUNDED,
            width=90,
            padding=(1, 2)
        )
        console.print(panel)
        console.print()

