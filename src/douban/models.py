from dataclasses import dataclass, asdict
from typing import Optional
from datetime import datetime


@dataclass
class Movie:
    """电影数据模型"""
    title: str
    douban_id: str
    rating: Optional[float] = None
    my_rating: Optional[int] = None
    watch_date: Optional[str] = None
    comment: Optional[str] = None
    url: Optional[str] = None
    cover_url: Optional[str] = None
    genres: Optional[list] = None
    release_year: Optional[int] = None
    directors: Optional[list] = None
    writers: Optional[list] = None
    actors: Optional[list] = None
    duration: Optional[int] = None
    
    def to_dict(self):
        """转换为字典"""
        data = asdict(self)
        return {k: v for k, v in data.items() if v is not None}
    
    def __hash__(self):
        return hash(self.douban_id)
    
    def __eq__(self, other):
        if isinstance(other, Movie):
            return self.douban_id == other.douban_id
        return False
