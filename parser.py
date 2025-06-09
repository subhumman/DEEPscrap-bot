import aiohttp
import asyncio
import random
import logging
from bs4 import BeautifulSoup
from config import config

logger = logging.getLogger(__name__)

class MetalParser:
    def __init__(self):
        self.base_url = config.BASE_URL
        self._services_cache = None
        self._session = None
        self._last_request_time = 0
        self._max_retries = 3
        self._retry_delay = 30  # Увеличиваем задержку между попытками
        logger.info("Parser initialized")

    async def _wait_before_request(self):
        """Ожидание перед запросом для избежания блокировки"""
        current_time = asyncio.get_event_loop().time()
        time_since_last_request = current_time - self._last_request_time
        
        # Минимальная задержка между запросами
        min_delay = 10.0
        # Добавляем случайную задержку
        random_delay = random.uniform(2.0, 5.0)
        
        if time_since_last_request < min_delay:
            wait_time = min_delay - time_since_last_request + random_delay
            logger.debug(f"Waiting {wait_time:.2f} seconds before request")
            await asyncio.sleep(wait_time)
        
        self._last_request_time = asyncio.get_event_loop().time()

    async def fetch_page(self, url=None, retry_count=0):
        """Получение HTML страницы"""
        if not self._session:
            self._session = aiohttp.ClientSession()
        
        try:
            await self._wait_before_request()
            target_url = url or self.base_url
            logger.info(f"Fetching page: {target_url} (attempt {retry_count + 1})")
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache'
            }
            
            async with self._session.get(target_url, headers=headers) as response:
                if response.status == 429:  # Too Many Requests
                    if retry_count < self._max_retries:
                        wait_time = self._retry_delay * (retry_count + 1)
                        logger.warning(f"Received 429 status code, waiting {wait_time} seconds before retry")
                        await asyncio.sleep(wait_time)
                        return await self.fetch_page(url, retry_count + 1)
                    else:
                        logger.error("Max retries reached for 429 error")
                        raise Exception("Too many requests, max retries reached")
                
                response.raise_for_status()
                return await response.text()
        except Exception as e:
            if retry_count < self._max_retries:
                wait_time = self._retry_delay * (retry_count + 1)
                logger.warning(f"Error fetching page (attempt {retry_count + 1}): {str(e)}, retrying in {wait_time} seconds")
                await asyncio.sleep(wait_time)
                return await self.fetch_page(url, retry_count + 1)
            logger.error(f"Error fetching page after {self._max_retries} attempts: {str(e)}")
            raise

    async def parse_services(self):
        """Парсинг списка услуг"""
        try:
            html = await self.fetch_page()
            soup = BeautifulSoup(html, 'html.parser')
            
            # Получаем все ссылки из списка услуг
            services = []
            for link in soup.select('ul.tabs li a'):
                service_name = link.get_text(strip=True)
                service_url = link.get('href', '')
                if service_name and service_url:
                    services.append({
                        'name': service_name,
                        'url': service_url,
                        'code': link.get('data-naimenovanie', '')
                    })
            
            self._services_cache = services
            return services
        except Exception as e:
            logger.error(f"Error parsing services: {str(e)}")
            raise

    async def get_sizes(self, service_code: str) -> list:
        """Получение списка размеров для услуги"""
        try:
            html = await self.fetch_page(f"{self.base_url}/price/{service_code}")
            soup = BeautifulSoup(html, 'html.parser')
            
            sizes = []
            for link in soup.select('div.panes div.pane a'):
                size = link.get_text(strip=True)
                if size:
                    sizes.append(float(size))
            
            return sorted(sizes)
        except Exception as e:
            logger.error(f"Error getting sizes: {str(e)}")
            raise

    def _extract_price(self, price_element) -> float:
        """Извлечение цены из элемента"""
        if not price_element:
            return 0.0
        
        price_text = price_element.get_text(strip=True)
        # Удаляем все символы кроме цифр
        price_str = ''.join(filter(str.isdigit, price_text))
        try:
            return float(price_str)
        except ValueError:
            return 0.0

    async def get_prices(self, service_code: str, size: float = None) -> list:
        """Получение цен для услуги"""
        try:
            url = f"{self.base_url}/price/{service_code}"
            if size:
                url += f"/{size}"
            
            html = await self.fetch_page(url)
            soup = BeautifulSoup(html, 'html.parser')
            
            prices = []
            for row in soup.select('table#table-price tbody tr'):
                # Получаем название и марку
                name = row.select_one('td:nth-child(1)').get_text(strip=True)
                mark = row.select_one('td:nth-child(2)').get_text(strip=True)
                length = row.select_one('td:nth-child(3)').get_text(strip=True)
                
                # Получаем цены
                price1_elem = row.select_one('td.td_cost span.cost')
                price2_elem = row.select_one('td.td_cost2 span.cost2')
                
                # Получаем условия
                condition1 = row.select_one('td.td_cost small.yslovie').get_text(strip=True)
                condition2 = row.select_one('td.td_cost2 small.yslovie2').get_text(strip=True)
                
                # Получаем поставщика
                supplier = row.select_one('td.td_firm_link_and_tel a.firm_link').get_text(strip=True)
                phone = row.select_one('td.td_firm_link_and_tel a.tel_link').get_text(strip=True)
                
                prices.append({
                    'name': name,
                    'mark': mark,
                    'length': length,
                    'price1': self._extract_price(price1_elem),
                    'price2': self._extract_price(price2_elem),
                    'condition1': condition1,
                    'condition2': condition2,
                    'supplier': supplier,
                    'phone': phone
                })
            
            return prices
        except Exception as e:
            logger.error(f"Error getting prices: {str(e)}")
            raise

    async def get_average_price(self, service_code: str, size: float = None) -> float:
        """Получение средней цены для услуги"""
        try:
            prices = await self.get_prices(service_code, size)
            if not prices:
                return 0.0
            
            # Берем минимальные цены из каждой строки
            min_prices = [min(p['price1'], p['price2']) for p in prices if p['price1'] > 0 or p['price2'] > 0]
            return sum(min_prices) / len(min_prices) if min_prices else 0.0
        except Exception as e:
            logger.error(f"Error getting average price: {str(e)}")
            raise

    async def get_cached_services(self):
        """Получение кэшированного списка услуг"""
        if not self._services_cache:
            await self.parse_services()
        return self._services_cache

    async def close(self):
        """Закрытие сессии"""
        if self._session:
            await self._session.close()
            self._session = None 