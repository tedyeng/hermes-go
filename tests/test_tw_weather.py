import pytest
import time
from tw_weather.cache import SQLiteCache
from tw_weather.api import (
    parse_gps_input,
    normalize_county,
    extract_county_and_district,
    parse_weather_json,
    parse_county_weather_json,
    parse_hourly_weather_json,
    format_rain_value,
    display_rain_value,
    get_rain_alert_level,
    find_nearest_rain_station,
    calculate_distance,
    get_rain_intensity_label,
    get_rain_volume_estimate,
    estimate_3h_rain_volume,
    parse_3h_forecast_for_rain
)

def test_weather_cache():
    cache = SQLiteCache(expiration_seconds=2)
    cache.clear()
    
    cache.set("test_key", {"weather": "rain"})
    assert cache.get("test_key") == {"weather": "rain"}
    
    time.sleep(2.1)
    assert cache.get("test_key") is None

def test_parse_gps_input():
    # Decimal coords
    assert parse_gps_input("25.0339, 121.5644") == (25.0339, 121.5644)
    # DMS coords
    assert parse_gps_input("北緯25°5′0″ 東經121°34′43″") is not None
    # Google Maps query URL
    assert parse_gps_input("https://www.google.com/maps/search/?api=1&query=25.0339,121.5644") == (25.0339, 121.5644)
    # Invalid coords
    assert parse_gps_input("invalid string") is None

def test_normalize_county():
    assert normalize_county("台北市") == "臺北市"
    assert normalize_county(" 台中市 ") == "臺中市"
    assert normalize_county("宜蘭縣") == "宜蘭縣"

def test_extract_county_and_district():
    address1 = {
        "city": "臺北市",
        "suburb": "信義區",
        "county": "臺灣"
    }
    co, dist = extract_county_and_district(address1)
    assert co == "臺北市"
    assert dist == "信義區"

    address2 = {
        "county": "彰化縣",
        "town": "鹿港鎮"
    }
    co, dist = extract_county_and_district(address2)
    assert co == "彰化縣"
    assert dist == "鹿港鎮"

def test_parse_weather_json():
    # Mock CWA JSON response
    mock_response = {
        "success": "true",
        "result": {
            "records": {
                "Locations": [
                    {
                        "Location": [
                            {
                                "LocationName": "信義區",
                                "WeatherElement": [
                                    {
                                        "ElementName": "12小時降雨機率",
                                        "Time": [
                                            {
                                                "StartTime": "2026-06-27T12:00:00+08:00",
                                                "EndTime": "2026-06-28T00:00:00+08:00",
                                                "ElementValue": [{"ProbabilityOfPrecipitation": "20"}]
                                            },
                                            {
                                                "StartTime": "2026-06-28T00:00:00+08:00",
                                                "EndTime": "2026-06-28T12:00:00+08:00",
                                                "ElementValue": [{"ProbabilityOfPrecipitation": "40"}]
                                            },
                                            {
                                                "StartTime": "2026-06-28T12:00:00+08:00",
                                                "EndTime": "2026-06-29T00:00:00+08:00",
                                                "ElementValue": [{"ProbabilityOfPrecipitation": "80"}]
                                            },
                                            {
                                                "StartTime": "2026-06-29T00:00:00+08:00",
                                                "EndTime": "2026-06-29T12:00:00+08:00",
                                                "ElementValue": [{"ProbabilityOfPrecipitation": "20"}] # Low pop, but severe weather upgrade
                                            }
                                        ]
                                    },
                                    {
                                        "ElementName": "天氣現象",
                                        "Time": [
                                            # Overlapping 2026-06-27T12:00:00+08:00 ~ 00:00:00
                                            {"StartTime": "2026-06-27T12:00:00+08:00", "EndTime": "2026-06-27T15:00:00+08:00", "ElementValue": [{"Weather": "晴時多雲"}]},
                                            {"StartTime": "2026-06-27T15:00:00+08:00", "EndTime": "2026-06-27T18:00:00+08:00", "ElementValue": [{"Weather": "多雲"}]},
                                            # Overlapping 2026-06-28T00:00:00+08:00 ~ 12:00:00
                                            {"StartTime": "2026-06-28T00:00:00+08:00", "EndTime": "2026-06-28T03:00:00+08:00", "ElementValue": [{"Weather": "陰時多雲"}]},
                                            {"StartTime": "2026-06-28T03:00:00+08:00", "EndTime": "2026-06-28T06:00:00+08:00", "ElementValue": [{"Weather": "多雲短暫雨"}]},
                                            # Overlapping 2026-06-28T12:00:00+08:00 ~ 00:00:00
                                            {"StartTime": "2026-06-28T12:00:00+08:00", "EndTime": "2026-06-28T15:00:00+08:00", "ElementValue": [{"Weather": "雷陣雨"}]},
                                            # Overlapping 2026-06-29T00:00:00+08:00 ~ 12:00:00
                                            {"StartTime": "2026-06-29T00:00:00+08:00", "EndTime": "2026-06-29T03:00:00+08:00", "ElementValue": [{"Weather": "午後雷陣雨"}]}
                                        ]
                                    },
                                    {
                                        "ElementName": "溫度",
                                        "Time": [
                                            {"StartTime": "2026-06-27T12:00:00+08:00", "DataTime": "2026-06-27T12:00:00+08:00", "ElementValue": [{"Temperature": "32"}]},
                                            {"StartTime": "2026-06-27T15:00:00+08:00", "DataTime": "2026-06-27T15:00:00+08:00", "ElementValue": [{"Temperature": "30"}]},
                                            {"StartTime": "2026-06-28T00:00:00+08:00", "DataTime": "2026-06-28T00:00:00+08:00", "ElementValue": [{"Temperature": "26"}]},
                                            {"StartTime": "2026-06-28T03:00:00+08:00", "DataTime": "2026-06-28T03:00:00+08:00", "ElementValue": [{"Temperature": "28"}]},
                                            {"StartTime": "2026-06-28T12:00:00+08:00", "DataTime": "2026-06-28T12:00:00+08:00", "ElementValue": [{"Temperature": "29"}]},
                                            {"StartTime": "2026-06-29T00:00:00+08:00", "DataTime": "2026-06-29T00:00:00+08:00", "ElementValue": [{"Temperature": "25"}]}
                                        ]
                                    },
                                    {
                                        "ElementName": "舒適度指數",
                                        "Time": [
                                            {"StartTime": "2026-06-27T12:00:00+08:00", "DataTime": "2026-06-27T12:00:00+08:00", "ElementValue": [{"ComfortIndexDescription": "悶熱"}]},
                                            {"StartTime": "2026-06-28T00:00:00+08:00", "DataTime": "2026-06-28T00:00:00+08:00", "ElementValue": [{"ComfortIndexDescription": "舒適"}]}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    }

    periods = parse_weather_json(mock_response, "信義區")
    assert len(periods) == 4
    
    # 20% pop -> 不需帶傘
    assert periods[0]["pop"] == 20
    assert periods[0]["recommendation"] == "不需帶傘"
    assert periods[0]["temp_min"] == 30
    assert periods[0]["temp_max"] == 32
    assert periods[0]["comfort"] == "悶熱"
    
    # 40% pop -> 需帶折疊傘
    assert periods[1]["pop"] == 40
    assert periods[1]["recommendation"] == "需帶折疊傘"
    assert periods[1]["comfort"] == "舒適"
    
    # 80% pop -> 需帶直傘
    assert periods[2]["pop"] == 80
    assert periods[2]["recommendation"] == "需帶直傘"

    # 20% pop but Wx is "午後雷陣雨" (severe rain upgrade) -> 需帶折疊傘
    assert periods[3]["pop"] == 20
    assert periods[3]["recommendation"] == "需帶折疊傘"

def test_parse_county_weather_json():
    # Mock CWA F-C0032-001 response
    mock_county_response = {
        "success": "true",
        "result": {
            "records": {
                "datasetDescription": "三十六小時天氣預報",
                "location": [
                    {
                        "locationName": "臺北市",
                        "weatherElement": [
                            {
                                "elementName": "Wx",
                                "time": [
                                    {"startTime": "2026-06-27 12:00:00", "endTime": "2026-06-28 00:00:00", "parameter": {"parameterName": "多雲短暫陣雨"}},
                                    {"startTime": "2026-06-28 00:00:00", "endTime": "2026-06-28 12:00:00", "parameter": {"parameterName": "多雲"}},
                                    {"startTime": "2026-06-28 12:00:00", "endTime": "2026-06-29 00:00:00", "parameter": {"parameterName": "雷陣雨"}}
                                ]
                            },
                            {
                                "elementName": "PoP",
                                "time": [
                                    {"startTime": "2026-06-27 12:00:00", "endTime": "2026-06-28 00:00:00", "parameter": {"parameterName": "30"}},
                                    {"startTime": "2026-06-28 00:00:00", "endTime": "2026-06-28 12:00:00", "parameter": {"parameterName": "10"}},
                                    {"startTime": "2026-06-28 12:00:00", "endTime": "2026-06-29 00:00:00", "parameter": {"parameterName": "80"}}
                                ]
                            },
                            {
                                "elementName": "MinT",
                                "time": [
                                    {"startTime": "2026-06-27 12:00:00", "endTime": "2026-06-28 00:00:00", "parameter": {"parameterName": "26"}},
                                    {"startTime": "2026-06-28 00:00:00", "endTime": "2026-06-28 12:00:00", "parameter": {"parameterName": "25"}},
                                    {"startTime": "2026-06-28 12:00:00", "endTime": "2026-06-29 00:00:00", "parameter": {"parameterName": "27"}}
                                ]
                            },
                            {
                                "elementName": "MaxT",
                                "time": [
                                    {"startTime": "2026-06-27 12:00:00", "endTime": "2026-06-28 00:00:00", "parameter": {"parameterName": "32"}},
                                    {"startTime": "2026-06-28 00:00:00", "endTime": "2026-06-28 12:00:00", "parameter": {"parameterName": "30"}},
                                    {"startTime": "2026-06-28 12:00:00", "endTime": "2026-06-29 00:00:00", "parameter": {"parameterName": "34"}}
                                ]
                            },
                            {
                                "elementName": "CI",
                                "time": [
                                    {"startTime": "2026-06-27 12:00:00", "endTime": "2026-06-28 00:00:00", "parameter": {"parameterName": "舒適至悶熱"}},
                                    {"startTime": "2026-06-28 00:00:00", "endTime": "2026-06-28 12:00:00", "parameter": {"parameterName": "舒適"}},
                                    {"startTime": "2026-06-28 12:00:00", "endTime": "2026-06-29 00:00:00", "parameter": {"parameterName": "悶熱"}}
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    }

    periods = parse_county_weather_json(mock_county_response, "臺北市")
    assert len(periods) == 3
    
    # Period 1: 30% pop -> 需帶折疊傘
    assert periods[0]["pop"] == 30
    assert periods[0]["recommendation"] == "需帶折疊傘"
    assert periods[0]["wx_summary"] == "多雲短暫陣雨"
    assert periods[0]["comfort"] == "舒適至悶熱"
    assert periods[0]["temp_min"] == 26
    assert periods[0]["temp_max"] == 32
    
    # Period 2: 10% pop -> 不需帶傘
    assert periods[1]["pop"] == 10
    assert periods[1]["recommendation"] == "不需帶傘"
    assert periods[1]["comfort"] == "舒適"
    
    # Period 3: 80% pop -> 需帶直傘
    assert periods[2]["pop"] == 80
    assert periods[2]["recommendation"] == "需帶直傘"
    assert periods[2]["comfort"] == "悶熱"


def test_parse_hourly_weather_json():
    # Mock CWA hourly response
    mock_hourly_response = {
        "success": "true",
        "result": {
            "records": {
                "Locations": [
                    {
                        "Location": [
                            {
                                "LocationName": "信義區",
                                "WeatherElement": [
                                    {
                                        "ElementName": "溫度",
                                        "Time": [
                                            {"DataTime": "2026-06-27T12:00:00+08:00", "ElementValue": [{"Temperature": "32"}]},
                                            {"DataTime": "2026-06-27T13:00:00+08:00", "ElementValue": [{"Temperature": "31"}]}
                                        ]
                                    },
                                    {
                                        "ElementName": "相對濕度",
                                        "Time": [
                                            {"DataTime": "2026-06-27T12:00:00+08:00", "ElementValue": [{"RelativeHumidity": "75"}]},
                                            {"DataTime": "2026-06-27T13:00:00+08:00", "ElementValue": [{"RelativeHumidity": "80"}]}
                                        ]
                                    },
                                    {
                                        "ElementName": "體感溫度",
                                        "Time": [
                                            {"DataTime": "2026-06-27T12:00:00+08:00", "ElementValue": [{"ApparentTemperature": "35"}]},
                                            {"DataTime": "2026-06-27T13:00:00+08:00", "ElementValue": [{"ApparentTemperature": "34"}]}
                                        ]
                                    },
                                    {
                                        "ElementName": "舒適度指數",
                                        "Time": [
                                            {"DataTime": "2026-06-27T12:00:00+08:00", "ElementValue": [{"ComfortIndexDescription": "悶熱"}]},
                                            {"DataTime": "2026-06-27T13:00:00+08:00", "ElementValue": [{"ComfortIndexDescription": "悶熱"}]}
                                        ]
                                    },
                                    {
                                        "ElementName": "天氣現象",
                                        "Time": [
                                            {"StartTime": "2026-06-27T12:00:00+08:00", "EndTime": "2026-06-27T15:00:00+08:00", "ElementValue": [{"Weather": "多雲短暫陣雨"}]}
                                        ]
                                    },
                                    {
                                        "ElementName": "3小時降雨機率",
                                        "Time": [
                                            {"StartTime": "2026-06-27T12:00:00+08:00", "EndTime": "2026-06-27T15:00:00+08:00", "ElementValue": [{"ProbabilityOfPrecipitation": "30"}]}
                                        ]
                                    },
                                    {
                                        "ElementName": "風向",
                                        "Time": [
                                            {"StartTime": "2026-06-27T12:00:00+08:00", "EndTime": "2026-06-27T15:00:00+08:00", "ElementValue": [{"WindDirection": "東北風"}]}
                                        ]
                                    },
                                    {
                                        "ElementName": "風速",
                                        "Time": [
                                            {"StartTime": "2026-06-27T12:00:00+08:00", "EndTime": "2026-06-27T15:00:00+08:00", "ElementValue": [{"WindSpeed": "3"}]}
                                        ]
                                    }
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    }

    records = parse_hourly_weather_json(mock_hourly_response, "信義區")
    assert len(records) == 2
    
    # Hour 1 (12:00)
    assert records[0]["temp"] == "32"
    assert records[0]["rh"] == "75"
    assert records[0]["apparent_temp"] == "35"
    assert records[0]["comfort"] == "悶熱"
    assert records[0]["wx"] == "多雲短暫陣雨"
    assert records[0]["pop"] == 30
    assert records[0]["wind_dir"] == "東北風"
    assert records[0]["wind_speed"] == "3"

    # Hour 2 (13:00)
    assert records[1]["temp"] == "31"
    assert records[1]["rh"] == "80"
    assert records[1]["apparent_temp"] == "34"
    assert records[1]["comfort"] == "悶熱"
    assert records[1]["wx"] == "多雲短暫陣雨"
    assert records[1]["pop"] == 30
    assert records[1]["wind_dir"] == "東北風"
    assert records[1]["wind_speed"] == "3"


def test_format_rain_value():
    assert format_rain_value(None) == 0.0
    assert format_rain_value("-99") == -99.0
    assert format_rain_value("-98") == 0.0
    assert format_rain_value("T") == 0.01
    assert format_rain_value("25.5") == 25.5
    
    assert display_rain_value(None) == "0.0 mm"
    assert display_rain_value("-99") == "缺值/無資料"
    assert display_rain_value("-98") == "0.0 mm"
    assert display_rain_value("T") == "雨跡 (Trace)"
    assert display_rain_value("12.3") == "12.3 mm"


def test_get_rain_alert_level():
    level, _ = get_rain_alert_level(0, 0, 550)
    assert "超大豪雨" in level
    
    level, _ = get_rain_alert_level(0, 210, 50)
    assert "大豪雨" in level
    
    level, _ = get_rain_alert_level(0, 110, 50)
    assert "豪雨" in level
    
    level, _ = get_rain_alert_level(45, 0, 10)
    assert "大雨" in level
    
    level, _ = get_rain_alert_level(10, 20, 30)
    assert "一般" in level


def test_find_nearest_rain_station():
    mock_rain_data = {
        "success": "true",
        "result": {
            "records": {
                "Station": [
                    {
                        "StationName": "觀測站A",
                        "StationId": "A001",
                        "GeoInfo": {
                            "Coordinates": [
                                {
                                    "CoordinateName": "WGS84",
                                    "StationLatitude": "25.0339",
                                    "StationLongitude": "121.5644"
                                }
                            ]
                        },
                        "RainfallElement": {
                            "Now": {"Precipitation": "10.0"}
                        }
                    },
                    {
                        "StationName": "觀測站B",
                        "StationId": "B002",
                        "GeoInfo": {
                            "Coordinates": [
                                {
                                    "CoordinateName": "WGS84",
                                    "StationLatitude": "25.1000",
                                    "StationLongitude": "121.5000"
                                }
                            ]
                        },
                        "RainfallElement": {
                            "Now": {"Precipitation": "5.0"}
                        }
                    }
                ]
            }
        }
    }
    
    target_lat = 25.0340
    target_lon = 121.5645
    
    station, dist = find_nearest_rain_station(mock_rain_data, target_lat, target_lon)
    assert station["StationName"] == "觀測站A"
    assert station["StationId"] == "A001"
    assert dist < 0.5


def test_get_rain_intensity_label():
    assert get_rain_intensity_label(-99.0) == "暫無即時雨勢資料"
    assert get_rain_intensity_label(0.0) == "目前無顯著降雨"
    assert get_rain_intensity_label(1.5) == "毛毛雨，可不撐傘"
    assert get_rain_intensity_label(5.0) == "小雨，出門記得帶傘"
    assert get_rain_intensity_label(15.0) == "大雨，開車騎車請減速"
    assert get_rain_intensity_label(35.0) == "豪雨或雷雨，注意低窪地區積水"


def test_get_rain_volume_estimate():
    assert get_rain_volume_estimate("多雲", 0) == "無雨 (0 mm)"
    assert get_rain_volume_estimate("多雲", 10) == "無雨 (0 mm)"
    assert get_rain_volume_estimate("多雲短暫雷陣雨", 70) == "大雨等級 (約 10~30 mm)"
    assert get_rain_volume_estimate("短暫陣雨", 40) == "小雨至中雨 (約 2~10 mm)"
    assert get_rain_volume_estimate("陰天有毛毛雨", 30) == "微量/毛毛雨 (<2 mm)"
    assert get_rain_volume_estimate("多雲", 80) == "小雨至中雨 (約 2~10 mm)"


def test_estimate_3h_rain_volume():
    # No rain
    assert estimate_3h_rain_volume(0, "多雲") == (0.0, 0.0)
    assert estimate_3h_rain_volume(10, "多雲") == (0.0, 0.0)
    # Drizzle / Light rain
    assert estimate_3h_rain_volume(30, "毛毛雨") == (0.0, 1.0)
    assert estimate_3h_rain_volume(60, "毛毛雨") == (0.1, 2.0)
    # Moderate rain
    assert estimate_3h_rain_volume(40, "陣雨") == (0.5, 3.0)
    assert estimate_3h_rain_volume(70, "下雨") == (2.0, 8.0)
    # Heavy rain
    assert estimate_3h_rain_volume(80, "雷陣雨", weather_code=15) == (8.0, 25.0)
    assert estimate_3h_rain_volume(30, "大雨", weather_code=30) == (2.0, 10.0)
    # Extremely heavy
    assert estimate_3h_rain_volume(90, "大豪雨", weather_code=31) == (25.0, 60.0)


def test_parse_3h_forecast_for_rain():
    mock_cwa_res = {
        "success": "true",
        "records": {
            "Locations": [{
                "Location": [{
                    "LocationName": "信義區",
                    "WeatherElement": [
                        {
                            "ElementName": "3小時降雨機率",
                            "Time": [
                                {
                                    "StartTime": "2026-06-27T12:00:00+08:00",
                                    "EndTime": "2026-06-27T15:00:00+08:00",
                                    "ElementValue": [{"ProbabilityOfPrecipitation": "60"}]
                                },
                                {
                                    "StartTime": "2026-06-27T15:00:00+08:00",
                                    "EndTime": "2026-06-27T18:00:00+08:00",
                                    "ElementValue": [{"ProbabilityOfPrecipitation": "70"}]
                                }
                            ]
                        },
                        {
                            "ElementName": "天氣現象",
                            "Time": [
                                {
                                    "StartTime": "2026-06-27T12:00:00+08:00",
                                    "EndTime": "2026-06-27T15:00:00+08:00",
                                    "ElementValue": [{"Weather": "短暫陣雨或雷雨", "WeatherCode": "15"}]
                                },
                                {
                                    "StartTime": "2026-06-27T15:00:00+08:00",
                                    "EndTime": "2026-06-27T18:00:00+08:00",
                                    "ElementValue": [{"Weather": "短暫陣雨或雷雨", "WeatherCode": "15"}]
                                }
                            ]
                        }
                    ]
                }]
            }]
        }
    }
    periods = parse_3h_forecast_for_rain(mock_cwa_res, "信義區")
    assert len(periods) > 0
    p = periods[0]
    assert "白天" in p["period_name"] or "晚上" in p["period_name"]
    assert p["pop"] == 70
    assert p["wx_summary"] == "短暫陣雨或雷雨"
    # min_accum should be 8.0 + 8.0 = 16.0
    assert p["min_mm"] == 16.0
    # max_accum should be 25.0 + 25.0 = 50.0
    assert p["max_mm"] == 50.0






