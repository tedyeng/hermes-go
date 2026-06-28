# 🚄 Hermes Go (日本鐵道/氣象、台灣公車/YouBike/天氣 & 全球觀光美食即時資訊 CLI 與 Web 儀表板)

此專案是一個精美、高效能且針對行動裝置與網頁瀏覽器最佳化的交通、天氣與景點查詢工具箱。它包含了六個獨立的 Python 終端機 CLI 工具與一個整合式地圖 Web 儀表板：

1. **jptrain** 🚄：查詢日本鐵道、地鐵、新幹線的即時運行概況與延誤詳情，自動翻譯為繁體中文。
   - 👉 詳細說明與使用方法請見 [jptrain 說明文件](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/jptrain/README.md)。
2. **twbus** 🚌：提供離線/快取優化的台灣附近公車即時 ETA、特定路線到站時間與直達規劃。
   - 👉 詳細說明與使用方法請見 [twbus 說明文件](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/twbus/README.md)。
3. **ubike** 🚲：輸入 GPS 座標或 Google Maps 連結，查詢附近 YouBike 站點與即時可借車輛數。
   - 👉 詳細說明與使用方法請見 [ubike 說明文件](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/ubike/README.md)。
4. **places** 🗺️：利用 Google Places API 查詢全球任何地點的餐廳與景點，支援指定搜尋類型與回傳語言。
   - 👉 詳細說明與使用方法請見 [places 說明文件](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/places/README.md)。
5. **tw-weather** 🌦️：整合中央氣象署鄉鎮預報、今明 36 小時預報與即時雨量觀測 API，提供天氣、溫度、舒適度、降雨機率、風速警戒、風向、及精準的雨具攜帶建議。支援即時雨勢狀態標籤、未來降雨估算、逐小時預報與全台降雨看板。
   - 👉 詳細說明與使用方法請見 [tw-weather 說明文件](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/tw_weather/README.md)。
6. **jp-weather** 🌦️：日本氣象廳與全球氣象天氣查詢 CLI 工具，優先調用 JMA MSM/GSM 高解析度氣象模型，並支援 SQLite 本地快取、GPS/DMS 座標、郵遞區號直查與攝影黃金時刻（攝影星級指數評估）。
   - 👉 詳細說明與使用方法請見 [jp-weather 說明文件](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/jp_weather/README.md)。

---

## 🚀 安裝與設定

請確保您的系統已安裝 **Python 3.10+** 以及 [uv](https://github.com/astral-sh/uv) 套件管理器。

1. 切換至專案目錄：
   ```bash
   cd hermes-go
   ```
2. 以可編輯模式安裝此專案與其依賴套件：
   ```bash
   uv pip install -e .
   ```
3. 將專案根目錄的 `.env.example` 複製為 `.env`，並填入您的 API 憑證與金鑰：
   ```bash
   cp .env.example .env
   ```
   *編輯 `.env` 檔案並設定以下內容（依您欲使用的工具而定）：*
   - `TDX_CLIENT_ID` 與 `TDX_CLIENT_SECRET`（用於 `twbus` 與 `ubike`）
   - `GOOGLE_PLACES_API_KEY`（用於 `places`）
   - `CWA_API_KEY`（用於 `tw-weather`）

---

## 🖥️ Web Dashboard 網頁儀表板

除了 CLI 終端機工具外，此專案亦提供了一個精美的單頁網頁版（SPA）儀表板，將所有交通、景點與天氣查詢功能整合在 Leaflet 地圖上展示。

### 啟動網頁服務：
1. **編譯前端靜態資源**：
   請確保您的系統已安裝 [Node.js](https://nodejs.org/)。切換至 `frontend/` 目錄並執行編譯：
   ```bash
   cd frontend
   npm install
   npm run build
   cd ..
   ```
2. **啟動 Python FastAPI 後端伺服器**：
   ```bash
   uv run python src/server.py
   ```
3. 在瀏覽器中開啟 [http://localhost:8000](http://localhost:8000) 即可使用完整的地圖與側邊欄儀表板。

---

## 🧪 單元測試

本專案使用 `pytest` 進行單元測試。

* **執行所有單元測試**：
  ```bash
  uv run python -m pytest
  ```
* **分模組執行測試**：
  ```bash
  # 日本鐵道測試
  PYTHONPATH=src uv run python -m pytest tests/test_api.py tests/test_cache.py
  # 台灣公車測試
  PYTHONPATH=src uv run python -m pytest tests/test_twbus.py
  # YouBike 測試
  PYTHONPATH=src uv run python -m pytest tests/test_ubike.py
  # Google Places 測試
  PYTHONPATH=src uv run python -m pytest tests/test_places.py
  # 台灣天氣測試
  PYTHONPATH=src uv run python -m pytest tests/test_tw_weather.py
  # 日本天氣測試
  PYTHONPATH=src uv run python -m pytest tests/test_jp_weather.py tests/test_golden.py tests/test_suncalc.py tests/test_weather_enhancements.py
  ```

---

## 📂 專案目錄結構

* `src/jptrain/`：日本鐵道即時查詢主程式源碼。
  * [README.md](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/jptrain/README.md)
* `src/twbus/`：台灣公車即時查詢主程式源碼。
  * [README.md](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/twbus/README.md)
* `src/ubike/`：台灣公共自行車即時車況主程式源碼。
  * [README.md](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/ubike/README.md)
* `src/places/`：全球觀光美食即時查詢主程式源碼。
  * [README.md](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/places/README.md)
* `src/tw_weather/`：台灣鄉鎮天氣預報與雨具建議主程式源碼。
  * [README.md](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/tw_weather/README.md)
* `src/jp_weather/`：日本與全球天氣/黃金時刻查詢主程式源碼。
  * [README.md](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/jp_weather/README.md)
* `tests/`：Pytest 單元測試腳本目錄。
  * `test_api.py` / `test_cache.py`：日本鐵道核心功能 Mock 測試。
  * `test_twbus.py`：台灣公車 Mock 測試與解析。
  * `test_ubike.py`：YouBike API 與 GPS 格式/連結解析。
  * `test_places.py`：Google Places API 與全球 GPS 格式/連結解析。
  * `test_tw_weather.py`：台灣天氣 API 與 GPS 格式/連結解析及雨具攜帶邏輯測試。
  * `test_jp_weather.py` / `test_golden.py` / `test_suncalc.py` / `test_weather_enhancements.py`：日本/全球天氣與攝影指數核心 Mock 測試。

