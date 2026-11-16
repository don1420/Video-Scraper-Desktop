import time

from urllib.parse import urljoin
from bs4 import BeautifulSoup, Tag
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.webdriver import WebDriver as ChromeWebDriver
from selenium.webdriver.common.by import By

from config import (
    HEADLESS_OPTION,
    PAGE_LOAD_TIMEOUT,
    PLAYLIST_ITEMS,
    PLAYLIST_SECTION,
    SCROLL_TIMEOUT,
    VIDEO_TAG,
    TITLE_SELECTOR,
)
from ffmpeg import build_ffmpeg_command


def create_driver() -> ChromeWebDriver:
    options = Options()
    options.add_argument(HEADLESS_OPTION)
    return ChromeWebDriver(options=options)


def get_playlist_urls(driver: ChromeWebDriver, url: str) -> list[str]:
    return [
        file_url
        for file_url, _ in get_playlist_entries(driver, url)
    ]


def get_playlist_entries(
    driver: ChromeWebDriver,
    url: str,
) -> list[tuple[str, str | None]]:
    driver.get(url)

    time.sleep(PAGE_LOAD_TIMEOUT)

    section = driver.find_element(By.CSS_SELECTOR, PLAYLIST_SECTION)
    driver.execute_script("arguments[0].scrollIntoView(true);", section)

    time.sleep(SCROLL_TIMEOUT)

    soup = BeautifulSoup(driver.page_source, "html.parser")
    page_title = _extract_title(
        soup.select_one('span.origintitle[itemprop="alternateName"]')
    )
    playlist_section = soup.select_one(PLAYLIST_SECTION)
    if playlist_section is None:
        raise ValueError("Playlist section was not found in the loaded page.")

    items = playlist_section.select(PLAYLIST_ITEMS)

    entries: list[tuple[str, str | None]] = []
    for item in items:
        file_url = item.get("data-file")
        if not file_url:
            continue

        entries.append((file_url, page_title))

    return entries


def get_video_src(driver: ChromeWebDriver, url: str) -> str | None:
    video_src, _ = get_video_details(driver, url)
    return video_src


def get_video_details(
    driver: ChromeWebDriver,
    url: str,
) -> tuple[str | None, str | None]:
    video_url = urljoin(driver.current_url, url)

    print(f"Opening video URL: {video_url}")

    driver.get(video_url)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    video = soup.select_one(VIDEO_TAG)
    title_element = soup.select_one(TITLE_SELECTOR)
    title = _extract_title(title_element)

    return (video.get("src") if video else None, title)


def _extract_title(title_element: Tag | None) -> str | None:
    if title_element is None:
        return None

    title = title_element.get_text(" ", strip=True)

    return title.strip() or None


def process_url(
    url: str,
    progress_callback=None,
) -> list[str]:
    video_sources = process_video_sources(url, progress_callback)
    return [
        build_ffmpeg_command(video_src, index)
        for index, video_src in enumerate(video_sources, start=1)
    ]


def process_video_sources(
    url: str,
    progress_callback=None,
) -> list[str]:
    return [
        video_src
        for video_src, _ in process_video_details(url, progress_callback)
    ]


def process_video_details(
    url: str,
    progress_callback=None,
) -> list[tuple[str, str | None]]:
    driver = create_driver()

    try:
        entries = get_playlist_entries(driver, url)

        video_details: list[tuple[str, str | None]] = []

        total = len(entries)

        for index, (file_url, playlist_title) in enumerate(entries, start=1):
            video_src = get_video_src(driver, file_url)

            if video_src:
                video_details.append((video_src, playlist_title))

            if progress_callback and total:
                progress_callback(index / total)

        return video_details

    finally:
        driver.quit()