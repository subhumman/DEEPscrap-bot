import asyncio
import random
import logging
import ujson
from asyncio import Semaphore
from typing import List, Dict, Optional

import aiohttp
from aiohttp_proxy import ProxyConnector
from bs4 import BeautifulSoup

from config import config
from database import init_db, save_parsed_data

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('parser.log', mode='w', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


class MetalParser:

    def __init__(self, max_concurrent_requests: int = 5):
        self.base_url = config.BASE_URL
        self.proxies = config.PROXIES
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'Accept-Language': 'en-US,en;q=0.9,ru;q=0.8',
        }
        self.session: Optional[aiohttp.ClientSession] = None
        self.semaphore = Semaphore(max_concurrent_requests)

    def _get_connector(self) -> Optional[ProxyConnector]:
        """Возвращает коннектор для сессии с прокси."""
        if self.proxies:
            proxy_url = random.choice(self.proxies)
            logger.info(f"Using proxy: {proxy_url}")
            return ProxyConnector.from_url(proxy_url)
        return None

    async def _create_session(self):
        """Создает сессию aiohttp."""
        if self.session and not self.session.closed:
            await self.session.close()
        
        connector = self._get_connector()
        self.session = aiohttp.ClientSession(
            headers=self.headers,
            connector=connector
        )

    async def close_session(self):
        """Закрывает сессию aiohttp."""
        if self.session and not self.session.closed:
            await self.session.close()
            logger.info("Session closed.")

    async def fetch_page(self, url: str, retries: int = 3, delay: int = 5) -> Optional[str]:
        """
        Получает HTML-содержимое страницы с обработкой ошибок и повторными попытками.
        """
        await self._create_session()
        page_url = f"{self.base_url}{url}" if url.startswith('/') else url

        async with self.semaphore:
            for attempt in range(retries):
                try:
                    logger.info(f"Fetching {page_url} (Attempt {attempt + 1}/{retries})")
                    async with self.session.get(page_url, timeout=20) as response:
                        response.raise_for_status()
                        return await response.text(encoding='utf-8', errors='ignore')
                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.warning(f"Error fetching {page_url}: {e}. Retrying in {delay}s...")
                    await asyncio.sleep(delay * (attempt + 1))
            logger.error(f"Failed to fetch {page_url} after {retries} attempts.")
            return None

    async def get_category_links(self) -> List[Dict[str, str]]:
        """
        Получает список ссылок на категории товаров из левого контейнера.
        """
        logger.info("Parsing category links...")
        html = await self.fetch_page("/price")
        if not html:
            logger.error("Could not fetch main page to parse categories.")
            return []

        soup = BeautifulSoup(html, 'lxml')
        left_container = soup.find('nav', id='left-container')
        if not left_container:
            logger.error("Left container not found on main page.")
            return []
        
        categories = []
        for link in left_container.select('ul.tabs a[data-naimenovanie]'):
            name = link.text.strip()
            href = link.get('href')
            if name and href:
                categories.append({'name': name, 'url': href})
        
        logger.info(f"Found {len(categories)} categories.")
        return categories

    def parse_center_container(self, soup: BeautifulSoup) -> Dict:
        """Парсит центральный контейнер для получения фильтров и размеров."""
        center_container = soup.find('nav', id='center-container')
        if not center_container:
            return {}
        
        data = {}
        panes = center_container.find_all('div', class_='pane')
        for pane in panes:
            group_name = pane.find_previous_sibling('h2')
            if group_name:
                group_name = group_name.text.strip()
            else:
                group_name = "default"
            
            sizes = [a.text.strip() for a in pane.find_all('a') if a.text.strip()]
            data[group_name] = sizes
        return data


    def parse_price_table(self, soup: BeautifulSoup) -> List[Dict]:
        """Парсит таблицу с ценами из правого контейнера."""
        price_table = soup.find('table', id='table-price')
        if not price_table or not price_table.find('tbody'):
            return []

        prices = []
        for row in price_table.tbody.find_all('tr'):
            columns = row.find_all('td')
            if not columns or 'tp-tr-hidden' in row.get('class', []):
                continue
            
            # Структура таблицы может меняться, поэтому парсим более гибко
            firm_dop_opener = columns[-1].find('span', class_='firm_dop_opener')
            if firm_dop_opener:
                supplier_info = columns[-2]
            else:
                supplier_info = columns[-1]


            supplier = supplier_info.find('a', class_='firm_link')
            phone = supplier_info.find('a', class_='tel_link')

            price_data = {
                'position': columns[0].text.strip() if len(columns) > 0 else '',
                'spec': columns[1].text.strip() if len(columns) > 1 else '',
                'dimensions': columns[2].text.strip() if len(columns) > 2 else '',
                'price_per_ton': columns[3].text.strip().replace('\xa0', '') if len(columns) > 3 else '',
                'price_per_item': columns[4].text.strip().replace('\xa0', '') if len(columns) > 4 else '',
                'supplier': supplier.text.strip() if supplier else '',
                'phone': phone.text.strip() if phone else '',
                'city': columns[-3].text.strip() if len(columns) > 5 else ''
            }
            prices.append(price_data)
        return prices

    async def parse_all(self):
        """
        Запускает полный процесс парсинга сайта.
        1. Получает все категории.
        2. Для каждой категории парсит страницу с ценами.
        3. Сохраняет результат в базу данных.
        """
        all_data = []
        categories = await self.get_category_links()

        tasks = [self.parse_category_page(cat) for cat in categories]
        results = await asyncio.gather(*tasks)

        for data in results:
            if data:
                all_data.append(data)

        logger.info(f"Total categories parsed: {len(all_data)}")
        
        try:
            save_parsed_data(all_data)
            logger.info(f"Data successfully saved to database")
        except Exception as e:
            logger.error(f"Error saving data to database: {e}")

    async def parse_category_page(self, category: Dict[str, str]) -> Optional[Dict]:
        """Парсит отдельную страницу категории."""
        category_url = category['url']
        html = await self.fetch_page(category_url)
        if not html:
            return None

        soup = BeautifulSoup(html, 'lxml')
        h1 = soup.find('h1', class_='price-h1')

        return {
            'category_name': h1.text.strip() if h1 else category['name'],
            'url': category_url,
            'filters': self.parse_center_container(soup),
            'prices': self.parse_price_table(soup)
        }


async def main():
    """Главная функция для запуска парсера."""
    init_db() # Инициализируем БД перед началом парсинга
    parser = MetalParser(max_concurrent_requests=10)
    try:
        await parser.parse_all()
    finally:
        await parser.close_session()

if __name__ == "__main__":
    if not config.PROXIES:
        logger.warning("No proxies found in config.py. Running without proxies.")
        logger.warning("The site may block your IP address.")


    asyncio.run(main()) 
