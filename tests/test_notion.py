"""
单元测试 - Notion模型
"""

import unittest
from src.notion.models import NotionMovie


class TestNotionMovie(unittest.TestCase):
    """NotionMovie模型测试"""
    
    def test_build_properties_basic(self):
        """测试构建基本属性"""
        movie_data = {
            "title": "测试电影",
            "rating": 8.5,
            "my_rating": 9
        }
        
        properties = NotionMovie.build_properties(movie_data)
        
        self.assertIn("电影名", properties)
        self.assertIn("我的评分", properties)
        self.assertIn("豆瓣评分", properties)
    
    def test_build_properties_full(self):
        """测试构建完整属性"""
        movie_data = {
            "title": "测试电影",
            "rating": 8.5,
            "my_rating": 9,
            "watch_date": "2024-01-15",
            "comment": "很好看！",
            "url": "https://movie.douban.com/subject/12345/",
            "release_year": 2020,
            "duration": 120,
            "directors": ["导演1", "导演2"],
            "genres": ["剧情", "悬疑"]
        }
        
        properties = NotionMovie.build_properties(movie_data)
        
        # 检查所有字段都被正确转换
        self.assertIn("电影名", properties)
        self.assertIn("观看日期", properties)
        self.assertIn("短评", properties)
        self.assertIn("豆瓣链接", properties)
        self.assertIn("发行年份", properties)
        self.assertIn("时长", properties)
        self.assertIn("导演", properties)
        self.assertIn("类型", properties)
    
    def test_build_properties_none_filtering(self):
        """测试None值过滤"""
        movie_data = {
            "title": "测试电影",
            "rating": None,  # 应该被过滤
            "my_rating": 0,  # 0值应该被保留
            "comment": None
        }
        
        properties = NotionMovie.build_properties(movie_data)
        
        # rating和comment因为None应该不在属性中
        self.assertNotIn("豆瓣评分", properties)
        self.assertNotIn("短评", properties)


if __name__ == "__main__":
    unittest.main()
