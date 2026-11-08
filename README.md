# Video Scraper

A cross-platform desktop application that extracts video sources from a playlist page and generates ready-to-use **FFmpeg** commands. The app runs natively on Windows, macOS, and Linux; it does not require a browser-based UI or a local web server.

## Features

* Enter a playlist URL.
* Automatically extract all video pages using Selenium.
* Parse video sources with BeautifulSoup.
* Generate FFmpeg commands for each video.
* Display progress while processing videos in the background.
* Copy generated commands or save them to a text file.

## Project Structure

```text
project/
├── app.py          # PySide6 desktop user interface
├── scraper.py      # Selenium scraping logic
├── ffmpeg.py       # FFmpeg command generation
├── config.py       # CSS selectors and constants
├── requirements.txt
└── README.md
```

## Requirements

* Python 3.10+
* Google Chrome or another Chromium-based browser supported by Selenium
* Selenium Manager (included with Selenium) to locate/download a compatible ChromeDriver

## Installation

Clone the repository:

```bash
git clone <repository-url>
cd <repository-name>
```

Create a virtual environment:

### Windows

Open PowerShell or Command Prompt and run:

```bash
python --version
```

If the python command is not recognized, try:

```bash
py --version
```

If py works but python does not, Python is installed, but its executable may not be configured in the Windows PATH environment variable.
You can use py instead of python in the commands below.
If Python is not installed, download it from:
https://www.python.org/downloads/
During installation, enable Add Python to PATH.

```bash
python -m venv venv
venv\Scripts\activate
```

### Linux / macOS

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

## Run the desktop app

```bash
python app.py
```

Enter a playlist URL, start scraping, and use **Copy commands** or **Save to file** to export the results. The window remains responsive while Selenium processes the playlist.

## Build a desktop executable

Install the requirements, then build on each target operating system:

```bash
python -m PyInstaller --noconfirm --clean --windowed --name VideoScraper app.py
```

The app bundle/executable is placed in `dist/`. Build separately on Windows, macOS, and Linux; PyInstaller does not cross-compile desktop applications. The target machine still needs a supported browser installed. Selenium Manager handles the matching driver.

## How It Works

1. Open the provided playlist URL.
2. Scroll to the playlist section.
3. Extract all `data-file` URLs.
4. Visit each video page.
5. Find the `<video>` element.
6. Extract the `src` attribute.
7. Generate an FFmpeg command for each video.

Example output:

```bash
ffmpeg -i "https://example.com/video1.mp4" -c copy -bsf:a aac_adtstoasc 1.mp4;
ffmpeg -i "https://example.com/video2.mp4" -c copy -bsf:a aac_adtstoasc 2.mp4;
```

## Technologies

* PySide6 / Qt
* Selenium
* BeautifulSoup4
* Chrome WebDriver
* FFmpeg

## Notes

* The target website must allow access through Selenium.
* Selenium opens the browser in headless mode.
* The first Selenium run may need an internet connection so Selenium Manager can obtain a compatible driver.

## License

This project is provided for educational and personal use. Ensure you have permission to download and use any content processed with this tool.
