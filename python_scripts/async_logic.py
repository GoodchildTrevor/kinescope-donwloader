import asyncio
from logging import Logger

from playwright.async_api import (
    async_playwright,
    Page,
    Frame,
    ElementHandle,
    BrowserContext,
    Browser
)

from python_scripts.iframes import FrameUtils
from python_scripts.media import MediaInterceptor
from python_scripts.site import SiteClient


async def main_async(
        logger: Logger,
        url: str,
        username: str,
        password: str
) -> list[dict[str, str]]:
    """
    Основная асинхронная функция для автоматизации захвата видео.
    Осуществляет вход на сайт, находит видеоплееры Kinescope,
    запускает их и перехватывает m3u8-потоки, затем присваивает
    им соответствующие заголовки.
    :param url: URL-адрес страницы с контентом.
    :return: Список словарей с URL и заголовками захваченных медиа-файлов.
    """
    media_interceptor = MediaInterceptor(logger)

    async with async_playwright() as p:
        browser: Browser = await p.chromium.launch(headless=False)
        context: BrowserContext = await browser.new_context()
        page: Page = await context.new_page()

        frame_utils = FrameUtils(logger, page)
        lms_client = SiteClient(logger, page)

        # Логин
        if not await lms_client.perform_login(url, username, password):
            await browser.close()
            return []

        logger.info("⏳ Ожидаем загрузку контента...")
        try:
            await page.wait_for_selector("iframe#unit-iframe", timeout=30000)
            unit_iframe_element: ElementHandle | None = await page.query_selector("iframe#unit-iframe")
            if not unit_iframe_element:
                raise Exception("Основной iframe не найден")

            inner_frame: Frame | None = await unit_iframe_element.content_frame()
            if not inner_frame:
                raise Exception("Не удалось получить контент iframe")
        except Exception as e:
            logger.error(f"❌ Ошибка загрузки контента: {e}")
            await browser.close()
            return []

        # Перехват m3u8
        await page.route("**/*", lambda route, request: media_interceptor.intercept_m3u8(route, request))
        # Поиск Kinescope iframe'ов
        kinescope_iframes: list[ElementHandle] = await frame_utils.get_kinescope_iframes(inner_frame)

        for idx, iframe_handle in enumerate(kinescope_iframes):
            # Получаем заголовок для текущего видео
            current_title = await lms_client.get_video_title(inner_frame, idx)

            logger.info(f"🎯 Видео {idx + 1} заголовок: {current_title}")

            kinescope_frame: Frame | None = await iframe_handle.content_frame()
            if kinescope_frame:
                await frame_utils.play_kinescope_video(kinescope_frame, iframe_handle, idx)
                await asyncio.sleep(5)

                for media in reversed(media_interceptor.captured_media_info):
                    if media["title"] == "Untitled_Video":
                        media["title"] = current_title
                        break

        # Фильтрация уникальных
        final_media: list[dict[str, str]] = []
        seen_urls: set[str] = set()
        seen_titles: set[str] = set()

        for item in media_interceptor.captured_media_info:
            if item["url"] in seen_urls:
                continue
            title: str = item["title"]
            new_title: str = title
            suffix: int = 1
            while new_title in seen_titles:
                new_title = f"{title}_{suffix}"
                suffix += 1
            final_media.append({"url": item["url"], "title": new_title})
            seen_urls.add(item["url"])
            seen_titles.add(new_title)

        await browser.close()
        return final_media
