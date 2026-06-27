# CWA Weather CLI Rain Intensity and Forecast Extension Plan

We will add real-time rain intensity classification labels and a future 24-hour rainfall probability outlook to the `tw-weather rain` command.

## User Review Required

> [!IMPORTANT]
> 1. **Real-time Rain Intensity Label (即時雨勢狀態標籤)**:
>    - Uses the 1-hour accumulated rain rate (`Past1hr` from `O-A0002-001`) to output rain intensity descriptions:
>      - $0.1 \le \text{rate} \le 2.0\text{ mm/hr}$: `毛毛雨，可不撐傘`
>      - $2.0 < \text{rate} \le 10.0\text{ mm/hr}$: `小雨，出門記得帶傘`
>      - $10.0 < \text{rate} \le 30.0\text{ mm/hr}$: `大雨，開車騎車請減速`
>      - $> 30.0\text{ mm/hr}$: `豪雨或雷雨，注意低窪地區積水`
>      - $\text{rate} = 0.0$: `目前無顯著降雨`
> 2. **Future Rainfall & Probability Outlook**:
>    - Since `F-C0032-003` / `F-C0032-004` (Quantitative Precipitation Forecast) is not registered under the CWA RESTful datastore API (returns 404), we will query the future 3-day town forecast (`F-D0047-063`) or 2-day hourly forecast (`F-D0047-061`) to display the **未來 24 小時降雨展望 (Future 24H Rain Outlook)**.
>    - It will list 3-hourly forecast blocks showing the weather description (`天氣現象` Wx) and probability of precipitation (`降雨機率` PoP).

## Open Questions

None.

## Proposed Changes

---

### [Component: Weather CLI and API]

#### [MODIFY] [api.py](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/tw_weather/api.py)
- **Intensity Calculator**:
  - Add `get_rain_intensity_label(rain_1h: float) -> str` returning the appropriate Chinese rain status text.

#### [MODIFY] [cli.py](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/tw_weather/cli.py)
- **Rain Command Enhancement**:
  - Fetch both live rain observations (`O-A0002-001`) and the town weather forecast (`F-D0047-xxx`) based on resolved county/district.
  - Display the **即時雨勢體感 (Current Rain Intensity)** label under the live observation block.
  - Append a **未來 24 小時降雨展望 (Future 24H Rain Outlook)** section showing the weather types and rain probabilities for the next 24 hours in 3-hourly blocks.

## Verification Plan

### Automated Tests
- Add `test_get_rain_intensity_label()` in `tests/test_tw_weather.py`.

### Manual Verification
- Run `tw-weather rain "臺北市信義區"` to check current rainfall, rain intensity label, and future 24H rain probability forecast.
