import re
import requests
from bs4 import BeautifulSoup
from typing import List
from urllib.parse import urljoin
import time
import random
from .models import Movie
from ..utils.logger import get_logger
import urllib.parse

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager
except Exception:
    webdriver = None

logger = get_logger("douban.scraper")


class DoubanScraper:
    """豆瓣爬虫 - 支持 requests 和可选的 Selenium 回退"""

    BASE_URL = "https://movie.douban.com"

    def __init__(self, cookie: str, user_id: str, use_selenium: bool = False, selenium_options: dict = None):
        self.cookie = cookie
        self.user_id = user_id
        self.session = requests.Session()
        self.use_selenium = use_selenium
        self.selenium_options = selenium_options or {}
        self.selenium_driver = None

        if self.use_selenium:
            self._setup_session()  # 始终先初始化 requests session（确保 Cookie 可用）
            self._setup_selenium()
        else:
            self._setup_session()

    def _setup_session(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Referer': 'https://www.douban.com/',
        }
        self.session.headers.update(headers)
        cookie_map = self._parse_cookie(self.cookie)
        if cookie_map:
            cookie_header = '; '.join(f'{k}={v}' for k, v in cookie_map.items())
            self.session.headers['Cookie'] = cookie_header
            jar = requests.cookies.RequestsCookieJar()
            for name, value in cookie_map.items():
                jar.set(name, value, domain='.douban.com', path='/')
            self.session.cookies = jar

    @staticmethod
    def _parse_cookie(cookie_str: str) -> dict:
        cookies = {}
        if cookie_str:
            for item in cookie_str.split(';'):
                item = item.strip()
                if '=' in item:
                    k, v = item.split('=', 1)
                    cookies[k.strip()] = v.strip()
        return cookies

    def _setup_selenium(self):
        if webdriver is None:
            raise RuntimeError("Selenium 或 webdriver-manager 未安装")
        options = Options()
        if self.selenium_options.get('headless', True):
            # Use Chrome headless mode compatible with current browser
            options.add_argument('--headless')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--lang=zh-CN')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option('excludeSwitches', ['enable-automation'])
        options.add_experimental_option('useAutomationExtension', False)

        ua = self.selenium_options.get('user_agent') or self.session.headers.get('User-Agent')
        if ua:
            options.add_argument(f'--user-agent={ua}')
        driver_path = ChromeDriverManager().install()
        service = Service(driver_path)
        self.selenium_driver = webdriver.Chrome(service=service, options=options)
        try:
            self.selenium_driver.get('https://movie.douban.com/')
            time.sleep(self.selenium_options.get('wait', 2))
            cookie_map = self._parse_cookie(self.cookie)
            for k, v in cookie_map.items():
                try:
                    self.selenium_driver.add_cookie({
                        'name': k,
                        'value': v,
                        'domain': '.douban.com',
                        'path': '/',
                    })
                except Exception:
                    continue
            self.selenium_driver.refresh()
            time.sleep(self.selenium_options.get('wait', 2))
        except Exception:
            if self.selenium_driver:
                try:
                    self.selenium_driver.quit()
                except Exception:
                    pass
            self.selenium_driver = None
            logger.warning("Selenium 初始化失败，回退到 requests")

    def _get(self, url: str, params: dict = None, timeout: int = 10):
        full_url = url
        if params:
            qs = urllib.parse.urlencode(params)
            connector = '&' if '?' in url else '?'
            full_url = f"{url}{connector}{qs}"

        if self.use_selenium and self.selenium_driver:
            try:
                self.selenium_driver.get(full_url)
                time.sleep(self.selenium_options.get('wait', 1.5))
                class _R:
                    pass
                r = _R()
                r.text = self.selenium_driver.page_source
                r.status_code = 200
                r.url = self.selenium_driver.current_url
                return r
            except Exception as e:
                logger.debug(f"Selenium 请求失败: {e}")

        response = self.session.get(url, params=params, timeout=timeout)
        if self._is_blocked_response(response.text, response.url):
            logger.warning(f"豆瓣请求可能被拦截: {response.url}")
            if self.use_selenium and webdriver is not None:
                if not self.selenium_driver:
                    self._setup_selenium()
                if self.selenium_driver:
                    try:
                        self.selenium_driver.get(full_url)
                        time.sleep(self.selenium_options.get('wait', 1.5))
                        class _R:
                            pass
                        r = _R()
                        r.text = self.selenium_driver.page_source
                        r.status_code = 200
                        r.url = self.selenium_driver.current_url
                        return r
                    except Exception as e:
                        logger.debug(f"Selenium 重试失败: {e}")
        return response

    def _is_blocked_response(self, text: str, url: str) -> bool:
        if not text:
            return False
        blocked_signals = [
            'misc/sorry',
            'sec.douban.com',
            '登录豆瓣',
            '登录豆瓣',
            '验证码',
            '请先登录',
            '您正在访问的页面暂时无法打开',
        ]
        if any(token in url for token in ['misc/sorry', 'sec.douban.com']):
            return True
        return any(signal in text for signal in blocked_signals)

    def close(self):
        if self.selenium_driver:
            try:
                self.selenium_driver.quit()
            except Exception:
                pass

    def validate_cookie(self) -> bool:
        """验证 Cookie 是否有效"""
        try:
            # 访问个人主页检查是否登录
            url = f"{self.BASE_URL}/people/{self.user_id}/"
            response = self.session.get(url, timeout=10)
            
            # 检查是否被重定向到登录页
            if 'login' in response.url.lower():
                logger.warning("Cookie 已过期，请重新获取")
                return False
            
            # 检查页面内容
            if '请先登录' in response.text or '登录豆瓣' in response.text:
                logger.warning("Cookie 无效，请重新获取")
                return False
            
            logger.info("Cookie 验证通过")
            return True
        except Exception as e:
            logger.error(f"Cookie 验证失败: {e}")
            return False

    def _random_delay(self, min_sec: float = 1.0, max_sec: float = 3.0):
        """随机延迟，避免触发反爬"""
        delay = random.uniform(min_sec, max_sec)
        time.sleep(delay)

    def _get_with_retry(self, url: str, params: dict = None, timeout: int = 10, max_retries: int = 3) -> requests.Response:
        """带重试机制的请求"""
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                # 随机延迟
                if attempt > 0:
                    delay = (2 ** attempt) + random.uniform(1, 3)  # 指数退避
                    logger.info(f"第 {attempt + 1} 次重试，等待 {delay:.1f} 秒...")
                    time.sleep(delay)
                else:
                    self._random_delay()
                
                response = self._get(url, params=params, timeout=timeout)
                
                # 检查是否被反爬
                if self._is_blocked_response(response.text, response.url):
                    logger.warning(f"请求被反爬拦截 (尝试 {attempt + 1}/{max_retries})")
                    continue
                
                return response
                
            except Exception as e:
                last_exception = e
                logger.warning(f"请求失败 (尝试 {attempt + 1}/{max_retries}): {e}")
        
        raise last_exception or Exception("请求失败，已达最大重试次数")

    def get_watched_movies(self, max_pages: int = None) -> List[Movie]:
        logger.info(f"开始爬取用户 {self.user_id} 的已看电影")
        
        # 验证 Cookie
        if not self.validate_cookie():
            logger.error("Cookie 无效，无法继续同步")
            return []
        
        movies = []
        page = 0
        while True:
            if max_pages and page >= max_pages:
                break
            try:
                url = f"{self.BASE_URL}/people/{self.user_id}/collect"
                params = {"start": page * 15, "sort": "time"}
                logger.debug(f"正在爬取第 {page + 1} 页")
                
                # 使用带重试的请求
                response = self._get_with_retry(url, params=params, timeout=15)
                
                if hasattr(response, 'status_code') and response.status_code >= 400:
                    raise Exception(f"请求失败, status={response.status_code}")
                page_movies = self._parse_movie_list(response.text)
                if not page_movies:
                    logger.info("没有更多电影了")
                    break
                movies.extend(page_movies)
                logger.info(f"已获取 {len(movies)} 部电影")
                page += 1
                
                # 页面间随机延迟
                self._random_delay(1.5, 3.0)
                
            except Exception as e:
                logger.error(f"爬取第 {page + 1} 页时出错: {e}")
                break
        logger.info(f"总共获取 {len(movies)} 部电影")
        return movies

    def _parse_movie_list(self, html: str) -> List[Movie]:
        movies = []
        try:
            soup = BeautifulSoup(html, 'html.parser')
            items = soup.find_all('div', class_='item')
            for item in items:
                try:
                    m = self._parse_movie_item(item)
                    if m:
                        movies.append(m)
                except Exception as e:
                    logger.debug(f"解析电影项目出错: {e}")
                    continue
        except Exception as e:
            logger.error(f"解析HTML出错: {e}")
        return movies

    def _parse_movie_item(self, item) -> Movie:
        title_elem = item.find('li', class_='title') or item.find('span', class_='title')
        if not title_elem:
            return None
        em = title_elem.find('em')
        title = em.get_text(strip=True) if em else title_elem.get_text(strip=True)
        link = item.find('a', class_='nbg') or item.find('a')
        url = link.get('href', '') if link else ''
        douban_id = url.rstrip('/').split('/')[-1] if url else ''
        if not douban_id:
            return None
        rating = None
        r_elem = item.find('span', class_='rating_nums')
        if r_elem:
            try:
                rating = float(r_elem.get_text(strip=True))
            except ValueError:
                pass
        my_rating = None
        mr = item.find('span', class_='my_rating')
        if mr:
            try:
                my_rating = int(mr.get('title', '0'))
            except Exception:
                pass
        # 备用：豆瓣新版用 rating{n}-t 的 CSS class 表示个人评分
        if my_rating is None:
            for star in range(1, 6):
                star_elem = item.find('span', class_=f'rating{star}-t')
                if star_elem:
                    my_rating = star
                    break
        watch_date = None
        de = item.find('span', class_='date')
        if de:
            watch_date = de.get_text(strip=True)
        comment = None
        ce = item.find('span', class_='comment')
        if ce:
            comment = ce.get_text(strip=True)
        cover_url = None
        img = item.find('img')
        if img:
            cover_url = img.get('src', '')
            if cover_url:
                cover_url = urljoin(self.BASE_URL, cover_url)
        return Movie(title=title, douban_id=douban_id, rating=rating, my_rating=my_rating,
                     watch_date=watch_date, comment=comment, url=url, cover_url=cover_url)

    def get_movie_details(self, movie_id: str) -> Movie:
        try:
            url = f"{self.BASE_URL}/subject/{movie_id}/"
            response = self._get_with_retry(url, timeout=15)
            if hasattr(response, 'status_code') and response.status_code >= 400:
                raise Exception(f"请求详情失败, status={response.status_code}")
            return self._parse_movie_details(response.text, movie_id, url)
        except Exception as e:
            logger.error(f"获取电影详情失败 (ID: {movie_id}): {e}")
            return None

    def _parse_movie_details(self, html: str, movie_id: str, url: str) -> Movie:
        soup = BeautifulSoup(html, 'html.parser')
        title_elem = soup.find('span', {'property': 'v:itemreviewed'})
        title = title_elem.get_text(strip=True) if title_elem else ''
        rating = None
        r = soup.find('strong', {'property': 'v:average'})
        if r:
            try:
                rating = float(r.get_text(strip=True))
            except Exception:
                pass
        directors = [a.get_text(strip=True) for a in soup.select('a[rel="v:directedBy"]')]
        actors = [a.get_text(strip=True) for a in soup.select('a[rel="v:starring"]')]
        genres = [span.get_text(strip=True) for span in soup.select('span[property="v:genre"]')]

        # 备用解析：豆瓣旧版页面会在 info 区块内使用 label + 链接形式
        info = soup.find('div', id='info')
        if info:
            for label in info.find_all('span', class_='pl'):
                label_text = label.get_text(strip=True).rstrip(':').strip()
                sibling = label.next_sibling
                while sibling:
                    if sibling.name == 'a':
                        value = sibling.get_text(strip=True)
                        if label_text == '导演' and value:
                            directors.append(value)
                        elif label_text in ('主演', '表演', '演员') and value:
                            actors.append(value)
                        elif label_text in ('类型', 'genre') and value:
                            genres.append(value)
                    elif sibling.name in ('span', 'div') and label_text == '类型':
                        genres.extend([g.get_text(strip=True) for g in sibling.select('span[property="v:genre"]')])
                    sibling = sibling.next_sibling

        # 去重并保留顺序
        directors = list(dict.fromkeys([d for d in directors if d]))
        actors = list(dict.fromkeys([a for a in actors if a]))
        genres = list(dict.fromkeys([g for g in genres if g]))

        year = None
        ye = soup.find('span', {'property': 'v:initialReleaseDate'})
        if ye:
            ys = ye.get_text(strip=True)
            try:
                year = int(ys[:4])
            except Exception:
                pass

        duration = None
        du = soup.find('span', {'property': 'v:runtime'})
        if du:
            ds = du.get_text(strip=True)
            try:
                duration = int(re.search(r'(\d+)', ds).group(1))
            except Exception:
                pass

        cover_url = None
        mainpic = soup.find('div', id='mainpic')
        if mainpic:
            img = mainpic.find('img')
            if img:
                cover_url = img.get('src', '')
                if cover_url:
                    cover_url = urljoin(self.BASE_URL, cover_url)

        # 不从详情页提取个人评分（豆瓣个人评分不在详情页HTML中，
        # 正则匹配容易误匹配豆瓣评分，所以保留列表页的评分即可）
        my_rating = None  # 个人评分仅从列表页的 rating{n}-t class 提取

        return Movie(title=title, douban_id=movie_id, rating=rating, my_rating=my_rating, url=url, cover_url=cover_url,
                     genres=genres if genres else None, release_year=year, directors=directors if directors else None,
                     actors=actors if actors else None, duration=duration)

    def _extract_my_rating(self, soup: BeautifulSoup):
        """从电影详情页中尝试解析我的评分。"""
        text = " ".join(soup.stripped_strings)
        if not text:
            return None

        patterns = [
            r'我(?:给这部电影打了|的评分|评分)[:：]?\s*([0-9])',
            r'你(?:给这部电影打了|的评分|已评分)[:：]?\s*([0-9])',
            r'评分[:：]?\s*([0-9])'
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    continue
        return None
