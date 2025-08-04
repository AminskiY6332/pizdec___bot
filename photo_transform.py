"""
Улучшенный модуль для генерации изображений по одному фото через Replicate API
PixelPie AI - Фото Преображение
"""

import replicate
import asyncio
import aiohttp
import os
import logging
import base64
from typing import Optional, Dict, Any, Union, List
from datetime import datetime
from PIL import Image
import io

from logger import get_logger
logger = get_logger('generation')

class PhotoTransformGenerator:
    """Класс для генерации изображений по одному фото через Replicate"""

    def __init__(self, replicate_api_key: str):
        """
        Инициализация генератора

        Args:
            replicate_api_key: API ключ для Replicate
        """
        self.api_key = replicate_api_key
        os.environ["REPLICATE_API_TOKEN"] = replicate_api_key

        # Улучшенные стили генерации с крутыми промптами
        self.styles = {
            "photoshop": {
                "name": "🤍 Фотошоп Pro",
                "description": "Профессиональная ретушь и улучшение",
                "prompt_template": "Professional magazine cover portrait of @person, luxury beauty photoshoot, flawless porcelain skin with healthy glow, perfect makeup enhancement, whitened teeth, sparkling eyes with enhanced iris detail, volumized hair with perfect styling, slimmed face contours, enhanced jawline, removed blemishes and wrinkles, studio lighting with rim light, bokeh background, fashion magazine quality, beauty filter applied, skin smoothing, color grading like vogue cover, ultra HD, 32K resolution, professional retouching, glamour photography",
                "model": "runwayml/gen4-image",
                "model_type": "gen4"
            },
            "art": {
                "name": "🎨 AI Art",
                "description": "Цифровое искусство в стиле Artstation",
                "prompt_template": "Stunning digital art portrait of @person by trending artist on Artstation, vibrant oil painting style mixed with digital art, ethereal glowing skin, dreamy soft focus background, magical particles floating, saturated colors with complementary color scheme, artistic brush strokes visible, fantasy art style, beautiful rim lighting, concept art quality, painted by Sam Spratt and Lois van Baarle style, ultra detailed, 8K wallpaper quality, digital masterpiece, award winning artwork",
                "model": "runwayml/gen4-image",
                "model_type": "gen4"
            },
            "cinema": {
                "name": "🎬 Кино",
                "description": "Голливудский блокбастер",
                "prompt_template": "Epic cinematic portrait of @person, Hollywood blockbuster movie still, directed by Christopher Nolan aesthetic, anamorphic lens flare, teal and orange color grading, dramatic key lighting with shadows, film grain texture, IMAX quality, depth of field blur, movie poster composition, intense emotional expression, rain or fog atmosphere, action movie vibes, shot on Arri Alexa, professional color correction, letterbox format, cinematic masterpiece, 4K BluRay quality",
                "model": "runwayml/gen4-image",
                "model_type": "gen4"
            },
            "portrait": {
                "name": "🖼️ Портрет",
                "description": "Психологический портрет как у Leibovitz",
                "prompt_template": "Intimate psychological portrait of @person, shot by Annie Leibovitz style, deep emotional storytelling, Rembrandt lighting, shallow depth of field, medium format camera quality, raw authentic expression, environmental portrait with meaningful background, natural imperfections retained for character, shot on Hasselblad, fine art photography, museum quality print, powerful eye contact, soul-revealing portrait, timeless black and white option, National Geographic portrait quality",
                "model": "runwayml/gen4-image",
                "model_type": "gen4"
            },
            "fantasy": {
                "name": "⚡ Киберпанк",
                "description": "Blade Runner 2049 стиль",
                "prompt_template": "Futuristic cyberpunk portrait of @person, Blade Runner 2049 aesthetic, neon pink and blue lighting, holographic effects, augmented reality elements, rain-soaked streets reflection, cybernetic enhancements, glowing LED implants, dystopian megacity background, volumetric fog, ray tracing reflections, metallic textures, tech wear fashion, atmospheric haze, Roger Deakins cinematography style, neo-noir mood, ultra detailed sci-fi world, RTX rendering quality",
                "model": "runwayml/gen4-image",
                "model_type": "gen4"
            },
            "lego": {
                "name": "🧱 LEGO",
                "description": "Официальная LEGO минифигурка",
                "prompt_template": "Official LEGO minifigure of @person, authentic LEGO product photography, perfect plastic molding with visible LEGO logo on studs, genuine minifigure proportions, interchangeable hair piece, printed face details not stickers, articulated arms and rotating head, clutch power hands, standing on green LEGO baseplate, soft studio lighting, slight plastic sheen, box art quality, instruction manual style, Danish design precision, collector's edition quality, macro lens detail showing texture, official LEGO certified design",
                "model": "runwayml/gen4-image",
                "model_type": "gen4"
            }
        }

        # Доступные соотношения сторон с эмодзи
        self.aspect_ratios = {
            "9:16": "📱 9:16",
            "4:3": "📺 4:3",
            "3:4": "🖼️ 3:4",
            "1:1": "⬜ 1:1",
            "16:9": "🖥️ 16:9"
        }

        # Маппинг для нормализации сокращенных aspect_ratio
        self.aspect_ratio_map = {
            "9": "9:16",
            "16": "16:9",
            "4": "4:3",
            "3": "3:4",
            "1": "1:1"
        }

        # Доступные разрешения (только 720p для фиксации)
        self.resolutions = {
            "720p": "720p"
        }

        # Клиент Replicate
        self.client = replicate.Client(api_token=replicate_api_key)

    async def generate_image(self, image_bytes: bytes, style: str, user_id: int, aspect_ratio: str = "3:4", resolution: str = "720p") -> Dict[str, Any]:
        """
        Генерация изображения в выбранном стиле с поддержкой aspect_ratio

        Args:
            image_bytes: Байты изображения
            style: Выбранный стиль генерации
            user_id: ID пользователя
            aspect_ratio: Соотношение сторон
            resolution: Разрешение (по умолчанию и фиксировано "720p")

        Returns:
            Словарь с результатами генерации
        """
        try:
            logger.info(f"Начало генерации для пользователя {user_id} в стиле {style}, aspect_ratio={aspect_ratio}, resolution={resolution}")

            if style not in self.styles:
                raise ValueError(f"Неизвестный стиль: {style}")

            # Нормализация aspect_ratio если передан сокращенный вариант
            if aspect_ratio in self.aspect_ratio_map:
                aspect_ratio = self.aspect_ratio_map[aspect_ratio]
                logger.info(f"Нормализовали aspect_ratio к {aspect_ratio}")

            if aspect_ratio not in self.aspect_ratios:
                raise ValueError(f"Неподдерживаемое соотношение сторон: {aspect_ratio}")

            if resolution not in self.resolutions:
                raise ValueError(f"Неподдерживаемое разрешение: {resolution}")

            style_config = self.styles[style]

            # Предобработка изображения: конвертация в JPG
            logger.info(f"Предобработка изображения: конвертация в JPG")
            try:
                img = Image.open(io.BytesIO(image_bytes))
            except Exception as pil_err:
                raise ValueError(f"Невозможно открыть изображение: {str(pil_err)}")

            buffer = io.BytesIO()
            img.convert('RGB').save(buffer, format="JPEG", quality=95)
            buffer.seek(0)
            processed_image_bytes = buffer.read()

            # Создаем data URI
            data_uri = self._create_data_uri(processed_image_bytes)

            # Параметры для модели
            input_params = {
                "prompt": style_config['prompt_template'],
                "aspect_ratio": aspect_ratio,
                "reference_tags": ["person"],
                "reference_images": [data_uri],
                "output_resolution": resolution
            }

            # Создаем prediction
            logger.info(f"Создание prediction для модели {style_config['model']}")

            prediction = await asyncio.to_thread(
                self.client.predictions.create,
                model=style_config['model'],
                input=input_params
            )

            logger.info(f"Prediction создан: {prediction.id}")

            # Ждем завершения
            while prediction.status not in ["succeeded", "failed", "canceled"]:
                await asyncio.sleep(2)
                prediction = await asyncio.to_thread(
                    self.client.predictions.get,
                    prediction.id
                )
                logger.info(f"Статус: {prediction.status}")

            if prediction.status == "succeeded":
                output_url = prediction.output

                logger.info(f"Тип output: {type(output_url)}")
                logger.info(f"Output значение: {output_url}")

                if isinstance(output_url, str):
                    result_url = output_url
                else:
                    result_url = str(output_url)
                    logger.info(f"Преобразовали {type(output_url)} в строку: {result_url}")

                logger.info(f"Генерация завершена успешно, URL: {result_url}")

                return {
                    "success": True,
                    "result_url": result_url,
                    "style": style,
                    "style_name": style_config['name'],
                    "timestamp": datetime.now().isoformat(),
                    "prediction_id": prediction.id
                }
            else:
                error_msg = f"Генерация завершилась со статусом: {prediction.status}"
                if hasattr(prediction, 'error') and prediction.error:
                    error_msg += f" - {prediction.error}"

                logger.error(f"Ошибка генерации: {error_msg}")

                return {
                    "success": False,
                    "error": error_msg,
                    "style": style,
                    "timestamp": datetime.now().isoformat()
                }

        except Exception as e:
            logger.error(f"Ошибка генерации для пользователя {user_id}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "style": style,
                "timestamp": datetime.now().isoformat()
            }

    def _create_data_uri(self, image_bytes: bytes) -> str:
        """
        Создает data URI для изображения.

        Args:
            image_bytes: Байты изображения

        Returns:
            str: data:image/jpeg;base64,BASE64STRING
        """
        b64_string = base64.b64encode(image_bytes).decode('utf-8')
        return f"data:image/jpeg;base64,{b64_string}"

    async def download_generated_image(self, url: str) -> bytes:
        """
        Скачивание сгенерированного изображения по public URL (без Auth).

        Args:
            url: Public URL изображения

        Returns:
            Байты изображения
        """
        try:
            timeout = aiohttp.ClientTimeout(total=60)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        image_bytes = await response.read()
                        logger.debug(f"Первые 10 байт скачанного: {image_bytes[:10]}")
                        return image_bytes
                    else:
                        error_text = await response.text()
                        raise Exception(f"Ошибка скачивания: HTTP {response.status} - {error_text}")
        except Exception as e:
            logger.error(f"Ошибка при скачивании: {str(e)}")
            raise

    def get_style_keyboard(self) -> List[List[Dict[str, str]]]:
        """
        Получение клавиатуры со стилями для inline-кнопок

        Returns:
            Список кнопок для InlineKeyboardMarkup
        """
        keyboard = []

        row = []
        for style_key, style_info in self.styles.items():
            button_data = {
                "text": style_info["name"],
                "callback_data": f"transform_style:{style_key}"
            }
            row.append(button_data)

            if len(row) == 2:
                keyboard.append(row)
                row = []

        if row:
            keyboard.append(row)

        keyboard.append([{"text": "❌ Отменить", "callback_data": "transform_cancel"}])

        return keyboard

    def get_style_info(self, style: str) -> Optional[Dict[str, str]]:
        return self.styles.get(style)

    def get_style_description(self, style: str) -> str:
        descriptions = {
            "photoshop": """🤍 Фотошоп Pro / Журнальная ретушь

Превращаем твое фото в обложку Vogue!
✨ Идеальная кожа с естественным сиянием
✨ Профессиональная цветокоррекция
✨ Улучшение черт лица и контуров
✨ Отбеливание зубов и блеск в глазах
✨ Удаление всех недостатков

📌 Результат: Ты, но в лучшей версии себя
⚡ PixelPie AI сделает тебя звездой глянца!""",

            "art": """🎨 AI Art / Цифровое искусство

Твой портрет в стиле топовых художников Artstation!
🎨 Живописные мазки и текстуры
🎨 Волшебное свечение и частицы
🎨 Яркие, сочные цвета
🎨 Фэнтези атмосфера
🎨 Качество цифрового шедевра

📌 Результат: Арт для NFT или принта на холсте
🎨 PixelPie AI превратит фото в произведение искусства!""",

            "cinema": """🎬 Кино / Hollywood Blockbuster

Ты — главный герой блокбастера!
🎬 Кинематографическая цветокоррекция
🎬 Драматичный свет как у Нолана
🎬 Эффект дорогой камеры
🎬 Атмосфера экшн-фильма
🎬 Постер качества IMAX

📌 Результат: Кадр из фильма с бюджетом $200M
🎥 PixelPie AI сделает тебя звездой Голливуда!""",

            "portrait": """🖼️ Портрет / Fine Art Photography

Психологический портрет уровня National Geographic
📸 Глубина и характер в каждой детали
📸 Свет Рембрандта для объема
📸 Эмоциональная подача
📸 Музейное качество
📸 Вневременная классика

📌 Результат: Портрет для галереи или выставки
📸 PixelPie AI раскроет твою душу в кадре!""",

            "fantasy": """⚡ Киберпанк / Blade Runner 2049

Добро пожаловать в 2077 год!
⚡ Неоновая подсветка розовый/синий
⚡ Киберимпланты и аугментации
⚡ Отражения дождливого мегаполиса
⚡ Голографические эффекты
⚡ Атмосфера дистопии

📌 Результат: Ты — житель Night City
🚀 PixelPie AI отправит тебя в киберпанк-будущее!""",

            "lego": """🧱 LEGO / Официальная минифигурка

Стань коллекционной LEGO фигуркой!
🧱 Точные пропорции минифигурки
🧱 Фирменный блеск пластика
🧱 Детализация как у оригинала
🧱 Подвижные части тела
🧱 Качество официального продукта

📌 Результат: Эксклюзивная фигурка LEGO
🧱 PixelPie AI создаст твою игрушечную версию!"""
        }

        return descriptions.get(style, "Описание недоступно")

    def get_aspect_ratio_keyboard(self, style_key: str) -> List[List[Dict[str, str]]]:
        keyboard = []

        # Первый ряд - вертикальные форматы
        keyboard.append([
            {"text": "📱 9:16", "callback_data": f"transform_ratio:{style_key}:9:16"},
            {"text": "🖼️ 3:4", "callback_data": f"transform_ratio:{style_key}:3:4"}
        ])

        # Второй ряд - квадрат
        keyboard.append([
            {"text": "⬜ 1:1", "callback_data": f"transform_ratio:{style_key}:1:1"}
        ])

        # Третий ряд - горизонтальные форматы
        keyboard.append([
            {"text": "📺 4:3", "callback_data": f"transform_ratio:{style_key}:4:3"},
            {"text": "🖥️ 16:9", "callback_data": f"transform_ratio:{style_key}:16:9"}
        ])

        keyboard.append([{"text": "❌ Отменить", "callback_data": "transform_cancel"}])

        return keyboard

    def get_resolution_keyboard(self, style_key: str, aspect_ratio: str) -> List[List[Dict[str, str]]]:
        keyboard = []
        row = []
        for res_key in self.resolutions:
            button_data = {
                "text": f"{res_key}",
                "callback_data": f"transform_resolution:{style_key}:{aspect_ratio}:{res_key}"
            }
            row.append(button_data)

        if row:
            keyboard.append(row)

        keyboard.append([{"text": "❌ Отменить", "callback_data": "transform_cancel"}])

        return keyboard

    def get_aspect_ratio_description(self) -> str:
        return """
📐 Выберите формат изображения:

📱 **9:16** — Вертикальный
Идеально для Stories, Reels, TikTok

🖼️ **3:4** — Портрет
Классика для фото, удобно для печати

⬜ **1:1** — Квадрат
Instagram посты, аватарки

📺 **4:3** — Стандартный
Универсальный формат для всего

🖥️ **16:9** — Широкоэкранный
YouTube, обложки, баннеры

Выберите подходящий формат для вашего шедевра! ✨
"""
