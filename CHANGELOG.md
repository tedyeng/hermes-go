# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.0] - 2026-06-27

### Added
- **Taiwan Weather CLI (`tw-weather`)**: Implemented a new command line interface to query Taiwan local weather forecasts and rain alerts from the Central Weather Administration (CWA).
- **Check Command (`check`)**: General weather and umbrella recommendation utility supporting counties, districts, GPS/DMS locations, and Google Maps URL parsing. Features county-level fallback.
- **Hourly Command (`hourly`)**: Fine-grained 48-hour hourly sequence forecast displaying temperature, apparent temperature, relative humidity, precipitation probability, wind speed/direction, and wind safety alarms. Includes `--all-hours` option.
- **Rain Command (`rain`)**: Real-time rainfall observations from the nearest CWA automatic rain station, featuring live rain rate classifications (e.g. Drizzle, Light rain) and warning levels (Heavy Rain, Torrential, etc.).
- **Future Rain Outlook & Volume Estimate**: Displays a 2-day precipitation probability outlook and custom rainfall volume estimation (in mm ranges) derived from Wx and PoP fields.
- **County Summary & Board (`summary`, `board`)**: Fast 36-hour forecasts and a nation-wide rainfall ranking board.
- **Unit Tests**: Full suite coverage in `tests/test_tw_weather.py` with mock-based API offline tests.

### Changed
- **Project Version**: Upgraded package version in `pyproject.toml` to `0.4.0`.
- **Root README**: Updated the description of `tw-weather` in the root `README.md` to include all subcommands and features.

---

## [0.3.0] - 2026-06-19

### Added
- **Google Places CLI (`places`)**: Implemented a new command line interface using Google Places API to search for nearby restaurants, tourist attractions, or custom type spots globally.
- **Universal Coordinate Swapping**: Built a global latitude-longitude swap detection logic that automatically corrects coordinates if they are entered in the wrong order.
- **Deduplication & Combined Search**: Created a joint query mechanism when no type is specified, which merges restaurant and attraction searches, de-duplicates them by `place_id`, and sorts them by walking distance.
- **Language Localization**: Added the `--lang` flag (defaulting to `zh-TW`) to fetch names, addresses, and details in any supported Google Places API language (e.g. Japanese `ja` for searches in Tokyo).
- **Unit Tests**: Created a dedicated `tests/test_places.py` file to test the API query client, coordinates decoding, distance logic, and global swapping heuristics.
- **Documentation Restructuring**: Simplified the root `README.md` and modularized it by creating individual `README.md` files inside each CLI package (`src/jptrain/README.md`, `src/twbus/README.md`, `src/ubike/README.md`, `src/places/README.md`).

### Changed
- **Project Structure**: Updated `pyproject.toml` script entry points to register the `places` CLI, and created a dedicated implementation guide in `docs/places_implementation.md`.

---

## [0.2.0] - 2026-06-13


### Added
- **YouBike CLI (`ubike`)**: Implemented a new command line interface mirroring `twbus` structure to query nearby public bicycle stations.
- **Smart GPS Parser**: Added coordinates parser supporting decimal pairs, DMS coordinates, and Google Maps URLs (including phone-shared `maps.app.goo.gl` redirect resolution).
- **Proximity Calculations**: Built Haversine formula calculation to sort nearby YouBike stations by distance.
- **Terminal Hyperlinks**: Added `rich` terminal hyperlinks to YouBike station names to easily open Google Maps App on compatible devices.
- **Cache Support**: SQLite persistent token caching isolated in the user cache directory under the `ubike` namespace.
- **Unit Tests**: Created a dedicated `tests/test_ubike.py` file testing GPS parsing, coordinate adjustments, distance calculations, and TDX queries.
- **Design & Layout**: Created a 38-character mobile-friendly output display optimized for Telegram bot integrations and SSH mobile terminals.

### Changed
- **Default Proximity Radius**: Changed YouBike default search radius from `500m` to `200m`.
- **Exclusion of Apple Maps**: Explicitly ignored Apple Maps URL link formats (`apple.com`/`apple.co`) in the coordinate parsing logic.
- **Removed YouBike version string**: Simplified the print output layout by removing the redundant `YouBike 2.0` / `YouBike 1.0` labels.
- **Project Structure**: Updated `pyproject.toml` entry points, `README.md` documentation, and created a dedicated implementation guide in `docs/ubike_implementation.md`.

---

## [0.1.0] - 2026-06-07

### Added
- **jptrain CLI**: Japan railways status and route translation tool.
  - Real-time delay, suspension, and operation status queries.
  - Automatic Yahoo! transit routing queries with operator, line, and detail parameters.
  - Google Translation integration to translate Japanese railway terms into Traditional Chinese.
  - SQLite persistent cache for areas, routes, and railway details.
- **twbus CLI**: Taiwan bus arrival time (ETA) and route search tool.
  - Nearby bus stops queries (within 500m radius) sorted by proximity.
  - Route ETA query supporting went/return directions.
  - Geocoding support via Nominatim to resolve destination coordinates and find direct transit options.
  - DMS coordinates support for input formatting.
  - OAuth2 token caching mechanisms.
