# 项目架构说明

## 总体设计

```
┌─────────────────────────────────────────────────────────┐
│                    Main Entry Point                      │
│                   (src/main.py)                          │
└────────────────┬────────────────────────────────────────┘
                 │
         ┌───────┴─────────┐
         │                 │
    ┌────▼─────┐      ┌────▼──────┐
    │  Syncer  │      │ Scheduler │
    │  同步器   │      │ 定时器     │
    └────┬─────┘      └────┬──────┘
         │                 │
    ┌────┴────────────┬────┴──────┐
    │                 │           │
┌───▼────────┐  ┌────▼────────┐  │
│   Douban   │  │   Notion    │  │
│  Scraper   │  │   Client    │  │
│ 豆瓣爬虫    │  │ Notion客户端 │  │
└────────────┘  └─────────────┘  │
                                  │
                            ┌─────▼──────┐
                            │   Logger   │
                            │   日志系统  │
                            └────────────┘
```

## 模块结构

### `src/douban/` - 豆瓣模块

- **scraper.py**: 豆瓣爬虫，负责：
  - 爬取用户观影记录
  - 解析电影列表页面
  - 获取电影详情
  - 处理Cookie认证

- **models.py**: 数据模型
  - `Movie` 类：电影数据结构

### `src/notion/` - Notion模块

- **client.py**: Notion API客户端
  - 创建/更新/删除页面
  - 查询数据库
  - 管理属性结构

- **models.py**: Notion数据模型
  - `NotionMovie` 类：Notion页面格式转换

### `src/sync/` - 同步模块

- **syncer.py**: 同步器
  - 协调豆瓣爬虫和Notion客户端
  - 处理数据映射和转换
  - 执行同步逻辑

- **scheduler.py**: 定时任务调度器
  - 定时执行同步任务
  - 管理任务生命周期

### `src/utils/` - 工具模块

- **logger.py**: 日志系统
  - 配置日志输出
  - 提供日志实例

## 数据流

### 手动同步流程

```
用户执行命令
    ↓
加载配置文件
    ↓
初始化日志系统
    ↓
初始化DoubanScraper（设置Cookie、User ID）
    ↓
初始化NotionClient（设置Token、Database ID）
    ↓
初始化Syncer
    ↓
执行syncer.sync()
    ├─ 获取豆瓣电影列表 (DoubanScraper.get_watched_movies)
    ├─ 对每部电影：
    │  ├─ 检查Notion中是否已存在
    │  ├─ 构建Notion格式数据
    │  └─ 创建或更新Notion页面
    └─ 返回统计信息
```

### 自动同步流程

```
用户执行命令 --auto
    ↓
执行第一次手动同步（如果--sync-now）
    ↓
初始化Scheduler
    ↓
每隔N分钟执行一次同步任务
    ├─ 运行syncer.sync()
    ├─ 记录结果
    └─ 等待下一次间隔
```

## 配置系统

配置文件 `config/config.yaml` 包含：

```yaml
douban:           # 豆瓣相关配置
  cookie: ...     # 登录凭证
  user_id: ...    # 用户ID
  list_types: ... # 要同步的列表类型

notion:           # Notion相关配置
  api_token: ...  # API凭证
  database_id: .. # 数据库ID
  overwrite_existing: ... # 是否覆盖已存在的记录

sync:             # 同步策略
  interval_minutes: ... # 自动同步间隔
  sync_comments: ...    # 是否同步短评
  sync_watch_date: ..   # 是否同步观看日期

logging:          # 日志配置
  level: ...      # 日志级别
  log_file: ...   # 日志文件路径
  console_output: ... # 是否输出到控制台
```

## 错误处理

- 网络错误：自动重试，记录错误日志
- 配置错误：程序启动时验证，如失败则退出
- 数据解析错误：跳过单个项目，继续处理其他项目
- API错误：记录错误并继续，不中断整个同步

## 扩展点

### 添加新的观影列表类型

在 `douban/scraper.py` 中添加新方法：

```python
def get_watching_movies(self):
    """获取正在看的电影"""
    # 实现类似get_watched_movies的逻辑
    pass
```

在 `config/config.yaml` 中启用：

```yaml
douban:
  list_types:
    - watched
    - watching
```

### 自定义Notion字段映射

在 `notion/models.py` 的 `build_properties` 方法中添加新字段处理。

### 添加新的数据源

创建新模块 (e.g., `src/imdb/`) 并实现类似的爬虫接口，然后在 `src/sync/syncer.py` 中集成。

## 依赖关系

```
requests        ←  网络请求
beautifulsoup4  ←  HTML解析
notion-client   ←  Notion API
pyyaml          ←  配置管理
schedule        ←  定时任务
python-dotenv   ←  环境变量
lxml            ←  XML/HTML解析
```

## 日志系统

日志记录以下信息：

- **INFO**: 程序启动、配置加载、同步开始/完成、重要操作
- **DEBUG**: 详细的操作步骤、数据解析、网络请求
- **WARNING**: 可恢复的错误、需要注意的情况
- **ERROR**: 不可恢复的错误、操作失败

日志同时输出到：
- 控制台（INFO及以上）
- 文件 `logs/sync.log`（所有级别）

## 性能考虑

- 网络请求均有超时控制（默认10秒）
- 两个请求之间有1秒延迟（礼貌爬虫）
- Notion API请求使用批量操作（减少API调用次数）
- 日志使用异步处理
