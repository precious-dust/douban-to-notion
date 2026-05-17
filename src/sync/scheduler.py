import schedule
import time
from typing import Callable
from ..utils.logger import get_logger

logger = get_logger("sync.scheduler")


class Scheduler:
    """定时任务调度器"""
    
    def __init__(self, interval_minutes: int = 60):
        """
        初始化调度器
        
        Args:
            interval_minutes: 同步间隔（分钟）
        """
        self.interval_minutes = interval_minutes
        self.job = None
        self.running = False
    
    def schedule_sync(self, sync_func: Callable):
        """
        调度同步任务
        
        Args:
            sync_func: 同步函数
        """
        self.job = schedule.every(self.interval_minutes).minutes.do(sync_func)
        logger.info(f"已调度同步任务，间隔 {self.interval_minutes} 分钟")
    
    def run(self):
        """运行调度器（阻塞）"""
        if self.job is None:
            logger.error("未调度任何任务，请先调用 schedule_sync()")
            return
        
        self.running = True
        logger.info("调度器已启动，等待下次运行...")
        
        try:
            while self.running:
                schedule.run_pending()
                time.sleep(60)  # 每分钟检查一次
        except KeyboardInterrupt:
            logger.info("调度器已停止")
            self.running = False
    
    def stop(self):
        """停止调度器"""
        self.running = False
        logger.info("停止调度器")
    
    def clear(self):
        """清除所有任务"""
        schedule.clear()
        logger.info("已清除所有任务")
