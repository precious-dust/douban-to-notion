import argparse
import logging
import yaml
import sys
import os
from pathlib import Path

# Ensure project root is on sys.path so `python src/main.py` can import `src.*`
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.douban import DoubanScraper
from src.notion import NotionClient
from src.sync import Syncer, Scheduler
from src.utils.logger import setup_logger, get_logger

logger = None


def load_config(config_path: str = "config/config.yaml") -> dict:
    import logging
    logger = logging.getLogger(__name__)
    """加载配置文件，支持环境变量覆盖"""
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # 环境变量覆盖配置（用于 GitHub Actions 等场景）
        env_mappings = {
            'DOUBAN_COOKIE': ('douban', 'cookie'),
            'DOUBAN_USER_ID': ('douban', 'user_id'),
            'NOTION_API_TOKEN': ('notion', 'api_token'),
            'NOTION_DATABASE_ID': ('notion', 'database_id'),
            'IMGUR_CLIENT_ID': ('storage', 'imgur', 'client_id'),
        }

        for env_key, path in env_mappings.items():
            env_value = os.environ.get(env_key)
            if env_value:
                target = config
                for segment in path[:-1]:
                    if segment not in target or not isinstance(target[segment], dict):
                        target[segment] = {}
                    target = target[segment]
                target[path[-1]] = env_value
                logger.info(f"从环境变量读取配置: {env_key}")
        
        logger.info(f"配置加载成功: {config_path}")
        return config
    except FileNotFoundError:
        logger.error(f"配置文件不存在: {config_path}")
        sys.exit(1)
    except yaml.YAMLError as e:
        logger.error(f"配置文件格式错误: {e}")
        sys.exit(1)


def validate_config(config: dict) -> bool:
    """验证配置"""
    # 检查豆瓣配置
    if not config.get("douban", {}).get("cookie"):
        logger.error("缺少豆瓣Cookie配置")
        return False
    
    if not config.get("douban", {}).get("user_id"):
        logger.error("缺少豆瓣用户ID配置")
        return False
    
    # 检查Notion配置
    if not config.get("notion", {}).get("api_token"):
        logger.error("缺少Notion API Token配置")
        return False
    
    if not config.get("notion", {}).get("database_id"):
        logger.error("缺少Notion Database ID配置")
        return False
    
    logger.info("配置验证成功")
    return True


def main():
    global logger
    
    parser = argparse.ArgumentParser(
        description="豆瓣观影记录同步到Notion"
    )
    
    parser.add_argument(
        "--config",
        type=str,
        default="config/config.yaml",
        help="配置文件路径"
    )
    
    parser.add_argument(
        "--sync-now",
        action="store_true",
        help="立即执行一次同步"
    )
    
    parser.add_argument(
        "--auto",
        action="store_true",
        help="启动自动定时同步"
    )
    
    parser.add_argument(
        "--with-details",
        action="store_true",
        help="同步时获取电影详细信息"
    )
    
    args = parser.parse_args()
    
    # 加载配置
    config = load_config(args.config)
    
    # 初始化日志
    logger = setup_logger(config)
    logger.info("=== 豆瓣到Notion同步工具 ===")
    logger.info(f"配置文件: {args.config}")
    
    # 验证配置
    if not validate_config(config):
        sys.exit(1)
    
    try:
        # 初始化豆瓣爬虫
        logger.info("初始化豆瓣爬虫...")
        douban_config = config.get("douban", {})
        douban_scraper = DoubanScraper(
            cookie=douban_config.get("cookie"),
            user_id=douban_config.get("user_id"),
            use_selenium=douban_config.get('use_selenium', False),
            selenium_options=douban_config.get('selenium', {})
        )
        logger.info("豆瓣爬虫初始化完成")
        
        # 初始化Notion客户端
        logger.info("初始化Notion客户端...")
        notion_config = config.get("notion", {})
        notion_client = NotionClient(
            api_token=notion_config.get("api_token"),
            database_id=notion_config.get("database_id")
        )
        # 如果配置了 storage（例如 imgur），传入 NotionClient
        storage_cfg = config.get('storage')
        if storage_cfg:
            try:
                notion_client.configure_storage(storage_cfg)
            except Exception:
                logger.warning("配置 storage 时出错，继续但不启用上传功能")
        logger.info("Notion客户端初始化完成")
        
        # 初始化同步器
        syncer = Syncer(douban_scraper, notion_client, config)
        logger.info("同步器初始化完成")
        
        # 执行同步或启动定时任务
        if args.sync_now:
            logger.info("开始手动同步...")
            if args.with_details:
                stats = syncer.sync_with_details(fetch_details=True)
            else:
                stats = syncer.sync()
            
            logger.info(f"同步结果: {stats}")
            
            # 如果指定了--auto，则继续启动定时同步
            if args.auto:
                logger.info("启动定时同步...")
                scheduler = Scheduler(
                    interval_minutes=config.get("sync", {}).get("interval_minutes", 60)
                )
                
                if args.with_details:
                    scheduler.schedule_sync(lambda: syncer.sync_with_details(fetch_details=True))
                else:
                    scheduler.schedule_sync(syncer.sync)
                
                scheduler.run()
        
        elif args.auto:
            logger.info("启动定时同步...")
            scheduler = Scheduler(
                interval_minutes=config.get("sync", {}).get("interval_minutes", 60)
            )
            
            if args.with_details:
                scheduler.schedule_sync(lambda: syncer.sync_with_details(fetch_details=True))
            else:
                scheduler.schedule_sync(syncer.sync)
            
            scheduler.run()
        
        else:
            # 默认立即执行一次同步
            logger.info("执行默认同步...")
            if args.with_details:
                stats = syncer.sync_with_details(fetch_details=True)
            else:
                stats = syncer.sync()
            
            logger.info(f"同步结果: {stats}")
    except Exception as e:
        logger.error(f"发生错误: {e}", exc_info=True)
        sys.exit(1)
    finally:
        # 清理可能的 Selenium 驱动
        try:
            douban_scraper.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
