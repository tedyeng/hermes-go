# Japan Weather CLI Migration Document

The `japan-weather` standalone project has been migrated into `hermes-go` as a native module to consolidate regional weather tools.

## Migration Summary

- **Source Location**: `/Users/tedyeng/VSCodeProjects/japan-weather`
- **Target Module**: `src/jp_weather`
- **CLI Entrypoint Command**: `jp-weather`
- **CLI Function Mapping**: `jp_weather.cli:cli`

## Codebase Modifications

1. **Imports**:
   - All references to `jpweather` package imports changed to `jp_weather`.
2. **Configuration & Scripts**:
   - `pyproject.toml` updated with entrypoint: `jp-weather = "jp_weather.cli:cli"`.
3. **Caching**:
   - SQLite cache directory updated to construct via `user_cache_dir("jp_weather")`.
4. **Loggers & User-Agents**:
   - Logger updated to `"jp_weather.api"`.
   - Nominatim geocoding User-Agent changed to `"jp_weather_cli_agent_tedyeng"`.

## Verification Steps

### Automated Tests
Run the following test files:
```bash
PYTHONPATH=src uv run python -m pytest tests/test_jp_weather.py tests/test_golden.py tests/test_suncalc.py tests/test_weather_enhancements.py
```

### Manual CLI Validation
```bash
# Check help and examples
uv run jp-weather --help

# Check current weather in Tokyo
uv run jp-weather current "東京"

# Check forecast for Kyoto
uv run jp-weather forecast "Kyoto"

# Check Golden hour in Tromsø (polar testing)
uv run jp-weather golden "Tromsø" --week
```
