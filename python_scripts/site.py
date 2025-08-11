import asyncio
from logging import Logger
from playwright.async_api import (
    Page,
    Frame,
    TimeoutError as PlaywrightTimeout
)


class SiteClient:
    """
    Класс-клиент для взаимодействия с сайтом.
    :param logger: Экземпляр логгера для вывода сообщений.
    :param page: Экземпляр страницы Playwright.
    """
    def __init__(self, logger: Logger, page: Page) -> None:
        self.logger = logger
        self.page = page

    async def perform_login(self, url: str, username: str, password: str) -> bool:
        """
        Выполняет логин.
        :param url: URL страницы входа.
        :param username: Имя пользователя (email).
        :param password: Пароль пользователя.
        :return: True, если вход выполнен успешно или уже авторизованы, иначе False.
        """
        self.logger.info("🌐 Загружаем страницу входа...")
        await self.page.goto(url, timeout=60000)

        try:
            await self.page.wait_for_selector('input[type="email"], input[name="email"]', timeout=15000)
            await self.page.fill('input[type="email"], input[name="email"]', username)
            await self.page.fill('input[type="password"]', password)

            async with self.page.expect_navigation(timeout=60000):
                await self.page.click('button[type="submit"]')

            self.logger.info("🔐 Успешный вход")
            return True
        except PlaywrightTimeout:
            self.logger.warning("⚠️ Поля логина не найдены. Возможно, вы уже авторизованы.")
            return True
        except Exception as e:
            self.logger.error(f"❌ Ошибка входа: {e}")
            return False

    async def get_video_title(self, inner_frame: Frame, idx: int = 0) -> str:
        """
        Извлекает название урока из первых двух <p> внутри блока xblock-student_view-html.
        :param inner_frame: Фрейм, содержащий контент
        :param idx: Индекс блока (начиная с 0)
        :return: Название урока в формате, готовом для использования в имени файла.
        """
        base_title = "Untitled_Video"

        try:
            container = inner_frame.locator("div.xblock-student_view-html")
            if await container.count() <= idx:
                self.logger.warning(f"⚠️ Блок xblock-student_view-html #{idx} не найден")
                return base_title

            p_locator = container.nth(idx).locator("p")
            p_count = await p_locator.count()
            if p_count == 0:
                self.logger.warning(f"⚠️ В блоке #{idx} нет <p>")
                return base_title

            parts: list[str] = []
            for i in range(min(2, p_count)):
                text = await p_locator.nth(i).text_content()
                if text:
                    parts.append(text.strip().replace("\n", " ").replace("\r", " "))

            base_title = " ".join(parts).strip()
            base_title = "".join(c for c in base_title if c.isalnum() or c in (' ', '.', '_', '-')).strip()
            base_title = base_title.replace(" ", "_") or "Untitled_Lesson"

            self.logger.info(f"📝 Извлечён заголовок видео из блока #{idx}: {base_title}")
        except Exception as title_e:
            self.logger.warning(f"⚠️ Не удалось извлечь заголовок видео для блока #{idx}: {title_e}")

        return base_title

    async def activate_tab(self, tab_index: int) -> None:
        """
        Активирует вкладку с видео по индексу.
        :param tab_index: Индекс вкладки (начиная с 0).
        """
        tab_elements = self.page.locator(".sf-unit-tab.sequence-tab-view-navigation__tab")
        if await tab_elements.count() > tab_index:
            is_current_tab = "sf-unit-tab--current" in (await tab_elements.nth(tab_index).get_attribute("class") or "")
            if not is_current_tab:
                self.logger.info(f"➡️ Активируем вкладку {tab_index + 1}...")
                await tab_elements.nth(tab_index).click()
                await self.page.wait_for_load_state('domcontentloaded', timeout=10000)
                await asyncio.sleep(2)
