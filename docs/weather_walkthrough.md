# CWA Weather CLI Real-Time Rain & Forecast Walkthrough

We have successfully added the real-time rainfall query command (`tw-weather rain`) to help users monitor actual local rainfall accumulation, view current rain intensity classifications, and inspect future precipitation forecasts.

## Changes Made

1. **Rain API Integration (`fetch_cwa_rain_data`)**:
   - Integrated with CWA Open Data live rain observations `O-A0002-001` in [api.py](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/tw_weather/api.py).
   - Designed value converters (`format_rain_value`, `display_rain_value`) to handle CWA custom codes like `-99` (missing), `-98` (dry), and `T` (trace rain).

2. **Haversine Distance Matching**:
   - Implemented `calculate_distance` using the Haversine formula.
   - Added `find_nearest_rain_station` which maps target input (address/GPS coordinates) onto active CWA rain stations and picks the closest station.

3. **Disaster Prevention Classification (`get_rain_alert_level`)**:
   - Implemented CWA's official warning levels based on accumulated rain:
     - **大雨 (Heavy Rain)**: 24H >= 80mm OR 1H >= 40mm
     - **豪雨 (Extremely Heavy)**: 24H >= 200mm OR 3H >= 100mm
     - **大豪雨 (Torrential)**: 24H >= 350mm OR 3H >= 200mm
     - **超大豪雨 (Extremely Torrential)**: 24H >= 500mm
   - Evaluates warning levels and triggers prominent warnings on the terminal.

4. **Rain Intensity Classification (`get_rain_intensity_label`)**:
   - Formatted rain rate ranges into user-friendly physical tags:
     - $0.1 \le \text{rate} \le 2.0\text{ mm/hr}$: `毛毛雨，可不撐傘`
     - $2.0 < \text{rate} \le 10.0\text{ mm/hr}$: `小雨，出門記得帶傘`
     - $10.0 < \text{rate} \le 30.0\text{ mm/hr}$: `大雨，開車騎車請減速`
     - $> 30.0\text{ mm/hr}$: `豪雨或雷雨，注意低窪地區積水`
     - Otherwise: `目前無顯著降雨`

5. **Future Rain Outlook Integration**:
   - Fetches county-specific weather forecasts (`F-D0047-XXX`) inside the `rain` command.
   - Displays the **未來兩日降雨預估** covering the next 2 days in 12-hour intervals showing weather conditions (`wx_summary`), precipitation probability (`pop`), and tailored emoji indicators.
   - Constrained to prevent column wrapping within a 38-character wide viewport.

6. **Hourly Forecast Expansion (`--all-hours` option)**:
   - Added the `--all-hours` click option to the `hourly` command to bypass the default limit (showing only today's remaining hours or next 24 hours) and display the full 48-hour hourly sequence.

7. **Future Rain Volume Estimation**:
   - Implemented `get_rain_volume_estimate` which analyzes the weather phenomenon keywords (`Wx`) and precipitation probability (`PoP`) to generate a reliable expected rain volume range (in mm), helping users gauge rain intensity.

---

## Verification Results

### Unit Tests
New unit tests in [test_tw_weather.py](file:///Users/tedyeng/VSCodeProjects/hermes-go/tests/test_tw_weather.py) cover:
- Rainfall formatting and anomaly cleansers.
- Alert level evaluations.
- Closest station calculations.
- Rain intensity label classifications (`test_get_rain_intensity_label`).
- Future rain volume estimations (`test_get_rain_volume_estimate`).

Run test suite:
```bash
.venv/bin/python -m pytest
```
Output:
```
============================== 42 passed in 5.77s ==============================
```

### Manual Verification
1. **Running `tw-weather rain` (Taipei default)**:
   ```bash
   .venv/bin/tw-weather rain
   ```
   Output:
   ```
   📍 降雨觀測定位
   • 縣市: 臺北市
   • 鄉鎮區: 信義區
   • 座標: (25.0333, 121.5669)
   ────────────────────────────────────
   ⚡ 讀取本地快取雨量資料...
   
   📡 觀測站資訊
   • 站名: 信義 (C0AC70)
   • 距離: 0.55 km
   • 觀測時間: 2026-06-27T11:20:00+08:00
   ────────────────────────────────────
   
   💧 累積降雨量數據
   • 10分鐘累積:  0.0 mm
   • 過去1小時:   0.5 mm
   • 過去3小時:   1.0 mm
   • 過去24小時:  21.5 mm
   • 今日日累積:  5.5 mm
   • 即時雨勢:    毛毛雨，可不撐傘
   ────────────────────────────────────
   
   ⚠️ 防災警戒分級
   🟢 一般 (Normal)
   ────────────────────────────────────
   
   🔮 未來兩日降雨預估
   • 06/27 (六) 白天
     預報: 短暫陣雨或雷 | 降雨: 70% ☔🔴
   • 06/27 (六) 晚上
     預報: 短暫陣雨或雷 | 降雨: 60% ☔
   • 06/28 (日) 白天
     預報: 短暫陣雨或雷 | 降雨: 50% ☔
   • 06/28 (日) 晚上
     預報: 短暫陣雨或雷 | 降雨: 30% ☔
   ────────────────────────────────────
   ```

## Web Dashboard Integration (FastAPI Backend + React Frontend)

We exposed the Taiwan weather analytics engine to the web dashboard:

### 1. Backend FastAPI Endpoints (`src/server.py`)
- **`/api/weather/check`**: Resolves county and district coordinates, then queries the 3-day weather forecasts (`F-D0047-XXX` or fallback `F-C0032-001`).
- **`/api/weather/hourly`**: Retrieves 48h hourly forecasts using the 2-day 3-hourly forecast dataset, fetching temperature, apparent temperature, relative humidity, wind speed/direction, and comfort indices.
- **`/api/weather/rain`**: Fetches live rainfall data from all CWA stations (`O-A0002-001`), geocodes nearest station distance/coordinates, computes alert levels, and appends future precipitation probability and volume estimates.

### 2. Frontend React Dashboard (`frontend/src/`)
- **`App.tsx`**: Registered `weather` mode, and connected coordinate changes to automatic API queries. Passes coordinates (`lat`, `lon`) and weather parameters to `Sidebar` and `MapContainer`.
- **`Sidebar.tsx`**: Constructed a gorgeous weather panel featuring three tabs matching the CLI functions:
  - **雨量與預期 (Rain & Outlook)**: Shows the closest rain station, live 10m/1h/3h/24h/today accumulations, rain intensity label, alert level, and a 2-day expected rain volume checklist.
  - **三日天氣預報 (3-Day Forecast)**: Shows weather state, high/low temp ranges, precipitation probabilities, comfort text, and smart umbrella tips (e.g. `需帶直傘`, `需帶折疊傘`).
  - **逐小時天氣 (Hourly Forecast)**: Lists hourly sequences with a toggle between today/24h and full 48h. Warns with red border and badges for high rain probabilities and strong winds.
- **`MapContainer.tsx`**: Added support for cyan Leaflet map markers, placing pins on the nearest rain station or town center coordinate for visual positioning.

### 3. Verification Results
Both TypeScript type-checking and Vite bundling completed successfully with zero issues.
Endpoints were verified by local curl query calls:
- **Rain API**:
  ```bash
  curl -s "http://localhost:8000/api/weather/rain?location=%E8%87%BA%E5%8C%97%E5%B8%82%E4%BF%A1%E7%BE%A9%E5%8D%80"
  ```
  Returns full geolocated station, observations, alert level, and 2-day outlook volume estimates.
- **Check API**:
  ```bash
  curl -s "http://localhost:8000/api/weather/check?location=%E8%87%BA%E5%8C%97%E5%B8%82%E4%BF%A1%E7%BE%A9%E5%8D%80"
  ```
  Returns 3-day weather periods, temp ranges, rain chance, and umbrella advice.
- **Hourly API**:
  ```bash
  curl -s "http://localhost:8000/api/weather/hourly?location=%E8%87%BA%E5%8C%97%E5%B8%82%E4%BF%A1%E7%BE%A9%E5%8D%80"
  ```
  Returns aligned hourly weather data including temperature, apparent temp, RH, and wind attributes.

---

## CLI Help Text Enhancement

Updated all `tw-weather` CLI `--help` docstrings in [cli.py](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/tw_weather/cli.py) with:

1. **Main Group (`tw-weather --help`)**: Comprehensive overview listing all 6 subcommands with one-line descriptions and example commands, properly formatted with Click `\b` markers to prevent text reflow.

2. **Subcommand Help** (`check`, `summary`, `board`, `hourly`, `rain`, `clean`):
   - Each subcommand now includes a detailed Chinese description of its functionality.
   - Lists supported input formats (location names, lat/lon coordinates).
   - Explains output features (alert levels, rain intensity labels, wind speed warnings).
   - Provides concrete `$ tw-weather <cmd>` usage examples.

3. **Click Formatting**: Used `\b` paragraph markers throughout to ensure multi-line help text preserves line breaks in terminal output instead of being reflowed by Click's default text wrapper.

---

## 定量降雨估算 (QPF Rainfall Volume Estimation)

於 `tw-weather rain` 指令與 `/api/weather/rain` 後端 API 串接定量降水預估功能：

1. **研究限制**：經分析中央氣象署常態性定量降水預報 API（F-C0035 系列）回傳的是**預報圖像**而非結構化 JSON 資料；格點預報資料（F-C0041）則僅在颱風陸警期間開放。因此本專案採用**啟發式定量降水估算模型**。
2. **多維度推估模型**：
   - 串接 `F-D0047` 鄉鎮天氣預報資料集之 `PoP3h` (3小時降雨機率) 與 `Wx` 中的 `WeatherCode` (天氣現象代碼)。
   - 根據代碼與文字區分降雨強度等級（無/微量/小雨/中雨/大雨/豪雨等級），乘以降雨機率比重。
   - 分段計算 3 小時累積，最後加總成 12 小時預報區間之累積雨量範圍（例如 `16.0 ~ 50.0 mm`）。
3. **無縫整合 Dashboard UI**：後端 `/api/weather/rain` 回傳之 `est_volume` 自動套用新的 mm 預估區間，前端網頁儀表板不需修改代碼即可自動更新顯示新版的雨量估算。

