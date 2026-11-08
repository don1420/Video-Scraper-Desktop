import time

from urllib.parse import urljoin
from bs4 import BeautifulSoup
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
)
from ffmpeg import build_ffmpeg_command


def create_driver() -> ChromeWebDriver:
    options = Options()
    options.add_argument(HEADLESS_OPTION)
    return ChromeWebDriver(options=options)


def get_playlist_urls(driver: ChromeWebDriver, url: str) -> list[str]:
    driver.get(url)

    time.sleep(PAGE_LOAD_TIMEOUT)

    section = driver.find_element(By.CSS_SELECTOR, PLAYLIST_SECTION)
    driver.execute_script("arguments[0].scrollIntoView(true);", section)

    time.sleep(SCROLL_TIMEOUT)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    items = soup.select(PLAYLIST_ITEMS)

    return [
        item["data-file"]
        for item in items
        if item.get("data-file")
    ]


def get_video_src(driver: ChromeWebDriver, url: str) -> str | None:

    video_url = urljoin(driver.current_url, url)

    print(f"Opening video URL: {video_url}")

    driver.get(video_url)

    soup = BeautifulSoup(driver.page_source, "html.parser")

    video = soup.select_one(VIDEO_TAG)

    if video:
        return video.get("src")

    return None


def process_url(
    url: str,
    progress_callback=None,
) -> list[str]:
    driver = create_driver()

    try:
        files = get_playlist_urls(driver, url)

        results: list[str] = []

        total = len(files)

        for index, file_url in enumerate(files, start=1):
            video_src = get_video_src(driver, file_url)

            if video_src:
                results.append(
                    build_ffmpeg_command(video_src, index)
                )

            if progress_callback:
                progress_callback(index / total)

        return results

    finally:
        driver.quit()