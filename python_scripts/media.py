import asyncio
from logging import Logger
import subprocess
from urllib.parse import urlparse

from playwright.async_api import (
    Route,
    Request,
)


class MediaInterceptor:
    """
    Класс для перехвата и загрузки медиа-потоков M3U8.
    :param logger: Объект логгера для вывода информации.
    :type logger: Logger
    """
    def __init__(self, logger: Logger):
        self.logger: Logger = logger
        self.captured_media_info: list[dict[str, str]] = []
        self.seen_m3u8_urls: set[str] = set()

    async def intercept_m3u8(
            self,
            route: Route,
            request: Request) -> None:
        """
        Перехватывает M3U8 потоки, фильтрует их и сохраняет информацию для последующей загрузки.
        Проверяет URL-адрес запроса. Если он содержит '.m3u8' и не является потоком с параметрами 'quality' или 'type',
        информация о нём добавляется в список для загрузки.
        :param route: Объект маршрута Playwright, используемый для продолжения запроса.
        :param request: Объект запроса Playwright.
        """
        request_url: str = request.url
        parsed_url = urlparse(request_url)

        if ".m3u8" in request_url:
            query_params: str = parsed_url.query
            if "quality=" in query_params and ("type=video" in query_params or "type=audio" in query_params):
                await route.continue_()
                return

            if request_url not in self.seen_m3u8_urls:
                self.logger.info(f"🎥 Захвачен m3u8 поток: {request_url}")
                self.captured_media_info.append({"url": request_url, "title": "Untitled_Video"})
                self.seen_m3u8_urls.add(request_url)

        await route.continue_()

    async def download_media_list(self) -> None:
        """
        Скачивает медиа-файлы из списка `captured_media_info`.
        Ожидает появления медиа-файлов в списке до 30 секунд. Для каждого M3U8 URL-адреса
        использует FFmpeg для загрузки и сохранения файла в формате MP4.
        """
        cooldown: int = 0
        while not self.captured_media_info:
            await asyncio.sleep(1)
            cooldown += 1
            if cooldown >= 30:
                self.logger.error("❌ Медиа-файлы не найдены, выход.")
                return

        for media_item in self.captured_media_info:
            m3u8_url: str = media_item["url"]
            raw_title: str = media_item.get("title", "")

            sanitized_title: str = "".join(
                c for c in raw_title if c.isalnum() or c in (" ", ".", "_", "-")
            ).strip() or "downloaded_video"

            output_file_name: str = f"{sanitized_title.replace(' ', '_')}.mp4"

            if ".m3u8" not in m3u8_url:
                self.logger.warning(f"⚠️ URL '{m3u8_url}' не является .m3u8 файлом, пропускаем.")
                continue

            self.logger.info(f"🔗 Скачиваем: {m3u8_url} -> {output_file_name}")
            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", m3u8_url, "-c", "copy", output_file_name],
                    check=True,
                    capture_output=True
                )
                self.logger.info(f"✅ Готово: {output_file_name}")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"❌ Ошибка FFmpeg для {output_file_name}: {e}")
                self.logger.error(f"stdout: {e.stdout.decode(errors='ignore')}")
                self.logger.error(f"stderr: {e.stderr.decode(errors='ignore')}")
            except FileNotFoundError:
                self.logger.error("❌ FFmpeg не найден. Установите FFmpeg и добавьте в PATH.")
