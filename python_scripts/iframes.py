from logging import Logger
from playwright.async_api import Page, Frame, ElementHandle, TimeoutError as PlaywrightTimeout


class FrameUtils:
    """
    Класс для работы с фреймами Playwright на страницах с видео Kinescope.
    Обеспечивает поиск видео-фреймов и управление воспроизведением.
    :param logger: Экземпляр логгера для вывода сообщений
    :param page: Экземпляр страницы Playwright
    """
    def __init__(self, logger: Logger, page: Page) -> None:
        self._logger = logger
        self._page = page

    async def get_kinescope_iframes(self, inner_frame: Frame) -> list[ElementHandle]:
        """
        Находит все iframe'ы с видеоплеерами Kinescope.
        :param inner_frame: Фрейм, содержащий контент страницы
        :return: Список найденных элементов iframe
        :raises PlaywrightTimeout: Если iframe не найден в течение 30 секунд
        """
        self._logger.info("🔍 Поиск Kinescope iframe'ов...")
        await inner_frame.wait_for_selector(
            "iframe[src*='kinescope.io']",
            timeout=30000
        )
        return await inner_frame.query_selector_all("iframe[src*='kinescope.io']")

    async def play_kinescope_video(
            self,
            frame: Frame,
            iframe_handle: ElementHandle,
            idx: int
    ) -> None:
        """
        Запускает воспроизведение видео Kinescope.
        Пытается кликнуть по кнопке Play. Если кнопка не найдена,
        кликает по центру iframe.
        :param frame: Внутренний фрейм с плеером
        :param iframe_handle: Элемент iframe в родительском фрейме
        :param idx: Индекс видео (начиная с 0) для логирования
        """
        try:
            await self._click_play_button(frame, idx)
        except PlaywrightTimeout:
            self._logger.warning(
                f"⚠️ Кнопка воспроизведения не найдена для видео {idx + 1}. "
                "Кликаем по центру."
            )
            await self._click_center(iframe_handle)

    async def _click_play_button(self, frame: Frame, idx: int) -> None:
        """Клик по кнопке воспроизведения видео в Kinescope плеере.
        :param frame: Фрейм Playwright, содержащий видео-плеер
        :param idx: Индекс видео (начиная с 0) для логирования
        :raises playwright.async_api.TimeoutError: Если кнопка не найдена за 10 секунд
        """
        play_button_selector = (
            "button[aria-label*='Play'], "
            "div[class*='play-button'], "
            "video, "
            "div[aria-label*='Воспроизвести']"
        )
        await frame.locator(play_button_selector).first.wait_for(timeout=10000)
        await frame.locator(play_button_selector).first.click()
        self._logger.info(f"▶️ Запущено воспроизведение видео {idx + 1}")

    async def _click_center(self, iframe_handle: ElementHandle) -> None:
        """Клик по центру iframe элемента.
        :param iframe_handle: Хэндл iframe элемента
        :note: Если bounding box недоступен, клик не выполняется
        """
        box = await iframe_handle.bounding_box()
        if box:
            await self._page.mouse.click(
                box['x'] + box['width'] / 2,
                box['y'] + box['height'] / 2
            )
