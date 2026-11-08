# AGENTS.md

## Project overview
This repository contains a cross-platform PySide6 desktop application for scraping a playlist page, collecting video URLs, and generating ready-to-use FFmpeg commands for downloading them.

The project is intentionally lightweight and focused on a single workflow:
1. User enters a playlist URL.
2. Selenium loads the page.
3. The scraper extracts playlist item URLs.
4. Each video page is opened and the `<video>` source is parsed.
5. FFmpeg commands are generated for download.

## Stack
- Python 3.10+
- PySide6
- PyInstaller
- Selenium
- BeautifulSoup4
- lxml

## Repository structure
- `app.py` — PySide6 desktop UI and main app flow.
- `scraper.py` — Selenium scraping logic and playlist/video processing.
- `ffmpeg.py` — FFmpeg command generation.
- `config.py` — CSS selectors and constants.
- `requirements.txt` — Python dependencies.
- `.gitignore` — repo ignore rules.
- `README.md` — user-facing project documentation.

## How to run locally
From the project root:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

On macOS or Linux, activate the environment with `source .venv/bin/activate`.

## Important project notes
- This app depends on Chrome or a supported Chromium browser. Selenium Manager resolves a compatible ChromeDriver.
- Build distributables on each target operating system with PyInstaller; desktop binaries are not cross-compiled.
- The scraper is site-specific; selectors live in `config.py` and may need updates if the target website changes.
- FFmpeg command output should remain stable and copy-paste friendly.
- Do not commit generated cache files such as `__pycache__/` or compiled Python bytecode.

## Development guidance for AI agents
- Prefer minimal, surgical edits.
- Keep UI logic in `app.py` and scraping logic in `scraper.py`.
- Keep site-specific selectors and timing constants in `config.py`.
- Preserve the current result format so the app output stays consistent for users.
- Validate Python syntax after edits with:

```powershell
python -m py_compile app.py scraper.py ffmpeg.py config.py
```

- If the app is changed significantly, update the README or AGENTS.md with the new behavior.

## Typical tasks
- Improve scraper resilience for changed HTML/JS pages.
- Update selectors or wait times in `config.py`.
- Improve FFmpeg command formatting or naming.
- Add validation or error handling without changing the user interface flow.
