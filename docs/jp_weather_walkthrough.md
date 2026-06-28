# Walkthrough - jp_weather (Japan Weather CLI)

We have successfully designed and built a gorgeous, high-performance CLI tool for querying current weather and 1-week forecasts in Japan. It features full interactive prompts, caching, automated CJK geocoding suffix generation, and professional styling in the terminal.

---

## 🌟 Key Accomplishments

1. **Integrated Open-Meteo Geocoding & Weather APIs**:
   - High-fidelity search with country filtering to prioritize Japan (`JP`).
   - Integrated Open-Meteo standard daily forecast featuring JMA/MSM/GSM model layers, high-resolution coverage, and **precipitation probabilities (Pop)**.

2. **Built-in Smart CJK Search Suffixes**:
   - Short 2-character Japanese place name queries (e.g. `東京`, `京都`, `大阪`, `青森`) automatically generate variants appending common administrative suffixes (`市`, `都`, `府`, `縣`, etc.) to guarantee high geocoding search hit-rates.

3. **High-Performance Caching System**:
   - Created a persistent caching mechanism using SQLite inside OS-native cache directories (`platformdirs`).
   - Geocoding results are cached for **24 hours**.
   - Weather forecasts are cached for **15 minutes** to balance accuracy and respect API limits.

4. **Stunning Terminal UI Rendering (`rich` + `questionary`)**:
   - Display current weather conditions inside a gorgeous card panel with weather emojis, apparent/relative temperatures, wind direction arrows, and current rainfall, **accompanied by a 3-hourly forecast trend table for the next 24 hours**.
   - Display 7-day outlook using clean, color-coded temperature ranges (blue for min, red for max) along with UV warnings, and Pop symbols.
   - Interactive place selector lists when multiple location matches are detected.

5. **Direct GPS Coordinate (Decimal & DMS) Parsing & OSM Reverse Geocoding**:
   - Direct decimal GPS coordinates (e.g., `35.6895, 139.6917`) or **DMS degree-minute-second formats** (e.g., `北緯25°5′0″  東經121°34′43″` or `N 35° 41' 22" E 139° 41' 30"`) are parsed, mathematically converted to decimal values, validated, and reverse-geocoded using the **OpenStreetMap Nominatim Reverse API**.
   - Gracefully resolves real place/road names (like `港墘路, 台北市, 台灣` or `都庁通り, 東京都, 日本`) to display on the weather card, bypasses geocoding, and falls back to placeholder coordinates names if offline.

---

## 🚀 How to Run the Tool

This project is fully managed using `uv` with support for console script mappings.

### 1. Execute subcommands directly

- **Get Current Weather**:
  ```bash
  uv run jp-weather current "東京"
  ```
  *Output Panel Example:*
  ```text
  📍 港墘路, 台北市, 台灣
  🌐 緯度: 25.0833  經度: 121.5786  時區: Asia/Taipei
  ╭───────────────── 🌦 目前天氣狀態 Current Weather ─────────────────╮
  │                                                                  │
  │                          體感溫度 Apparent Temp :   29.3°C       │
  │    ☀  27.8°C             相對濕度 Humidity      :   57%          │
  │                          風速風向 Wind Speed    :   12.4 m/s ↙   │
  │    目前天氣：            目前降雨 Precipitation :   0.0 mm       │
  │    晴天 / Clear Sky                                              │
  │                                                                  │
  │                                                                  │
  ╰──────────────────────────────────────────────────────────────────╯
  
  🕒 近期每 3 小時預報 Hourly Forecast (Next 24h)
  ╭──────────────┬─────────────────────────┬───────────┬──────────────╮
  │ 時間 Time    │ 天氣 Weather            │ 氣溫 Temp │ 降雨機率 Pop │
  ├──────────────┼─────────────────────────┼───────────┼──────────────┤
  │ 00:00 (現在) │ ⛅ 多雲 / Partly Cloudy │    18.8°C │           0% │
  │ 03:00 (+3h)  │ 🌤 晴間 / Mainly Clear   │    17.3°C │           0% │
  │ 06:00 (+6h)  │ ☁ 陰天 / Overcast       │    17.3°C │           0% │
  │ 09:00 (+9h)  │ ☁ 陰天 / Overcast       │    22.1°C │           0% │
  │ 12:00 (+12h) │ ⛅ 多雲 / Partly Cloudy │    25.7°C │           0% │
  │ 15:00 (+15h) │ ☀ 晴天 / Clear Sky      │    27.4°C │          10% │
  │ 18:00 (+18h) │ ☀ 晴天 / Clear Sky      │    25.2°C │          14% │
  │ 21:00 (+21h) │ ☀ 晴天 / Clear Sky      │    21.4°C │           0% │
  ╰──────────────┴─────────────────────────┴───────────┴──────────────╯
  ```

- **Get 7-Day Forecast**:
  ```bash
  uv run jp-weather forecast "Kyoto"
  ```
  *Output Table Example (renders clean color-coded temperature ranges):*
  ```text
  📅 7 天天氣預報 7-Day Outlook : 京都市, 日本
  時區 Timezone: Asia/Tokyo | 更新時間 Update Time: 2026-05-31 10:38
  
  ╭────────────┬────────────┬────────────┬────────────┬────────────┬─────────────╮
  │            │ 天氣       │   降雨機率 │   累積降雨 │            │  氣溫變化   │
  │ 日期 Date  │ Weather    │        Pop │       Rain │ 紫外線 UV  │ Temp Range  │
  ├────────────┼────────────┼────────────┼────────────┼────────────┼─────────────┤
  │ 2026-05-31 │ ☁ 陰天 /   │        14% │     0.0 mm │ 7.2 (高 /  │  16.6°C ~   │
  │ (週日)     │ Overcast   │            │            │   High)    │   27.4°C    │
  │ 2026-06-01 │ ☁ 陰天 /   │         0% │     0.0 mm │ 7.3 (高 /  │  17.2°C ~   │
  │ (週一)     │ Overcast   │            │            │   High)    │   29.7°C    │
  ╰────────────┴────────────┴────────────┴────────────┴────────────┴─────────────╯
  ```

### 2. Run Interactive Wizard Mode

Running `jp_weather` without subcommands launches the premium interactive guided wizard:
```bash
uv run jp-weather
```
- It prompts you for a location.
- If multiple matches are found, it opens an interactive select menu.
- It prompts you to select whether to view the Current Weather, 7-Day Forecast, or Both!

### 3. Mobile Layout Mode (`--mobile`)

For users reading weather on their mobile terminals (e.g., iPhone 16 Pro running Termius or SSH), standard desktop layouts can easily cause border misalignment or wrapping. 

By passing the `--mobile` option parameter to any subcommand or parent command, the tool renders a narrow, super compact 38-column layout optimized specifically for monospaced mobile displays:

- **Mobile Current Weather**:
  ```bash
  uv run jp-weather --mobile current "東京"
  ```
  *Output Example:*
  ```text
  🌦 東京都 目前天氣 Current Weather

  📍 東京都, 日本
  🌐 緯度: 35.69 經度: 139.69
  ⏰ 時區: Asia/Tokyo

  🌤  22.8°C  晴間

  體感 Apparent : 24.1°C
  濕度 Humidity : 70%
  風速 Wind Spd : 7.6 m/s ↑
  降雨 Rain     : 0.0 mm



  🕒 3小時預報 Hourly Forecast
  ● 18:00* 🌤 晴間 24.0°C 0%
  ● 21:00 ☁ 陰天 21.5°C 0%
  ● 00:00 ☁ 陰天 20.4°C 0%
  ● 03:00 ☁ 陰天 19.8°C 0%
  ```

- **Mobile 7-Day Forecast**:
  ```bash
  uv run jp-weather forecast "大阪" --mobile
  ```
  *Output Cards Example:*
  ```text
  📅 7 天天氣預報 7-Day Outlook
  📍 大阪市, 大阪府, 日本
  更新: 05-31 15:44

  ● 2026-05-31 (週日) ☁ 陰天
    🌡️ 氣溫: 17.4°C ~ 27.9°C
    🌧️ 降雨: 0% | 0.0 mm
    ☀️ 紫外線: 5.7 (中)
  ```

### 4. Clear Local Caches

If you wish to refresh and purge the local cache:
```bash
uv run jp-weather clean
```

### 5. Golden & Blue Hour (📸)

This feature calculates the exact times for **Golden Hour** and **Blue Hour** (morning and evening) along with a photography recommendation index (1 to 5 stars) based on cloud cover and precipitation forecasts.

- **Query Today's Golden Hour**:
  ```bash
  uv run jp-weather golden "東京"
  ```
  *Output Example:*
  ```text
  📍 Tokyo Heliport, 千葉県, 日本
  🌐 緯度: 35.6333  經度: 139.8500  時區: Asia/Tokyo
  ╭──────────────── 📸 黃金時刻與藍調時刻 Golden & Blue Hour ────────────────╮
  │                                                                          │
  │  ╭── 🌅 晨間光影 Morning Light ──╮    ╭── 🌇 傍晚光影 Evening Light ──╮  │
  │  │ 晨間藍調 Blue Hour… 03:58 -   │    │ 日落時刻 Sunset   … 🌇 18:55  │  │
  │  │ :                   04:09     │    │ :                             │  │
  │  │ 晨間黃金 Golden     04:09 -   │    │ 傍晚黃金 Golden     18:18 -   │  │
  │  │ Hour :              05:05     │    │ Hour :              19:14     │  │
  │  │ 日出時刻 Sunrise  … 🌅 04:27  │    │ 傍晚藍調 Blue Hour… 19:14 -   │  │
  │  │ :                             │    │ :                   19:25     │  │
  │  │ 晨間攝影推薦指數  … ★★★★★     │    │ 傍晚攝影推薦指數  … ★★★★★     │  │
  │  │ :                             │    │ :                             │  │
  │  │ 天氣實況與指引    … ⛅        │    │ 天氣實況與指引    … ⛅        │  │
  │  │ :                   雲量適中… │    │ :                   雲量適中… │  │
  │  ╰───────────────────────────────╯    ╰───────────────────────────────╯  │
  │                                                                          │
  ╰──────────────────────────────────────────────────────────────────────────╯
  ```

- **Query 7-Day Forecast**:
  ```bash
  uv run jp-weather golden "京都" --week
  ```
  Generates a tabular forecast displaying transition slots and ratings for the entire week.

- **Mobile View Integration**:
  ```bash
  uv run jp-weather golden "富士山" --mobile
  ```
  Formats all light phases and recommendations vertically under 38 characters.

- **Polar Region Support**:
  In high-latitude areas experiencing polar days (midnight sun) or polar nights, the system automatically detects the status and prints localized warning panels:
  ```text
  ☀️ 極晝狀態 (Polar Day) / Midnight Sun
  此地太陽今日終日不落。
  整日均為白晝，可全天進行戶外拍攝，但無傳統日出/日落的黃金與藍調時刻。
  ```

---

## 🧪 Verification & Testing

We created a robust unit test suite targeting critical utility functions, caching logic, edge-case geocoding behaviors, API mock layers, solar calculations, DMS coordinates, and command integration.
To run the test suite:
```bash
.venv/bin/pytest
```

*Results:*
```text
============================== 29 passed in 0.49s ==============================
```
All tests pass successfully!

### Test Suite Breakdown

Our testing architecture consists of four primary test modules:

1. **`tests/test_jp_weather.py` (6 Tests)**:
   - **`test_is_cjk`**: Verifies accurate detection of CJK characters.
   - **`test_clean_query`**: Ensures input queries are stripped of trailing or leading spaces.
   - **`test_get_weather_info`**: Validates the translation mapping from WMO weather codes.
   - **`test_get_wind_direction_arrow`**: Validates wind arrow mapping depending on wind direction angle.
   - **`test_get_weekday_ch`**: Verifies Chinese weekday formatting.
   - **`test_geocode`**: Tests geocoding by mocking HTTP API requests to Open-Meteo.

2. **`tests/test_weather_enhancements.py` (9 Tests)**:
   - **`test_get_weather_returns_none_on_http_error`**: Verifies that network timeouts or HTTP failures gracefully return `None`.
   - **`test_fetch_weather_with_cache_handles_failure`**: Verifies that failed API calls propagate `None` cleanly and do not populate the SQLite cache.
   - **`test_geocode_suffixes_for_three_char_query`**: Verifies the CJK matching suffix generation.
   - **`test_parse_gps`**: Validates decimal and DMS GPS coordinate parsing.
   - **`test_reverse_geocode_success`**: Mocks the Nominatim reverse geocoding API.
   - **`test_reverse_geocode_failure`**: Verifies graceful fallback to coordinates-labeled placeholders.
   - **`test_cli_current_mobile` / `test_cli_forecast_mobile` / `test_cli_current_cancel`**: Tests CLI mobile formats and cancellations.

3. **`tests/test_suncalc.py` (5 Tests)**:
   - **`test_julian_conversions`**: Validates datetime-to-Julian calculations.
   - **`test_tokyo_solstice_sun_times`**: Checks solar math accuracy against Tokyo summer solstice.
   - **`test_london_equinox_sun_times`**: Checks solar math accuracy against London equinox.
   - **`test_solar_phases_order`**: Verifies chronological ordering constraints.
   - **`test_polar_status_detection`**: Validates polar status detection for high-latitude locations (Tromsø solstices/equinox).

4. **`tests/test_golden.py` (9 Tests)**:
   - **`test_calculate_photography_rating_rain` / `overcast` / `perfect_clouds` / `clear`**: Tests cloud and rain thresholds for rating stars.
   - **`test_cli_golden_today` / `week_and_mobile` / `cancel`**: Tests the `golden` CLI subcommand execution and arguments.
   - **`test_parse_iso_datetime`**: Validates ISO datetime parsing for naive, offset, and trailing `Z` values.
   - **`test_reverse_geocode_timezone_fallback`**: Verifies coordinates-based fallback timezone heuristics (Tokyo vs Tromsø).
