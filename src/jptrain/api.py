import requests
from bs4 import BeautifulSoup
import logging
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger("jptrain.api")

BASE_URL = "https://transit.yahoo.co.jp"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# Default hardcoded mapping for regions just in case scraping fails
DEFAULT_AREAS = [
    {"name": "北海道", "code": "2", "english": "Hokkaido"},
    {"name": "東北", "code": "3", "english": "Tohoku"},
    {"name": "関東", "code": "4", "english": "Kanto"},
    {"name": "中部", "code": "5", "english": "Chubu"},
    {"name": "近畿", "code": "6", "english": "Kinki/Kansai"},
    {"name": "中国", "code": "8", "english": "Chugoku"},
    {"name": "四国", "code": "9", "english": "Shikoku"},
    {"name": "九州", "code": "7", "english": "Kyushu"}
]

def fetch_html(url: str) -> Optional[str]:
    """Helper to fetch HTML with a custom User-Agent and timeout."""
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.text
        logger.error(f"Failed to fetch {url}: status code {r.status_code}")
    except Exception as e:
        logger.error(f"Exception during fetch of {url}: {e}", exc_info=True)
    return None

def get_areas() -> List[Dict[str, Any]]:
    """Scrape the main page to find all area codes and names."""
    url = f"{BASE_URL}/diainfo"
    html = fetch_html(url)
    if not html:
        return DEFAULT_AREAS

    try:
        soup = BeautifulSoup(html, "html.parser")
        # Find links like href="/diainfo/area/4"
        pattern = re.compile(r'/diainfo/area/(\d+)')
        
        scraped_areas = []
        seen_codes = set()
        
        # Yahoo lists areas in various links
        for a in soup.find_all("a", href=pattern):
            href = a.get("href")
            match = pattern.search(href)
            if match:
                code = match.group(1)
                if code not in seen_codes:
                    seen_codes.add(code)
                    name = a.text.strip()
                    # Find English name if possible
                    english = ""
                    for item in DEFAULT_AREAS:
                        if item["name"] == name or item["code"] == code:
                            english = item["english"]
                            break
                    scraped_areas.append({
                        "name": name,
                        "code": code,
                        "english": english or name
                    })
        
        if scraped_areas:
            # Sort by area code to keep consistency
            scraped_areas.sort(key=lambda x: int(x["code"]))
            return scraped_areas
    except Exception as e:
        logger.warning(f"Error parsing areas: {e}. Falling back to default list.")
    
    return DEFAULT_AREAS

def get_area_status(area_code: str) -> Dict[str, Any]:
    """Scrape and parse all railway line statuses in a given area."""
    url = f"{BASE_URL}/diainfo/area/{area_code}"
    html = fetch_html(url)
    if not html:
        return {"routes": [], "update_time": ""}

    routes = []
    update_time = ""
    try:
        soup = BeautifulSoup(html, "html.parser")
        
        # Find the general update time of the area status page
        time_span = soup.find("span", class_="subText")
        if time_span:
            update_time = time_span.text.strip().replace("<!-- -->", "")
            
        all_divs = soup.find_all("div", class_=lambda x: x and "elmTblLstLine" in x)
        
        for div in all_divs:
            # Identify the operator name by looking backward at the nearest heading
            prev = div.find_previous(["h1", "h2", "h3", "h4", "h5", "h6"])
            operator = "未知"
            if prev:
                operator = prev.text.strip()
                # Clean comments or HTML elements inside heading
                operator = re.sub(r'<!--.*?-->', '', str(operator))
                operator = BeautifulSoup(operator, "html.parser").text.strip()
                
            # Skip the trouble summary section at the top (it duplicates routes listed below)
            if "現在運行情報のある路線" in operator:
                continue
                
            table = div.find("table")
            if not table:
                continue
                
            rows = table.find_all("tr")[1:]  # Skip header tr
            for row in rows:
                tds = row.find_all("td")
                if len(tds) < 3:
                    continue
                
                a_tag = tds[0].find("a")
                route_name = a_tag.text.strip() if a_tag else tds[0].text.strip()
                detail_url = a_tag["href"] if a_tag else None
                
                status = tds[1].text.strip()
                detail = tds[2].text.strip()
                
                # Fetch full untruncated description if not running normally
                if status != "平常運転" and detail_url:
                    route_detail = get_route_detail(detail_url)
                    if route_detail and route_detail.get("description"):
                        detail = route_detail["description"]
                
                routes.append({
                    "operator": operator,
                    "route": route_name,
                    "status": status,
                    "detail": detail,
                    "detail_url": detail_url
                })
    except Exception as e:
        logger.error(f"Error parsing area status for code {area_code}: {e}", exc_info=True)
        
    return {
        "routes": routes,
        "update_time": update_time
    }

def get_route_detail(detail_path: str) -> Dict[str, Any]:
    """Scrape and parse full route delay details and update time."""
    # Ensure detail_path starts with slash and doesn't duplicate base url
    if detail_path.startswith("http"):
        url = detail_path
    else:
        path = detail_path if detail_path.startswith("/") else f"/{detail_path}"
        url = f"{BASE_URL}{path}"
        
    html = fetch_html(url)
    if not html:
        return {"status": "未知", "description": "無法取得詳細資訊。", "update_time": ""}
        
    try:
        soup = BeautifulSoup(html, "html.parser")
        status_div = soup.find("div", id="mdServiceStatus")
        
        if status_div:
            dt = status_div.find("dt")
            status = dt.text.strip() if dt else "未知"
            
            dd = status_div.find("dd")
            if dd:
                p = dd.find("p")
                if p:
                    # Extract publication time span if present
                    span = p.find("span")
                    update_time = ""
                    if span:
                        update_time = span.text.strip().strip("（）() ")
                        span.decompose()
                    desc = p.text.strip()
                else:
                    desc = dd.text.strip()
                    update_time = ""
            else:
                desc = ""
                update_time = ""
                
            return {
                "status": status,
                "description": desc,
                "update_time": update_time
            }
    except Exception as e:
        logger.error(f"Error parsing route detail for {detail_path}: {e}", exc_info=True)
        
    return {"status": "未知", "description": "解析詳細資訊時出錯。", "update_time": ""}

def get_route_search(from_station: str, to_station: str, date: Optional[str] = None, time: Optional[str] = None) -> Dict[str, Any]:
    """Scrape route search options between two stations from Yahoo Transit."""
    import urllib.parse
    import json
    
    # 1st attempt: disable airplane (al) and ferry (sr)
    params = {
        "from": from_station,
        "to": to_station,
        "shin": "1", # 新幹線
        "ex": "1",  # 有料特急
        "al": "0",  # 空路 (飛機) - 預設不搭乘
        "hb": "1",  # 高速巴士
        "lb": "1",  # 路線巴士
        "sr": "0",  # 渡輪 - 預設不搭乘
        "s": "2",   # 排序：轉乘次數最少優先 (乗換回数の少ない順)
    }
    
    # Parse date and time if provided
    if date or time:
        from datetime import datetime
        now = datetime.now()
        
        target_year = str(now.year)
        target_month = f"{now.month:02d}"
        target_day = f"{now.day:02d}"
        target_hour = f"{now.hour:02d}"
        target_minute = f"{now.minute:02d}"
        
        if date:
            # Try parsing YYYY-MM-DD, YYYY/MM/DD, YYYYMMDD
            date_clean = re.sub(r'[-/]', '', date.strip())
            if len(date_clean) == 8:
                target_year = date_clean[:4]
                target_month = date_clean[4:6]
                target_day = date_clean[6:8]
            elif len(date_clean) == 4:
                # MMDD format, use current year
                target_month = date_clean[:2]
                target_day = date_clean[2:4]
                
        if time:
            # Try parsing HH:MM, HHMM
            time_clean = re.sub(r'[:]', '', time.strip())
            if len(time_clean) == 4:
                target_hour = time_clean[:2]
                target_minute = time_clean[2:4]
                
        m_val = int(target_minute)
        m1_val = str(m_val // 10)
        m2_val = str(m_val % 10)
        
        params.update({
            "y": target_year,
            "m": target_month,
            "d": target_day,
            "hh": target_hour,
            "m1": m1_val,
            "m2": m2_val,
            "type": "1" # 出發時間指定
        })
    
    def perform_search(search_params):
        url = f"{BASE_URL}/search/result?{urllib.parse.urlencode(search_params)}"
        html = fetch_html(url)
        if not html:
            return {"errors": ["無法取得網頁資料，請檢查網路連線。"], "routes": []}
            
        try:
            soup = BeautifulSoup(html, "html.parser")
            
            # Check if Next.js data contains errors
            next_data_script = soup.find("script", id="__NEXT_DATA__")
            if next_data_script:
                try:
                    data = json.loads(next_data_script.string)
                    page_props = data.get("props", {}).get("pageProps", {})
                    error_list = page_props.get("queryState", {}).get("errorList")
                    if error_list:
                        return {
                            "errors": [str(e) for e in error_list],
                            "routes": []
                        }
                except Exception as e:
                    logger.warning(f"Error parsing Next.js query state errors: {e}")
                    
            # Find all route options
            route_divs = soup.find_all("div", id=lambda x: x and x.startswith("route"))
            if not route_divs:
                return {"errors": ["経路検索ができませんでした。"], "routes": []}
                
            routes = []
            
            for route_div in route_divs:
                # Summary details
                title = ""
                title_el = route_div.find("h2", class_="title")
                if title_el:
                    title = re.sub(r'\s+', ' ', title_el.text).strip()
                    
                priorities = []
                priority_ul = route_div.find("ul", class_="priority")
                if priority_ul:
                    priorities = [li.text.strip() for li in priority_ul.find_all("li") if li.text.strip()]
                    
                summary_ul = route_div.find("ul", class_="summary")
                time_info = ""
                transfer_info = ""
                fare_info = ""
                distance_info = ""
                
                if summary_ul:
                    time_li = summary_ul.find("li", class_="time")
                    if time_li:
                        time_info = re.sub(r'\s+', ' ', time_li.text).strip()
                        
                    transfer_li = summary_ul.find("li", class_="transfer")
                    if transfer_li:
                        transfer_info = re.sub(r'\s+', ' ', transfer_li.text).strip()
                        
                    fare_li = summary_ul.find("li", class_="fare")
                    if fare_li:
                        fare_info = re.sub(r'\s+', ' ', fare_li.text).strip()
                        
                    distance_li = summary_ul.find("li", class_="distance")
                    if distance_li:
                        distance_info = re.sub(r'\s+', ' ', distance_li.text).strip()
                        
                segments = []
                route_detail = route_div.find("div", class_="routeDetail")
                
                def parse_elements(elements):
                    for el in elements:
                        classes = el.get("class", []) if el.name == "div" else []
                        if "station" in classes:
                            time_ul = el.find("ul", class_="time")
                            time_val = " ".join([li.text.strip() for li in time_ul.find_all("li")]) if time_ul else ""
                            
                            icon_p = el.find("p", class_="icon")
                            status_val = icon_p.text.strip() if icon_p else ""
                            
                            dt = el.find("dt")
                            name_val = dt.text.strip() if dt else ""
                            name_val = re.sub(r'\s+', ' ', name_val).strip()
                            
                            segments.append({
                                "type": "station",
                                "name": name_val,
                                "time": time_val,
                                "status": status_val
                            })
                            
                        elif "fareSection" in classes:
                            transport_el = el.find(class_="transport")
                            transport_name = ""
                            destination = ""
                            
                            if transport_el:
                                dest_el = transport_el.find("span", class_="destination")
                                if dest_el:
                                    destination = dest_el.text.strip()
                                    transport_name = transport_el.text.strip().replace(dest_el.text.strip(), "")
                                else:
                                    transport_name = transport_el.text.strip()
                                transport_name = re.sub(r'\s+', ' ', transport_name).strip()
                                
                            status_val = "平常運転"
                            detail_url = None
                            status_el = el.find("li", class_="serviceStatus")
                            if status_el:
                                a_el = status_el.find("a")
                                if a_el:
                                    status_val = a_el.text.strip()
                                    detail_url = a_el.get("href")
                                    
                            # Parse intermediate stops if present
                            stop_el = el.find("li", class_="stop")
                            stops = []
                            if stop_el:
                                ul_stop = stop_el.find("ul")
                                if ul_stop:
                                    for li in ul_stop.find_all("li"):
                                        dt_stop = li.find("dt")
                                        dd_stop = li.find("dd")
                                        if dt_stop and dd_stop:
                                            stops.append({
                                                "name": dd_stop.text.strip(),
                                                "time": dt_stop.text.strip()
                                            })
                                            
                            segments.append({
                                "type": "transport",
                                "name": transport_name,
                                "destination": destination,
                                "status": status_val,
                                "detail_url": detail_url,
                                "stops": stops
                            })
                            
                            # Recursively parse nested divs inside the fareSection
                            nested_children = el.find_all("div", recursive=False)
                            parse_elements(nested_children)
                
                if route_detail:
                    parse_elements(route_detail.find_all("div", recursive=False))
                            
                routes.append({
                    "title": title,
                    "priorities": priorities,
                    "time": time_info,
                    "transfer": transfer_info,
                    "fare": fare_info,
                    "distance": distance_info,
                    "segments": segments
                })
                
            # Sort routes by number of transport segments (fewer transfers first)
            routes.sort(key=lambda r: sum(1 for s in r["segments"] if s["type"] == "transport"))
            return {"errors": [], "routes": routes}
        except Exception as e:
            logger.error(f"Error parsing route search from {from_station} to {to_station}: {e}", exc_info=True)
            return {"errors": ["解析路網查詢資料時發生錯誤。"], "routes": []}

    # First attempt: without airplanes & ferries
    result = perform_search(params)
    
    # If first attempt has errors or no routes, retry with them enabled
    if result.get("errors") or not result.get("routes"):
        params["al"] = "1"
        params["sr"] = "1"
        fallback_result = perform_search(params)
        if fallback_result.get("routes"):
            return fallback_result
            
    return result

