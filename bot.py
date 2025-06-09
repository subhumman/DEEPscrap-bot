import asyncio
import logging
import signal
import sys
import traceback
from aiogram import Bot, Dispatcher
from config import config
from handlers import router
from parser import MetalParser

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log')
    ]
)

logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
try:
    bot = Bot(token=config.BOT_TOKEN)
    dp = Dispatcher()
except Exception as e:
    logger.error(f"Failed to initialize bot: {str(e)}")
    sys.exit(1)

# Регистрация роутера
dp.include_router(router)

# Инициализация парсера
parser = MetalParser()

async def on_shutdown():
    """
    Корректное завершение работы бота
    """
    logger.info("Shutting down...")
    try:
        await parser.close()
    except Exception as e:
        logger.error(f"Error closing parser: {str(e)}")
    
    try:
        await bot.session.close()
    except Exception as e:
        logger.error(f"Error closing bot session: {str(e)}")

async def main():
    """
    главная функция
    """
    try:
        logger.info("Starting bot...")
        # Запуск бота
        await dp.start_polling(bot, skip_updates=True)
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        # Закрытие сессии бота
        await on_shutdown()

if __name__ == "__main__":
    try:
        logger.info("Bot initialization started")
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    finally:
        logger.info("Bot stopped") 