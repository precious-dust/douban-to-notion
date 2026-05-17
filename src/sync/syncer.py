from typing import List, Set
from ..douban import DoubanScraper, Movie
from ..notion import NotionClient, NotionMovie
from ..utils.logger import get_logger
import json
from pathlib import Path

logger = get_logger("sync.syncer")


class Syncer:
    """豆瓣到Notion的同步器"""
    
    def __init__(self, douban_scraper: DoubanScraper, notion_client: NotionClient, config: dict):
        """
        初始化同步器
        
        Args:
            douban_scraper: 豆瓣爬虫
            notion_client: Notion客户端
            config: 配置字典
        """
        self.douban_scraper = douban_scraper
        self.notion_client = notion_client
        self.config = config
        self.sync_comments = config.get("sync", {}).get("sync_comments", True)
        self.overwrite_existing = config.get("notion", {}).get("overwrite_existing", True)
        self.max_items = config.get("sync", {}).get("max_items", -1)
        self.incremental = config.get("sync", {}).get("incremental", True)  # 默认增量同步
        self.progress_file = Path("logs/progress.json")
    
    def _get_existing_movie_ids(self) -> Set[str]:
        """获取 Notion 中已存在的所有电影豆瓣 ID"""
        logger.info("获取 Notion 中已存在的电影...")
        existing_ids = set()
        
        try:
            # 查询所有电影
            results = self.notion_client.query_database()
            
            for page in results:
                # 从豆瓣链接中提取 ID
                props = page.get("properties", {})
                url_prop = props.get("豆瓣链接", {})
                url = url_prop.get("url", "")
                
                if url:
                    # 从 URL 提取 ID: https://movie.douban.com/subject/123456/
                    parts = url.rstrip("/").split("/")
                    if parts:
                        movie_id = parts[-1]
                        existing_ids.add(movie_id)
            
            logger.info(f"Notion 中已存在 {len(existing_ids)} 部电影")
            
        except Exception as e:
            logger.warning(f"获取已存在电影失败: {e}")
        
        return existing_ids
    
    def _save_progress(self, synced_ids: List[str], stats: dict):
        """保存同步进度"""
        try:
            progress = {
                "last_sync": stats,
                "synced_ids": synced_ids[-1000:]  # 只保留最近 1000 个
            }
            self.progress_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存进度失败: {e}")
    
    def _load_progress(self) -> List[str]:
        """加载上次同步进度"""
        try:
            if self.progress_file.exists():
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    progress = json.load(f)
                    return progress.get("synced_ids", [])
        except Exception as e:
            logger.warning(f"加载进度失败: {e}")
        return []
    
    def sync(self) -> dict:
        """
        执行同步
        
        Returns:
            同步统计信息
        """
        logger.info("开始同步")
        
        stats = {
            "total": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0
        }
        
        synced_ids = []
        
        try:
            # 获取豆瓣电影列表
            douban_movies = self.douban_scraper.get_watched_movies()
            total_available = len(douban_movies)
            
            # 增量同步：过滤已存在的电影
            if self.incremental:
                existing_ids = self._get_existing_movie_ids()
                original_count = len(douban_movies)
                douban_movies = [m for m in douban_movies if m.douban_id not in existing_ids]
                logger.info(f"增量同步：过滤掉 {original_count - len(douban_movies)} 部已存在的电影")
            
            # 限制同步数量
            if self.max_items > 0:
                douban_movies = douban_movies[:self.max_items]
            stats["total"] = len(douban_movies)
            logger.info(f"从豆瓣获取 {total_available} 部电影，本次同步 {stats['total']} 部")
            
            # 同步每部电影
            for i, movie in enumerate(douban_movies):
                try:
                    result = self._sync_movie(movie)
                    if result == "created":
                        stats["created"] += 1
                        synced_ids.append(movie.douban_id)
                    elif result == "updated":
                        stats["updated"] += 1
                    elif result == "skipped":
                        stats["skipped"] += 1
                    
                    # 每同步 50 部保存一次进度
                    if (i + 1) % 50 == 0:
                        self._save_progress(synced_ids, stats)
                        
                except Exception as e:
                    logger.error(f"同步电影失败: {movie.title} - {e}")
                    stats["failed"] += 1
            
            # 保存最终进度
            self._save_progress(synced_ids, stats)
            
            logger.info(
                f"同步完成！创建: {stats['created']}, 更新: {stats['updated']}, "
                f"跳过: {stats['skipped']}, 失败: {stats['failed']}"
            )
            
        except Exception as e:
            logger.error(f"同步过程中出错: {e}")
            # 即使出错也保存进度
            if synced_ids:
                self._save_progress(synced_ids, stats)
        
        return stats
    
    def _sync_movie(self, movie: Movie) -> str:
        """
        同步单部电影
        
        Args:
            movie: Movie对象
        
        Returns:
            操作类型: "created", "updated", "skipped", "failed"
        """
        # 获取电影在Notion中是否已存在（通过标题或豆瓣链接避免重复）
        existing_page = self.notion_client.get_page_by_title_or_url(movie.title, movie.url)
        
        # 构建Notion属性
        movie_data = movie.to_dict()
        properties = NotionMovie.build_properties(movie_data)
        
        if existing_page:
            if self.overwrite_existing:
                # 更新现有页面
                try:
                    self.notion_client.update_page(existing_page["id"], properties)
                    logger.debug(f"更新电影: {movie.title}")
                    return "updated"
                except Exception as e:
                    logger.error(f"更新电影失败: {movie.title} - {e}")
                    return "failed"
            else:
                logger.debug(f"电影已存在，跳过: {movie.title}")
                return "skipped"
        else:
            # 创建新页面
            try:
                self.notion_client.create_page(properties)
                logger.debug(f"创建电影: {movie.title}")
                return "created"
            except Exception as e:
                logger.error(f"创建电影失败: {movie.title} - {e}")
                return "failed"
    
    def sync_with_details(self, fetch_details: bool = True) -> dict:
        """
        带详细信息的同步
        
        Args:
            fetch_details: 是否获取电影详情
        
        Returns:
            同步统计信息
        """
        logger.info("开始带详情的同步")
        
        stats = {
            "total": 0,
            "created": 0,
            "updated": 0,
            "skipped": 0,
            "failed": 0
        }
        
        synced_ids = []
        
        try:
            # 获取豆瓣电影列表
            douban_movies = self.douban_scraper.get_watched_movies()
            total_available = len(douban_movies)
            
            # 增量同步：过滤已存在的电影
            if self.incremental:
                existing_ids = self._get_existing_movie_ids()
                original_count = len(douban_movies)
                douban_movies = [m for m in douban_movies if m.douban_id not in existing_ids]
                logger.info(f"增量同步：过滤掉 {original_count - len(douban_movies)} 部已存在的电影")
            
            # 限制同步数量
            if self.max_items > 0:
                douban_movies = douban_movies[:self.max_items]
            stats["total"] = len(douban_movies)
            logger.info(f"从豆瓣获取 {total_available} 部电影，本次同步 {stats['total']} 部（含详情）")
            
            for i, movie in enumerate(douban_movies):
                try:
                    # 获取详细信息
                    if fetch_details and movie.douban_id:
                        details = self.douban_scraper.get_movie_details(movie.douban_id)
                        if details:
                            # 合并数据
                            movie = self._merge_movie_data(movie, details)
                    
                    result = self._sync_movie(movie)
                    if result == "created":
                        stats["created"] += 1
                        synced_ids.append(movie.douban_id)
                    elif result == "updated":
                        stats["updated"] += 1
                    elif result == "skipped":
                        stats["skipped"] += 1
                    
                    # 每同步 50 部保存一次进度
                    if (i + 1) % 50 == 0:
                        self._save_progress(synced_ids, stats)
                
                except Exception as e:
                    logger.error(f"同步电影失败: {movie.title} - {e}")
                    stats["failed"] += 1
            
            # 保存最终进度
            self._save_progress(synced_ids, stats)
            
            logger.info(
                f"同步完成！创建: {stats['created']}, 更新: {stats['updated']}, "
                f"跳过: {stats['skipped']}, 失败: {stats['failed']}"
            )
        
        except Exception as e:
            logger.error(f"同步过程中出错: {e}")
            # 即使出错也保存进度
            if synced_ids:
                self._save_progress(synced_ids, stats)
        
        return stats
    
    @staticmethod
    def _merge_movie_data(movie1: Movie, movie2: Movie) -> Movie:
        """合并两个Movie对象的数据（movie2的信息优先级更高）"""
        merged_data = movie1.to_dict()
        movie2_data = movie2.to_dict()
        
        merged_data.update({k: v for k, v in movie2_data.items() if v is not None})
        
        return Movie(
            title=merged_data.get('title', movie1.title),
            douban_id=merged_data.get('douban_id', movie1.douban_id),
            rating=merged_data.get('rating'),
            my_rating=merged_data.get('my_rating'),
            watch_date=merged_data.get('watch_date'),
            comment=merged_data.get('comment'),
            url=merged_data.get('url'),
            cover_url=merged_data.get('cover_url'),
            genres=merged_data.get('genres'),
            release_year=merged_data.get('release_year'),
            directors=merged_data.get('directors'),
            writers=merged_data.get('writers'),
            actors=merged_data.get('actors'),
            duration=merged_data.get('duration')
        )
