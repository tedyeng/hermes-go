# ubike 🚲 (台灣 YouBike 即時車況 CLI)

`ubike` 串接台灣 TDX 運輸資料流通服務，輸入 GPS 座標、度分秒 DMS、或地圖連結（Google Maps）即可查詢範圍內 YouBike 站點，顯示車輛與空位數，並提供地圖連結。

本工具專為行動裝置終端機最佳化，**預設採用 38 欄寬度的直式排版**，非常適合在手機（如 Termius）或 Telegram 中使用。

## 🔧 設定與前置步驟
與 `twbus` 相同，在使用前需於專案根目錄的 `.env` 檔案中設定 TDX API 憑證：
```env
TDX_CLIENT_ID=您的_tdx_client_id
TDX_CLIENT_SECRET=您的_tdx_client_secret
```

---

## 💻 使用方法

### 1. 查詢附近 YouBike 站點即時狀態
直接傳入您複製的 GPS 資訊，支援多種輸入格式：
- **經緯度數值**（如 `"25.02605, 121.5436"`，經緯度倒置會自動校正）
- **度分秒 DMS 格式**（如 `"北緯25°01'33.8\" 東經121°32'37.0\""`)
- **Google 地圖網址**（支援一般網址與手機分享之 `maps.app.goo.gl` 短網址）
- *Apple Maps 連結會被自動排除忽略*

```bash
# 輸入經緯度數值
uv run ubike nearby "25.02605, 121.5436"

# 輸入度分秒 DMS 格式
uv run ubike nearby "北緯25°01'33.8\" 東經121°32'37.0\""
```

### 2. 透過選項查詢附近站點
若想手動輸入緯度、經度與設定搜尋半徑 (radius，預設為 200m)，可以使用以下選項：
```bash
uv run ubike nearby --lat 25.0260 --lon 121.5436 --radius 200
```

### 3. 清除本地 YouBike 快取資料
手動清空 SQLite 中的快取 Access Token 資料：
```bash
uv run ubike clean
```
