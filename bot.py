import asyncio
import logging
import sys
import subprocess
import signal
from typing import Optional

from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from handlers import router
from database import init_db

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)

# Глобальные переменные для graceful shutdown
bot: Optional[Bot] = None
dp: Optional[Dispatcher] = None

def run_parser():
    """Запускает парсер как отдельный процесс."""
    logger.info("Starting parser...")
    try:
        # Запускаем парсер с явным указанием кодировки
        process = subprocess.run(
            [sys.executable, 'parser.py'],
            check=True,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore'
        )
        logger.info("Parser finished successfully.")
        logger.info(f"Parser output:\n{process.stdout}")
        if process.stderr:
            logger.error(f"Parser errors:\n{process.stderr}")

    except FileNotFoundError:
        logger.error("parser.py not found. Make sure the parser script is in the root directory.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logger.error(f"Parser script failed with exit code {e.returncode}.")
        logger.error(f"Parser output:\n{e.stdout}")
        logger.error(f"Parser errors:\n{e.stderr}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred while running the parser: {e}")
        sys.exit(1)

async def on_shutdown():
    """Обработчик завершения работы бота."""
    logger.info("Shutting down bot...")
    if bot:
        await bot.session.close()
    if dp:
        await dp.storage.close()

async def main():
    """Главная функция для запуска бота."""
    global bot, dp
    
    # Инициализируем базу данных
    init_db()

    # Создаем объекты бота и диспетчера
    bot = Bot(token=config.BOT_TOKEN, parse_mode="HTML")
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Включаем роутер
    dp.include_router(router)

    # Регистрируем обработчик завершения
    dp.shutdown.register(on_shutdown)

    logger.info("Starting bot...")
    await bot.delete_webhook(drop_pending_updates=True)
    
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error while polling: {e}")
        await on_shutdown()
        sys.exit(1)

def handle_signal(signum, frame):
    """Обработчик сигналов для graceful shutdown."""
    logger.info(f"Received signal {signum}")
    if bot and dp:
        asyncio.create_task(on_shutdown())
    sys.exit(0)

if __name__ == '__main__':
    # Регистрируем обработчики сигналов
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Сначала запускаем парсер для обновления данных
    run_parser()
    
    # Затем запускаем бота
    asyncio.run(main()) 