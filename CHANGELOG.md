# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
