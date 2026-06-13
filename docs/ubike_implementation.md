# YouBike CLI 實作計畫與技術細節

本文件紀錄了 YouBike CLI (`ubike`) 的設計目標、技術架構、實作細節與測試驗證結果。此 CLI 參照 `twbus` 架構開發，旨在提供行動終端機（如手機 SSH、Telegram Bot）最佳化的即時車況查詢工具。

---

## 📌 設計目標與功能
1. **輸入位置解析**：支援輸入多種格式的 GPS 座標資訊，包含：
   - 經緯度數值（如 `"25.02605, 121.5436"`），若順序相反會自動修正。
   - 度分秒 DMS 格式（如 `"北緯25°01'33.8\" 東經121°32'37.0\""`）。
   - Google 地圖連結（包括手機分享之 `maps.app.goo.gl` 短網址與 `@lat,lon` 格式）。
   - 依據需求，**排除 (忽略)** Apple Maps 連結（`apple.com` 或 `apple.co`）。
2. **200m 範圍查詢**：查詢輸入座標 200 公尺內（半徑可自訂）的 YouBike 站點。
3. **即時車況資訊**：顯示站點中文名稱、營運狀態、可借車輛數、空位歸還數、以及來源平台最後更新時間。
4. **Google Maps 導航連結**：自動產生 Google Maps 連結，除利用 `rich` 的終端機超連結功能包裝站點名稱外，亦直接印出純文字 URL，以解決在非 TTY 終端（如 Telegram / Agent 等重新導向環境）中超連結資訊會被 `rich` 過濾的問題。
5. **行動最佳化版面**：強制 38 欄寬排版，避免在小螢幕上因折行造成邊框錯位。

---

## 🛠️ 技術架構與模組劃分

### 1. 本地快取模組 ([cache.py](../src/ubike/cache.py))
- **SQLitePersistentCache**：在使用者快取目錄下建立獨立的 `ubike/cache.db`。
- **Token 暫存**：用於快取 TDX Access Token，以減少向 TDX 伺服器頻繁申請 Token 的次數。

### 2. 資料對接與 GPS 解析 ([api.py](../src/ubike/api.py))
- **TDX OIDC 認證**：對接 TDX Client Credentials 認證機制，動態取得認證權杖。
- **TDX 進階服務 (NearBy)**：
  - `/v2/Bike/Station/NearBy`：取得半徑範圍內所有站點的靜態資料。
  - `/v2/Bike/Availability/NearBy`：取得半徑範圍內所有站點的即時車位狀態。
  - 均使用 OData `$spatialFilter=nearby({lat}, {lon}, {radius})` 語法進行空間過濾。
- **智慧 GPS 文本解析 (`parse_gps_input`)**：
  1. **Apple Maps 過濾**：若輸入中含有 `apple.com` 或 `apple.co`，立即返回 `None`。
  2. **短網址還原**：對 `maps.app.goo.gl` 發送 `requests.head` 獲取重定向後的最終 Google Maps URL。
  3. **網址參數提取**：解析 URL Path（如 `/@lat,lon`）與 Query Params（如 `?q=lat,lon`）來擷取經緯度。
  4. **正則表達式提取**：於純文本中匹配經緯度數值對，並在必要時依據台灣座標範圍自動校正緯度和經度順序。
  5. **DMS 格式解析**：呼叫 `twbus` 的 DMS 解析器。

### 3. CLI 控制器與視覺呈現 ([cli.py](../src/ubike/cli.py))
- **Click 整合**：
  - `ubike nearby [LOCATION]`：支援位置參數或 `--lat`/`--lon` 選項。
  - `ubike clean`：手動清除本地 SQLite 快取的 Token 資料庫。
- **距離排序**：使用 Haversine 公式計算使用者與站點的步行距離，並進行升序排列（由近到遠）。
- **豐富終端機視覺**：
  - 狀態燈號提示：🟢 正常營運、🟡 暫停營運、🔴 停止營運。
  - 可借車輛與空位使用高亮色彩標註。
  - 將站點名稱清理（移除冗餘的 `YouBike2.0_` 或 `YouBike1.0_` 前綴）。
  - 將站點名稱包裝為 `[link=GMAP_URL]站點名稱[/link]` 行動超連結，並提供獨立的 `• 地圖: {gmaps_url}` 文字 URL 輸出，以相容各類重導向擷取環境。

---

## 🧪 測試驗證

### 單元測試 ([test_ubike.py](../tests/test_ubike.py))
已針對以下功能編寫 `pytest` 單元測試：
1. `test_parse_gps_input_raw_decimals`：驗證標準十進位與反向經緯度修正。
2. `test_parse_gps_input_urls`：驗證 Google Maps 各種格式的連結座標提取。
3. `test_parse_gps_input_short_url`：Mock 還原並解析縮網址連結。
4. `test_parse_gps_input_dms`：驗證 DMS 座標解析。
5. `test_calculate_distance`：驗證 Haversine 計算距離。
6. `test_get_nearby_stations` 與 `test_get_nearby_availability`：Mock TDX API 的回傳並驗證 spatialFilter 參數拼接。

測試執行指令：
```bash
uv run python -m pytest tests/test_ubike.py
```

---

## 📂 檔案異動清單
- **[pyproject.toml](../pyproject.toml)**：新增 CLI 入口 `ubike = "ubike.cli:cli"`。
- **[src/ubike/__init__.py](../src/ubike/__init__.py)**：封包初始化。
- **[src/ubike/cache.py](../src/ubike/cache.py)**：隔離 SQLite 快取。
- **[src/ubike/api.py](../src/ubike/api.py)**：TDX 串接與 GPS 解析。
- **[src/ubike/cli.py](../src/ubike/cli.py)**：CLI 使用介面。
- **[tests/test_ubike.py](../tests/test_ubike.py)**：單元測試。
- **[README.md](../README.md)**：更新說明文件。
- **[CHANGELOG.md](../CHANGELOG.md)**：新增更新日誌。
