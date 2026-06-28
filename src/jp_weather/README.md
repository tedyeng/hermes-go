# jp-weather 🇯🇵 (日本與全球氣象天氣查詢 CLI 工具)

一個精美、高效能的終端機 CLI 工具，用於查詢日本及全球當前天氣與一週天氣預報。基於 SQLite 本地快取優化，優先深度整合日本氣象廳 (JMA) 高解析度氣象預報模型，並無縫支援全球地標、郵遞區號及 GPS 座標直查。

---

## 🌟 核心特色

* **🇯🇵 日本氣象廳高解析度預報**：整合 Open-Meteo 天氣預報服務，優先調用針對東亞地區優化的日本氣象廳高解析度氣象模型數據 (JMA MSM/GSM)。
* **🌍 全球無縫覆蓋與日本優先匹配**：除專為日本地名行政尾綴優化外，亦完美支援全球任意地點的氣象直查。當查詢國際地點時，會自動切換至歐洲 ECMWF / 美國 GFS 等全球頂級氣象模型；當查詢具備多國重名時（如 `Fuji`），系統會智慧優先匹配日本（`JP`）境內的地點。
* **🔍 智慧 CJK 地名與行政尾綴匹配**：針對日文或中文的地名查詢，程式會自動處理與補全常見的日本行政區劃尾綴（如 `市`、`都`、`府`、`縣` 等）進行智慧檢索，並支持中日英文及日本郵遞區號（如 `100-0001`）查詢，保證檢索最大精準度。
* **🌐 GPS 十進位與 DMS 度分秒座標直查**：支援直接輸入 GPS 十進位座標（如 `35.6895, 139.6917` 等）或 **DMS 度分秒分標格式**（如 `北緯25°5′0″ 東經121°34′43″`、`N 35° 41' 22" E 139° 41' 30"` 等格式）。系統會自動智慧解析並調用 **OSM Reverse Geocoding API** 精確反向定標，呈現當地天氣。
* **🗺️ 景點與自然地標雙引擎定位 (OSM Fallback)**：當行政區地名搜尋無結果時，會自動無縫切換至 **OpenStreetMap Nominatim API** 進行二次檢索。完美支持日本與全球自然景區、山谷、名勝景點（如 `上高地`、`富士山` 等）的精確經緯度定位。
* 🎨 精美終端機視覺 UI：使用 `rich` 套件渲染精美的即時天氣狀態卡片（包含天氣圖示、體感溫度、風速風向箭頭與降雨量），並提供排列整齊、高度對齊的 **一週天氣預報表格**。
* 🕒 即時天氣附帶每 3 小時氣象走勢：在查詢即時天氣時，系統會自動在下方渲染未來 24 小時的 **每 3 小時預報走勢圖表**（含氣溫、降雨機率、天氣圖示），讓近期天氣趨勢一目了然。
* 📸 黃金時刻與藍調時刻 (Golden & Blue Hour)：提供攝影愛好者專屬的晨昏黃金與藍調光影起訖時段計算。整合 Open-Meteo 當天與一週預報（氣溫、降雨、雲量），智慧評估 1 至 5 星級的「攝影指數」與拍照實況建議，並支援高緯度地區「極晝/極夜」之智慧警示排版。
* ⚡ 本地 SQLite 持久化快取：自動將地點檢索結果快取 **24 小時**，天氣預報數據快取 **15 分鐘**。基於 SQLite 實現，兼顧即時極速響應並節制外部 API 請求次數。
* 📱 手機最佳化排版 (iPhone 16 Pro)：提供專用 `--mobile` 旗標，開啟 38 欄寬度超緊湊的直式排版。消除 CJK 全寬字元在手機 SSH 或終端機模擬器 (如 Termius、a-Shell) 上的折行與框線錯位，並貼心只顯示精簡中文天氣描述以防超出螢幕邊界。
* 🤖 互動式引導模式：在不加任何參數的情況下執行工具，即可開啟精美的互動式導覽選單（支援方向鍵選擇地點與要查詢的天氣類型，且同樣支援 `--mobile` 模式）。


---

## 🚀 安裝與設定

此專案已作為子模組整合至 `hermes-go` 中。請於 `hermes-go` 專案根目錄下執行：

1. 安裝或更新專案依賴與 entrypoint：
   ```bash
   uv pip install -e .
   ```

---

## 💻 使用方法

### 1. 互動式引導模式（預設）
直接執行 CLI，不加任何子指令或參數：
```bash
uv run jp-weather
```
這將會開啟一個非常直觀的互動式導覽選單，可使用鍵盤上下方向鍵挑選。

### 2. 快速快捷指令
在終端機中一步到位直接獲取氣象結果。

* **查詢「即時天氣狀態」**：
  ```bash
  uv run jp-weather current "地名、地址、郵遞區號或 GPS 座標"
  ```
  *範例：*
  ```bash
  uv run jp-weather current "東京"
  uv run jp-weather current "Kyoto"
  uv run jp-weather current "100-0001"
  uv run jp-weather current "35.6895, 139.6917"          # GPS 十進位座標
  uv run jp-weather current "北緯25°5′0″ 東經121°34′43″"  # DMS 度分秒座標
  ```

* **查詢「一週天氣預報」**：
  ```bash
  uv run jp-weather forecast "地名、地址、郵遞區號或 GPS 座標"
  ```
  *範例：*
  ```bash
  uv run jp-weather forecast "大阪"
  uv run jp-weather forecast "35.6895, 139.6917"          # GPS 十進位座標
  uv run jp-weather forecast "北緯25°5′0″ 東經121°34′43″"  # DMS 度分秒座標
  ```

* **查詢「黃金時刻與藍調時刻」**（📸 攝影專屬）：
  ```bash
  uv run jp-weather golden "地名、地址、郵遞區號或 GPS 座標" [選項]
  ```
  *選項：*
  - `--week`：顯示未來一週的光影預報。
  - `--mobile`：使用手機最佳化 38 欄寬度直式排版。
  - `--no-interactive`：略過多重地點互動選擇，直接挑選首位匹配地點。
  *範例：*
  ```bash
  uv run jp-weather golden "東京"
  uv run jp-weather golden "京都" --week
  uv run jp-weather golden "富士山" --mobile
  uv run jp-weather golden "69.649,18.956" --no-interactive  # 查詢挪威極地 (支援極晝/極夜警示)
  ```

* **靜態非互動模式旗標 (`--no-interactive`)**：
  略過多重地點選擇，自動挑選關聯度最高的第一個匹配地點（非常適合編寫自動化 Shell 腳本）：
  ```bash
  uv run jp-weather current "東京" --no-interactive
  ```

* **手機閱讀模式旗標 (`--mobile`)**：
  在主指令或子指令中加入 `--mobile`，即可以 38 欄寬度完美緊湊排版呈現，特別適合 iPhone 16 Pro 等手機終端機 (Termius / a-Shell)：
  ```bash
  # 啟動手機版互動式引導模式
  uv run jp-weather --mobile
  
  # 查詢手機版即時天氣 (支援在主指令或子指令放置旗標)
  uv run jp-weather --mobile current "東京"
  uv run jp-weather current "東京" --mobile
  
  # 查詢手機版一週預報
  uv run jp-weather forecast "大阪" --mobile
  ```


### 3. 清除本地快取
手動清空 SQLite 快取資料庫中的歷史快取：
```bash
uv run jp-weather clean
```

---

## 🧪 單元測試

執行完善的 pytest 單元測試套件（共 29 案），驗證核心工具函式、API Mock 機制以及天文算法：
```bash
.venv/bin/pytest
```

## 📊 數據來源 (Data Sources)

本專案之天氣數據與地理定位資訊完全對接公開且免金鑰的高解析度數據源，並透過本地 SQLite 持久化快取進行查詢加速：

### 1. 天氣預報數據 (Weather Forecast)
對接 **[Open-Meteo Weather API](https://open-meteo.com/)**，優先深度整合以下數值天氣預報模型：
* **🇯🇵 日本與東亞地區**：優先調用 **日本氣象廳 (JMA, Japan Meteorological Agency)** 的 **MSM (5公里高解析度區域模型)** 與 **GSM (全球光譜模型)**，提供最具權威性與在地精準度的天氣與降雨指標。
* **🌍 全球無縫覆蓋**：對於日本以外的國際城市，自動切換調用 **歐洲中期天氣預報中心 (ECMWF)** 的 IFS 模型（9公里網格）與 **美國國家海洋暨大氣總署 (NOAA)** 的 **GFS** 預報模型。

### 2. 地理資訊與地名檢索 (Geocoding & Reverse Geocoding)
地名查詢與經緯度定位採用雙引擎無縫 fallback 架構：
* **主引擎：[Open-Meteo Geocoding Service](https://open-meteo.com/en/docs/geocoding-api)**（基於 GeoNames 數據庫），自動過濾並優先匹配日本（`JP`）境內的地點，支援日、中、英多語系。
* **副引擎與 GPS 反查：[OpenStreetMap (OSM) Nominatim Service](https://nominatim.org/)**，用於：
  * 自然地標、景區、名勝山谷（如 `富士山`、`上高地` 等）的備用高精度地理定位。
  * **GPS 座標逆向定標**：精確將 Decimal 十進位或 DMS 度分秒座標（如 `北緯25°5′0″ 東經121°34′43″`）反查為實際地標、行政區或路名名稱。

---

## 📂 專案目錄結構

* `src/jp_weather/`：主程式源碼目錄。
  * `api.py`：整合地名檢索 (Geocoding) 與天氣預報 API 的交互模組。
  * `suncalc.py`：純 Python 實現的太陽高度角與天文位置計算模組（計算日出、日落、黃金時刻、藍調時刻與極地判定）。
  * `cache.py`：管理 SQLite 本地持久化快取的邏輯模組。
  * `formatter.py`：處理終端機視覺美化渲染與 WMO 天氣代碼映射。
  * `cli.py`：指令控制器主入口與互動式導覽介面。
* `tests/`：單元測試腳本目錄（含 `test_jp_weather.py`、`test_golden.py`、`test_suncalc.py` 等）。
* `docs/`：專案說明文檔目錄。
  * [docs/jp_weather_walkthrough.md](../../docs/jp_weather_walkthrough.md)：完整的成果展示與終端機渲染範例說明。
  * [docs/jp_weather_implementation_plan.md](../../docs/jp_weather_implementation_plan.md)：初始系統設計決策與 API 評估方案。
  * [docs/jp_weather_task.md](../../docs/jp_weather_task.md)：專案開發里程碑與完成清單。
  * [docs/jp_weather_migration.md](../../docs/jp_weather_migration.md)：移轉至 Hermes Go 的技術變更與開發指引。
