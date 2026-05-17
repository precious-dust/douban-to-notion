from typing import Optional


class NotionMovie:
    """Notion电影数据模型 - 用于与Notion API交互"""
    
    def __init__(self, title: str, properties: dict = None):
        self.title = title
        self.properties = properties or {}
    
    def to_notion_page(self) -> dict:
        """转换为Notion页面格式"""
        return {
            "properties": self.properties
        }
    
    @staticmethod
    def build_properties(movie_data: dict) -> dict:
        """构建Notion页面属性
        
        Args:
            movie_data: 电影数据字典
        
        Returns:
            Notion格式的属性字典
        """
        properties = {
            "电影名": {
                "title": [
                    {
                        "text": {
                            "content": movie_data.get('title', 'Unknown')
                        }
                    }
                ]
            }
        }
        
        # 我的评分
        if 'my_rating' in movie_data and movie_data['my_rating']:
            rating_value = int(movie_data['my_rating']) if isinstance(movie_data['my_rating'], (int, float)) else None
            star_name = None
            if rating_value and 1 <= rating_value <= 5:
                star_name = '⭐' * rating_value
            elif rating_value:
                star_name = str(rating_value)
            else:
                star_name = str(movie_data['my_rating'])

            properties["我的评分"] = {
                "select": {
                    "name": star_name
                }
            }
        
        # 豆瓣评分
        if 'rating' in movie_data and movie_data['rating']:
            properties["豆瓣评分"] = {
                "number": float(movie_data['rating'])
            }
        
        # 观看日期
        if 'watch_date' in movie_data and movie_data['watch_date']:
            properties["观看日期"] = {
                "date": {
                    "start": movie_data['watch_date']
                }
            }
        
        # 短评
        if 'comment' in movie_data and movie_data['comment']:
            properties["短评"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": movie_data['comment']
                        }
                    }
                ]
            }
        
        # 豆瓣链接
        if 'url' in movie_data and movie_data['url']:
            properties["豆瓣链接"] = {
                "url": movie_data['url']
            }
        
        # 发行年份
        if 'release_year' in movie_data and movie_data['release_year']:
            properties["发行年份"] = {
                "number": int(movie_data['release_year'])
            }
        
        # 时长
        if 'duration' in movie_data and movie_data['duration']:
            properties["时长"] = {
                "number": int(movie_data['duration'])
            }
        
        # 导演 - 存储为文本
        if 'directors' in movie_data and movie_data['directors']:
            directors_text = ", ".join(movie_data['directors'])
            properties["导演"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": directors_text
                        }
                    }
                ]
            }
        
        # 主演 - 存储为文本（最多5个，超出显示...）
        if 'actors' in movie_data and movie_data['actors']:
            actors_list = movie_data['actors'][:5]
            actors_text = ", ".join(actors_list)
            if len(movie_data['actors']) > 5:
                actors_text += "..."
            properties["主演"] = {
                "rich_text": [
                    {
                        "text": {
                            "content": actors_text
                        }
                    }
                ]
            }
        
        # 类型 - 存储为 multi_select
        if 'genres' in movie_data and movie_data['genres']:
            genres_list = movie_data['genres']
            properties["类型"] = {
                "multi_select": [
                    {"name": g} for g in genres_list
                ]
            }

        # 封面 - 存储为文件（优先使用外部链接）
        if 'cover_url' in movie_data and movie_data['cover_url']:
            cover_url = movie_data['cover_url']
            properties["封面"] = {
                "files": [
                    {
                        "name": f"{movie_data.get('title', 'cover')} 封面",
                        "external": {"url": cover_url}
                    }
                ]
            }
        
        return properties