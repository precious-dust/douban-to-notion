from notion_client import Client
from typing import List, Optional
from ..utils.logger import get_logger
import requests
import tempfile
import os
import mimetypes
import base64

logger = get_logger("notion.client")


class NotionClient:
    """Notion API客户端"""

    def __init__(self, api_token: str, database_id: str):
        """
        初始化Notion客户端

        Args:
            api_token: Notion API Token
            database_id: Notion数据库ID
        """
        self.client = Client(auth=api_token)
        self.api_token = api_token
        self.database_id = database_id
        # 可选的存储配置（例如 imgur）可以通过 config 传入并设置到此属性
        self.storage_config = None

    def configure_storage(self, storage_config: dict):
        """配置外部图片上传服务（可选）。

        支持格式示例:
        storage:
          imgur:
            client_id: YOUR_CLIENT_ID
        """
        self.storage_config = storage_config
    
    def create_page(self, properties: dict) -> dict:
        """
        创建新页面
        
        Args:
            properties: 页面属性
        
        Returns:
            创建的页面信息
        """
        try:
            # 如果配置了存储（如 imgur），尝试上传封面并替换外链
            try:
                properties = self._maybe_upload_cover(properties)
            except Exception as e:
                logger.warning(f"封面上传失败，使用原始链接: {e}")

            page = self.client.pages.create(
                parent={"database_id": self.database_id},
                properties=properties
            )
            logger.info(f"创建页面成功: {properties.get('电影名', {}).get('title', [{}])[0].get('text', {}).get('content', 'Unknown')}")
            return page
        except Exception as e:
            logger.error(f"创建页面失败: {e}")
            raise
    
    def query_database(self, filter_conditions: dict = None, page_size: int = 100) -> List[dict]:
        """
        查询数据库
        
        Args:
            filter_conditions: 过滤条件
            page_size: 每页数量
        
        Returns:
            查询结果列表
        """
        try:
            results = []
            has_more = True
            start_cursor = None
            
            while has_more:
                kwargs = {
                    "database_id": self.database_id,
                    "page_size": page_size
                }
                
                if start_cursor:
                    kwargs["start_cursor"] = start_cursor
                
                if filter_conditions:
                    kwargs["filter"] = filter_conditions
                
                response = self.client.databases.query(**kwargs)
                results.extend(response.get("results", []))
                
                has_more = response.get("has_more", False)
                start_cursor = response.get("next_cursor")
            
            logger.info(f"查询数据库成功，返回 {len(results)} 条记录")
            return results
        
        except Exception as e:
            logger.error(f"查询数据库失败: {e}")
            raise
    
    def get_page_by_title(self, title: str) -> Optional[dict]:
        """
        根据标题获取页面
        
        Args:
            title: 电影名
        
        Returns:
            页面信息或None
        """
        try:
            filter_conditions = {
                "property": "电影名",
                "title": {
                    "equals": title
                }
            }
            
            results = self.query_database(filter_conditions)
            return results[0] if results else None
        
        except Exception as e:
            logger.debug(f"查询页面失败: {e}")
            return None

    def get_page_by_title_or_url(self, title: str = None, url: str = None) -> Optional[dict]:
        """
        根据标题或豆瓣链接获取页面，避免重复创建。
        """
        try:
            filters = []
            if title:
                filters.append({
                    "property": "电影名",
                    "title": {"equals": title}
                })
            if url:
                filters.append({
                    "property": "豆瓣链接",
                    "url": {"equals": url}
                })

            if not filters:
                return None

            filter_conditions = filters[0] if len(filters) == 1 else {"or": filters}
            results = self.query_database(filter_conditions)
            return results[0] if results else None
        except Exception as e:
            logger.debug(f"查询页面失败: {e}")
            return None
    
    def update_page(self, page_id: str, properties: dict) -> dict:
        """
        更新页面
        
        Args:
            page_id: 页面ID
            properties: 要更新的属性
        
        Returns:
            更新后的页面信息
        """
        try:
            try:
                properties = self._maybe_upload_cover(properties)
            except Exception as e:
                logger.warning(f"封面上传失败，使用原始链接: {e}")

            page = self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            logger.info(f"更新页面成功: {page_id}")
            return page
        except Exception as e:
            logger.error(f"更新页面失败: {e}")
            raise
    
    def delete_page(self, page_id: str) -> None:
        """
        删除页面
        
        Args:
            page_id: 页面ID
        """
        try:
            self.client.blocks.update(
                block_id=page_id,
                archived=True
            )
            logger.info(f"删除页面成功: {page_id}")
        except Exception as e:
            logger.error(f"删除页面失败: {e}")
            raise
    
    def get_database_structure(self) -> dict:
        """
        获取数据库结构信息
        
        Returns:
            数据库属性结构
        """
        try:
            database = self.client.databases.retrieve(self.database_id)
            properties = database.get("properties", {})
            logger.info(f"获取数据库结构成功，包含 {len(properties)} 个属性")
            return properties
        except Exception as e:
            logger.error(f"获取数据库结构失败: {e}")
            raise

    def _maybe_upload_cover(self, properties: dict) -> dict:
        """处理封面图片：下载豆瓣图片并上传到 Notion 服务器，解决防盗链问题。"""
        cover = properties.get('封面')
        if not cover:
            return properties

        files = cover.get('files') or []
        if not files:
            return properties

        first = files[0]
        external = first.get('external')
        if not external:
            return properties

        url = external.get('url')
        if not url:
            return properties

        # 跳过非豆瓣图片（已经托管在其他可访问的地方）
        if 'doubanio.com' not in url:
            return properties

        # 方案1：如果配置了 Imgur，使用 Imgur
        imgur_cfg = self.storage_config.get('imgur') if isinstance(self.storage_config, dict) else None
        if imgur_cfg and imgur_cfg.get('client_id') and imgur_cfg.get('client_id') != 'YOUR_IMGUR_CLIENT_ID':
            try:
                new_url = self._upload_image_to_imgur(url, imgur_cfg.get('client_id'))
                properties['封面'] = {
                    'files': [
                        {
                            'name': first.get('name', 'cover'),
                            'external': {'url': new_url}
                        }
                    ]
                }
                return properties
            except Exception as e:
                logger.debug(f"Imgur 上传失败: {e}")

        # 方案2：下载图片并通过 Notion File Upload API 上传到 Notion 服务器
        try:
            file_upload_id = self._upload_to_notion_storage(url, first.get('name', 'cover'))
            if file_upload_id:
                properties['封面'] = {
                    'files': [
                        {
                            'type': 'file_upload',
                            'file_upload': {'id': file_upload_id}
                        }
                    ]
                }
                logger.debug(f"封面已上传到 Notion: {url[:50]}...")
        except Exception as e:
            logger.warning(f"Notion 文件上传失败: {e}")

        return properties

    def _upload_to_notion_storage(self, image_url: str, name: str = "cover") -> Optional[str]:
        """下载图片并通过 Notion File Upload API 上传，返回 file_upload ID。"""
        # 1. 下载图片
        dl_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
            'Referer': 'https://movie.douban.com/',
            'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        }
        
        # 增加延迟避免触发豆瓣反爬
        import time
        time.sleep(3)
        
        resp = requests.get(image_url, timeout=15, headers=dl_headers)
        resp.raise_for_status()

        # 检查返回的是否为有效图片（豆瓣反爬会返回 HTML/JS 而非图片）
        content_type = resp.headers.get('Content-Type', '')
        if 'text/html' in content_type or len(resp.content) < 2000:
            logger.warning(f"图片下载被豆瓣反爬拦截 ({image_url[:50]}...)，跳过封面上传")
            return None

        # 豆瓣图片统一使用 jpg
        content_type = "image/jpeg"
        ext = ".jpg"

        # 2. 创建文件上传请求
        api_token = self.api_token
        notion_headers = {
            "Authorization": f"Bearer {api_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        create_resp = requests.post(
            "https://api.notion.com/v1/file_uploads",
            headers=notion_headers,
            json={
                "mode": "single_part",
                "filename": f"{name}{ext}",
                "content_type": content_type
            }
        )
        create_resp.raise_for_status()
        upload_info = create_resp.json()

        if upload_info.get("status") != "pending" or not upload_info.get("upload_url"):
            raise Exception(f"创建上传失败: {upload_info}")

        upload_url = upload_info["upload_url"]
        file_id = upload_info["id"]

        # 3. 上传文件内容（multipart/form-data POST）
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name

        try:
            with open(tmp_path, 'rb') as f:
                upload_resp = requests.post(
                    upload_url,
                    headers={
                        "Authorization": f"Bearer {api_token}",
                        "Notion-Version": "2022-06-28",
                    },
                    files={"file": (f"{name}{ext}", f, content_type)}
                )
            upload_resp.raise_for_status()
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        # 4. 验证上传状态
        check_resp = requests.get(
            f"https://api.notion.com/v1/file_uploads/{file_id}",
            headers=notion_headers
        )
        check_info = check_resp.json()
        if check_info.get("status") != "uploaded":
            raise Exception(f"上传未成功: status={check_info.get('status')}")

        return file_id

    def _upload_image_to_imgur(self, image_url: str, client_id: str) -> str:
        """下载图片并上传到 Imgur，返回新图片链接。要求提供 Imgur Client-ID。"""
        headers = {
            'Authorization': f'Client-ID {client_id}',
            'User-Agent': 'Mozilla/5.0',
            'Referer': image_url
        }
        # 下载图片
        resp = requests.get(image_url, stream=True, timeout=20, headers=headers)
        resp.raise_for_status()
        # Imgur 支持 multipart 上传
        files = {'image': ('cover.jpg', resp.content)}
        r = requests.post('https://api.imgur.com/3/image', headers=headers, files=files, timeout=30)
        r.raise_for_status()
        data = r.json()
        link = data.get('data', {}).get('link')
        if not link:
            raise Exception('Imgur 返回结果不包含 link')
        return link
