# places 🗺️ (全球觀光美食即時查詢 CLI)

`places` 利用 Google Places API 查詢全球任何地點半徑內的餐廳與景點，支援指定搜尋類型（如咖啡廳、酒吧等）與回傳語言（如日文、英文），具備全球 GPS 經緯度智慧自動互換修正。

本工具專為行動裝置終端機最佳化，**預設採用 38 欄寬度的直式排版**，支援全球範圍的地點搜尋，特別適合在手機（如 Termius）或 Telegram 中使用。

## 🔧 設定與前置步驟
在使用 `places` 之前，請在您的 `.env` 檔案中設定 Google Places API 金鑰：
```env
GOOGLE_PLACES_API_KEY=您的_google_places_api_key
```

---

## 💻 使用方法

### 1. 查詢附近觀光美食即時狀態 (預設)
直接傳入您複製的 GPS 座標、度分秒 DMS、或地圖連結，預設會查詢該位置半徑 500m 內的**餐廳與景點**（自動合併、去重，並排序）：
```bash
# 輸入經緯度數值 (緯度, 經度)
uv run places nearby "25.0339, 121.5644"

# 輸入度分秒 DMS 格式
uv run places nearby "北緯25°5′0″ 東經121°34′43″"

# 輸入 Google Maps 連結
uv run places nearby "https://maps.app.goo.gl/xxxxxx"
```
*如果沒有指定 `--type`，工具會同時向 Google API 查詢餐廳與景點，並合併去重後排序輸出。*

### 2. 智慧型全球經緯度自動修正
如果輸入的經緯度順序相反（例如將經度寫在前面），工具會偵測並自動校正。這在全球範圍皆有效：只要第一位數值超出 `[-90, 90]` 緯度範圍，但第二位數值符合 `[-90, 90]`，系統即會將其視為經度與緯度寫反而自動進行互換。
```bash
# 舊金山正確座標為 37.7749, -122.4194。若輸入反向座標，工具將自動換位查詢：
uv run places nearby "-122.4194, 37.7749"
```

### 3. 進階選項與參數

* **指定搜尋半徑 (`--radius`)**：
  設定搜尋範圍（公尺），預設為 500 公尺。
  ```bash
  uv run places nearby "25.0339, 121.5644" --radius 200
  ```

* **篩選特定類型 (`--type`)**：
  內建常見中文關鍵字對應表，會自動轉換為 Google Places API 對應的類型進行搜尋。未給予時會預設搜尋餐廳及景點。
  ```bash
  uv run places nearby "25.0339, 121.5644" --type 咖啡廳
  ```
  *內建中文關鍵字對照：*
  - 餐廳 / 美食 -> `restaurant`
  - 景點 / 觀光 -> `tourist_attraction`
  - 咖啡 / 咖啡廳 / 咖啡店 -> `cafe`
  - 酒吧 -> `bar`
  - 住宿 / 飯店 / 旅館 -> `lodging`
  - 博物館 -> `museum`
  - 公園 -> `park`
  - 百貨 / 商場 / 購物中心 -> `shopping_mall`
  *(其他輸入會直接透傳給 API，例如 `zoo`、`aquarium`、`bakery` 等)*

* **自訂回傳語言 (`--lang`)**：
  指定 Places API 回傳的地點名稱與地址語言編碼，預設為 `zh-TW`。
  ```bash
  # 搜尋日本東京鐵塔附近的酒吧，並要求回傳英文 (en) 資訊
  uv run places nearby --lat 35.6586 --lon 139.7454 --type bar --lang en
  ```
