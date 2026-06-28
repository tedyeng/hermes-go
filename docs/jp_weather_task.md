# Tasks

- [x] Initialize Python project with `uv`
- [x] Add dependencies (`click`, `requests`, `rich`, `questionary`, `platformdirs`)
- [x] Implement geocoding & JMA weather API client (`src/jp_weather/api.py`)
- [x] Implement SQLite caching mechanism (`src/jp_weather/cache.py`)
- [x] Implement terminal formatting, custom WMO emoji mapping, and UI layout (`src/jp_weather/formatter.py`)
- [x] Implement CLI commands, click controller, and interactive wizard (`src/jp_weather/cli.py`)
- [x] Configure `pyproject.toml` console script entry point
- [x] Verify the application by running command lines
- [x] Create base unit tests and run them (`tests/test_jp_weather.py`)
- [x] Implement OpenStreetMap Nominatim fallback geocoding for tourist spots and mountains (e.g. "上高地")
- [x] Implement 3-hourly weather forecast block table (Next 24h) under current weather
- [x] Support smart CJK 3-character administrative suffix handling and variation matching
- [x] Implement robust error handling (avoiding uncaught exceptions on network failure) and cache failure protection
- [x] Create additional test suites for error handling, CJK 3-character matching, and cache reliability (`tests/test_weather_enhancements.py`)
- [x] Implement decimal and DMS (Degrees, Minutes, Seconds) GPS coordinate parsing and format sanitization (e.g. CJK/English formats)
- [x] Integrate OpenStreetMap Nominatim reverse geocoding to resolve GPS coordinates to CJK place names
- [x] Create unit tests for GPS parsing, Nominatim reverse geocoding, and network fallbacks
- [x] Generate and keep walkthrough updated (`walkthrough.md`)
- [x] Update and synchronize all project documentation and README files

## Mobile Layout Feature Integration
- [x] Modify `src/jp_weather/cli.py` to support `--mobile` options and adjust `--help` alignments
- [x] Add unit tests in `tests/test_weather_enhancements.py` for mobile output formatting
- [x] Update `README.md` and documentation
- [x] Verify functionality via CLI tests

## Golden & Blue Hour Feature Integration
- [x] Create pure Python `src/jp_weather/suncalc.py` solar astronomy calculation module
- [x] Update `src/jp_weather/api.py` to fetch hourly cloud cover and implement photography ratings
- [x] Add formatting tables and cards in `src/jp_weather/formatter.py` with `--mobile` support
- [x] Implement CLI command `golden` and interactive wizard entry in `src/jp_weather/cli.py`
- [x] Create unit tests for sun calculations and CLI integration in `tests/test_suncalc.py` and `tests/test_golden.py`
- [x] Document the feature in `docs/ideas/golden-hour.md` and `docs/specs/golden-hour-spec.md`

## Golden & Blue Hour Code Review Fixes
- [x] Define solar altitude constants to avoid magic numbers
- [x] Standardize dictionary output keys for polar day/night
- [x] Implement polar day/night status detection in `suncalc.py`
- [x] Update CLI type hints to ensure compatibility with Python 3.9
- [x] Create robust ISO datetime parser handling naive, aware, and trailing `Z` offsets
- [x] Implement timezone fallback heuristic based on coordinates within Japan
- [x] Integrate standard `logging` and replace silent request errors
- [x] Extract photography rating thresholds into module constants
- [x] Move geocoding sorting logic into a clean helper function
- [x] Add polar day/night UI warning banners for desktop/mobile views
- [x] Implement unit tests for polar status, ISO parser, and timezone fallback
- [x] Verify CLI behavior and pass all 29 tests
