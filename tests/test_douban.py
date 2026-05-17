"""
单元测试 - 豆瓣爬虫
"""

import unittest
from src.douban.models import Movie


class TestMovie(unittest.TestCase):
    """Movie模型测试"""
    
    def test_movie_creation(self):
        """测试电影对象创建"""
        movie = Movie(
            title="测试电影",
            douban_id="12345",
            rating=8.5,
            my_rating=9
        )
        
        self.assertEqual(movie.title, "测试电影")
        self.assertEqual(movie.douban_id, "12345")
        self.assertEqual(movie.rating, 8.5)
        self.assertEqual(movie.my_rating, 9)
    
    def test_movie_to_dict(self):
        """测试电影对象转字典"""
        movie = Movie(
            title="测试电影",
            douban_id="12345",
            rating=8.5,
            my_rating=None  # None不应该在输出中
        )
        
        movie_dict = movie.to_dict()
        
        self.assertIn("title", movie_dict)
        self.assertIn("rating", movie_dict)
        self.assertNotIn("my_rating", movie_dict)  # None应该被排除
    
    def test_movie_equality(self):
        """测试电影对象相等性"""
        movie1 = Movie(title="电影1", douban_id="12345")
        movie2 = Movie(title="电影2", douban_id="12345")
        movie3 = Movie(title="电影1", douban_id="67890")
        
        self.assertEqual(movie1, movie2)  # douban_id相同
        self.assertNotEqual(movie1, movie3)  # douban_id不同
    
    def test_movie_hash(self):
        """测试电影对象哈希"""
        movie = Movie(title="电影1", douban_id="12345")
        
        # 应该能用作字典键
        movie_set = {movie}
        self.assertEqual(len(movie_set), 1)


if __name__ == "__main__":
    unittest.main()
