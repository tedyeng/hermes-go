# Implementation Plan - Mobile Layout CLI Parameter Integration

We will implement the `--mobile` layout optimization parameter in the `jp_weather` CLI so that terminal outputs can render in a vertical, compact 38-column layout suitable for narrow mobile screen terminal emulators (specifically for iPhone 16 Pro running Termius or SSH).

## User Review Required

> [!IMPORTANT]
> - We will support the `--mobile` option at both the main CLI group level (`jp_weather --mobile ...`) and individual subcommand levels (`jp_weather current ... --mobile`). This offers maximum user convenience.
> - We will update the CLI `--help` examples block to perfectly align the `#` comment characters, keeping them cleanly aligned with 3 additional spaces of padding relative to the previous version.

## Proposed Changes

### `src/jp_weather/cli.py`

#### [MODIFY] [cli.py](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/jp_weather/cli.py)
- Import `render_current_weather`, `render_forecast_weather` with `mobile` parameter support.
- Add `@click.option("--mobile", is_flag=True, help="...")` to the `cli` group, `current` subcommand, and `forecast` subcommand.
- Update `cli(ctx, mobile)` to pass the `mobile` flag to the interactive wizard: `interactive_wizard(mobile)`.
- Update `interactive_wizard(mobile=False)` signature and pass the `mobile` flag to the formatting functions: `render_current_weather(..., mobile=mobile)` and `render_forecast_weather(..., mobile=mobile)`.
- Decorate `current` and `forecast` subcommands with `@click.pass_context` and extract `is_mobile = mobile or (ctx.parent.params.get("mobile") if ctx.parent else False)`. Pass `mobile=is_mobile` to the formatters.
- Update the main `cli` docstring help text and its usage examples to have `#` comments perfectly aligned (with 3 additional spaces of padding on the DMS coordinate example line, and all other lines aligned to it).

### `tests/test_weather_enhancements.py`

#### [MODIFY] [test_weather_enhancements.py](file:///Users/tedyeng/VSCodeProjects/hermes-go/tests/test_weather_enhancements.py)
- Add unit tests for the `--mobile` options using Click's `CliRunner`.
- Assert that `--mobile` runs successfully and formats output in a 38-column layout constraints without errors.

### `src/jp_weather/formatter.py`

#### [MODIFY] [formatter.py](file:///Users/tedyeng/VSCodeProjects/hermes-go/src/jp_weather/formatter.py)
- Change WMO emoji parsing inside `get_weather_info` to automatically strip the Variation Selector-16 (`\ufe0f`) globally to prevent terminal box border misalignment.
- Remove border grids in mobile layout's hourly forecast table by setting `box=None`.
- Remove `Panel` box borders from mobile layout's 7-day daily forecast cards, rendering them as borderless paragraphs.
- Redesign desktop weather status in `render_current_weather` to segment location metadata (header block) and current conditions (compact 68-character wide panel) to prevent horizontal stretching.

### Documentation

#### [MODIFY] [README.md](file:///Users/tedyeng/VSCodeProjects/hermes-go/README.md)
- Update the documentation to introduce the new `--mobile` layout option parameter.
- Update the CLI examples section in README.md.

---

## Verification Plan

### Automated Tests
- Run `uv run pytest` to execute the whole test suite including new tests for `--mobile`.

### Manual Verification
- Run:
  ```bash
  uv run jp-weather --mobile current "東京"
  uv run jp-weather current "東京" --mobile
  uv run jp-weather forecast "Kyoto" --mobile
  uv run jp-weather --mobile
  ```
- Verify that terminal rendering displays perfectly aligned border boxes within the 38-column constraint on mobile emulators.
