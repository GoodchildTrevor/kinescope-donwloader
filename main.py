import asyncio
from dotenv import load_dotenv
import gradio as gr
import logging
import os

from python_scripts.async_logic import main_async
from python_scripts.media import MediaInterceptor

# Настройка логгера
logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Извлечение переменных окружения
load_dotenv()
USERNAME = os.getenv("LMS_EMAIL")
PASSWORD = os.getenv("LMS_PASSWORD")

with gr.Blocks() as demo:
    gr.Markdown("# 🎬 Kinescope Downloader")

    # Страница 1 — поиск
    with gr.Column(visible=True) as page1:
        url_input = gr.Textbox(label="🔗 Введите URL страницы", placeholder="https://...")
        run_btn = gr.Button("Начать извлечение видео")
        status_box1 = gr.Textbox(label="Статус", lines=4)

    # Страница 2 — выбор и скачивание
    with gr.Column(visible=False) as page2:
        video_checklist = gr.CheckboxGroup(label="Выберите видео для скачивания", choices=[])
        download_btn = gr.Button("Скачать выбранные")
        back_btn = gr.Button("⬅ Назад")
        status_box2 = gr.Textbox(label="Статус", lines=4)

    media_storage = gr.State([])


    def find_videos(url: str) -> tuple:
        """
        Основная функция для поиска видео на указанном URL.
        Запускает асинхронный процесс `main_async` для поиска видео.
        Обновляет пользовательский интерфейс, показывая статус
        поиска и список найденных видео.
        :param url: URL-адрес страницы для поиска видео.
        :yield: Кортеж, содержащий статус, видимость элементов UI и список медиа.
        """
        status: str = "🔍 Подготовка к скачиванию..."
        yield status, gr.update(visible=True), gr.update(visible=False), [], []
        media_list: list[dict[str, str]] = asyncio.run(main_async(logger, url, USERNAME, PASSWORD))
        if not media_list:
            yield "❌ Видео не найдено", gr.update(visible=True), gr.update(visible=False), [], []
            return
        titles: list[str] = [m["title"] for m in media_list]
        yield f"✅ Найдено {len(titles)} видео", gr.update(visible=False), gr.update(
            visible=True), media_list, gr.update(choices=titles)


    def download_selected(selected_titles: list[str], media_list: list[dict[str, str]]) -> str:
        """
        Скачивает выбранные видео.
        Создаёт экземпляр `MediaInterceptor`, фильтрует список медиа-файлов по
        выбранным заголовкам и запускает асинхронную загрузку.
        :param selected_titles: Список заголовков видео, выбранных для скачивания.
        :param media_list: Полный список найденных медиа-файлов.
        :return: Сообщение о статусе скачивания.
        """
        if not selected_titles:
            return "⚠ Ничего не выбрано"
        interceptor = MediaInterceptor(logger)
        interceptor.captured_media_info = [m for m in media_list if m["title"] in selected_titles]
        asyncio.run(interceptor.download_media_list())
        return f"✅ Скачано {len(selected_titles)} видео"


    def go_back() -> tuple:
        """
        Функция для возврата к начальному состоянию пользовательского интерфейса.
        :return: Обновления видимости для элементов UI.
        """
        return gr.update(visible=True), gr.update(visible=False)

    # Привязка кнопок
    run_btn.click(find_videos, inputs=url_input, outputs=[status_box1, page1, page2, media_storage, video_checklist])
    download_btn.click(download_selected, inputs=[video_checklist, media_storage], outputs=status_box2)
    back_btn.click(go_back, outputs=[page1, page2])


if __name__ == "__main__":
    demo.launch()
