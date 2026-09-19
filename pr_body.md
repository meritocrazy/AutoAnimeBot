## Summary

This PR implements comprehensive security, correctness, performance, and code quality improvements across the AutoAnimeBot codebase.

## Security Fixes
- **Removed hardcoded Telegram API credentials** (`functions/config.py:29-30`) - API_ID and API_HASH now require environment variables
- **Fixed shell injection in FFmpeg commands** (`functions/tools.py`) - Rewrote `compress()`, `genss()`, `gen_ss_sam()` using `asyncio.create_subprocess_exec` with argument lists instead of shell f-strings
- **Updated Docker base image** from EOL `python:3.12.3-slim-buster` (Debian 10) to `python:3.12-slim-bookworm` (Debian 12) with non-root `appuser`; removed `chmod 777 /usr/src/app`

## Correctness Fixes
- **Replaced 26 occurrences of `except BaseException:`** with `except Exception:` across 9 files to allow KeyboardInterrupt/SystemExit propagation
- **Fixed TelegramClient import** in `functions/schedule.py:29` - now imports from `telethon` instead of `libs.logger`
- **Replaced `os.execl` hard restart** with graceful `SIGTERM` signal in `functions/schedule.py:63`
- **Fixed syntax error** in `auto_env_gen.py:96` (unterminated string literal)

## Performance Improvements
- **Converted blocking `subprocess.Popen` in `genss()`** to async `asyncio.create_subprocess_exec`
- **Shared single `aiohttp.ClientSession`** in `libs/kitsu.py` via lazy `_get_session()` instead of creating new session per call

## Testing
- **Added 30 unit tests** (`pytest.ini`, `tests/test_tools.py`) covering:
  - Tools: `hbs()`, `TimeFormatter`, CRF validation (20-51 range)
  - Config, AnimeInfo, Reporter, Torrent, Database, Schedule, AdminUtils
- All 30 tests passing

## Code Quality
- **Extracted shared subprocess logic** to new `libs/subprocess_utils.py` (`run_subprocess`, `run_ffmpeg`, `run_aria2c`) - eliminates duplicate code between `libs/ariawarp.py` and `functions/tools.py`
- **Added try/finally temp directory cleanup** in `tools.init_dir()` for `encode/`, `thumbs/`, `downloads/`
- **Added comprehensive docstrings** to all DataBase methods in `database/__init__.py`
- **Fixed naming conventions** (`dB` → `DB`), f-string interpolation issues, redefined built-in `id`, broad exceptions, unnecessary comprehensions
- **Applied `black` + `isort` formatting** (line-length 120)

## Metrics
- **Pylint score: 7.09 → 8.49/10**
- **All 30 tests passing**

## Files Changed
- Modified: 16 files
- Added: `libs/subprocess_utils.py`, `tests/test_tools.py`, `pytest.ini`