# Google Places CLI 實作計畫與技術細節 (places CLI)

本文件紀錄了 Google Places CLI (`places`) 的設計目標、技術架構、實作細節與測試驗證結果。此 CLI 旨在為使用者提供全球範疇的觀光景點與美食搜尋工具，並針對行動終端機（如手機 SSH、Telegram Bot）進行排版與功能最佳化。

---

## 📌 設計目標與功能
1. **輸入位置解析**：支援輸入多種格式的 GPS 座標資訊，包含：
   - 十進位經緯度數值（如 `"25.0339, 121.5644"`）。
   - 度分秒 DMS 格式（如 `"北緯25°5′0″ 東經121°34′43″"`）。
   - Google 地圖連結（包括手機分享之 `maps.app.goo.gl` 短網址與 `@lat,lon` 格式）。
   - 排除 Apple Maps 連結（`apple.com` 或 `apple.co`）。
2. **全球經緯度自動修正**：
   - 實作智慧型通用經緯度順序檢查。當使用者輸入的經度與緯度順序相反時（例如第一位數值超出 `[-90, 90]` 範圍但符合 `[-180, 180]`，且第二位數值符合 `[-90, 90]` 緯度範圍），系統會自動進行互換修正（例如將美國舊金山 `"-122.4194, 37.7749"` 修正為 `"37.7749, -122.4194"`）。
3. **半徑 500m 範圍查詢**：預設查詢輸入座標 500 公尺內（半徑可透過 `--radius` 自訂）的地點。
4. **景點與美食交叉檢索**：
   - 當使用者未指定類型時，系統會同時向 Google Places API 查詢 `restaurant`（餐廳）與 `tourist_attraction`（景點），將兩者結果進行合併、以 `place_id` 進行去重，並依照距離排序顯示。
   - 支援 `--type` 參數進行精確篩選（如輸入「餐廳」、「景點」、「咖啡廳」或「bar」等，將對應至 Google 的 place types，未知類型將直接透傳至 API）。
5. **多國語言支援**：
   - 支援 `--lang` 參數（預設 `zh-TW`），允許使用者指定 Google API 回傳之語言（如傳入 `ja` 以日文查詢東京的地點名稱與地址）。
6. **行動端排版最佳化**：
   - 強制以 38 欄寬進行排版，避免邊框錯位。
   - 地點名稱採用 `rich` 的終端機超連結功能（連結至 Google Maps 對應之地點網頁），並在下方印出純文字 URL，提升在重導向擷取環境（如 Telegram 機器人）的相容性。

---

## 🛠️ 技術架構與模組劃分

### 1. 資料對接與 GPS 解析 ([api.py](../src/places/api.py))
- **Google Places API (Legacy Nearby Search)**：
  - 串接 `https://maps.googleapis.com/maps/api/place/nearbysearch/json` 端點。
  - 對結果狀態（如 `OK`, `ZERO_RESULTS`, `REQUEST_DENIED`, `OVER_QUERY_LIMIT`）進行完整異常處理與中文防錯訊息提示。
- **通用 GPS 文本解析 (`parse_gps_input`)**：
  1. **Apple 地圖過濾**：排他性排除 Apple Maps 連結。
  2. **短網址還原**：對 `maps.app.goo.gl` 進行跳轉解析。
  3. **座標提取與自動校正**：從 URL 或純文字提取數值，並套用全球通用 Lat/Lon 互換修正。

### 2. CLI 控制器與視覺呈現 ([cli.py](../src/places/cli.py))
- **Click 整合**：
  - `places nearby [LOCATION]`：支援位置參數或 `--lat`/`--lon` 選項。
  - 選項參數包含：`--radius` (預設 500), `--type` 與 `--lang` (預設 zh-TW)。
- **距離排序**：
  - 使用 Haversine 公式計算使用者座標與地點實際經緯度之間的距離。
  - 依照距離由近到遠排序，且僅展示半徑範圍內的前 10 筆地點。
- **豐富終端機視覺**：
  - 展示地點星級評分與評論總數（如 `⭐ 4.5 (13648 則評論)`）。
  - 將 Google API 回傳之營業狀態（`opening_hours.open_now`）轉換為中文標示：`🟢 營業中`、`🔴 已打烊`、`⚪ 營業時間未知`。
  - 將景點類型對應並轉譯為易讀的中文標籤（例如 `restaurant` 顯示為「餐廳」）。

---

## 🧪 測試驗證

### 單元測試 ([test_places.py](../tests/test_places.py))
已針對 `places` 套件編寫 `pytest` 單元測試：
1. **距離計算**：驗證 Haversine 計算距離是否正確。
2. **座標解析與修正**：
   - 驗證標準十進位輸入與台灣區域經緯度互換。
   - 驗證全球通用經緯度互換（例如 San Francisco 的 `-122.4194, 37.7749` 自動換位）。
   - 驗證 Google Maps URL 各式座標格式擷取與短網址 Mock 跳轉。
   - 驗證 DMS 座標解析與互換。
3. **Google API 對接與 Mocking**：
   - 模擬 Places API 成功（`OK`）的回傳與錯誤拒絕處理（`REQUEST_DENIED`）。
   - 驗證未指定類型時，餐廳與景點聯合查詢的合併去重邏輯。

測試執行指令：
```bash
uv run python -m pytest tests/test_places.py
```

---

## 📂 檔案異動清單
- **[pyproject.toml](../pyproject.toml)**：註冊 CLI 入口 `places = "places.cli:cli"`。
- **[src/places/__init__.py](../src/places/__init__.py)**：封包初始化。
- **[src/places/api.py](../src/places/api.py)**：Places API 串接與 GPS 解析。
- **[src/places/cli.py](../src/places/cli.py)**：CLI 使用介面。
- **[tests/test_places.py](../tests/test_places.py)**：單元測試。
- **[docs/places_implementation.md](file:///Users/tedyeng/VSCodeProjects/hermes-go/docs/places_implementation.md)**: 本實作計畫書。
