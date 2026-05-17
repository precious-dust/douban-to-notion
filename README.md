# 豆瓣到Notion同步工具

将豆瓣观影记录自动同步至Notion数据库，支持封面图片上传、个人评分、主演、导演等完整信息。

## 功能特性

- ✅ **完整数据同步** - 电影名、评分、主演、导演、类型、时长、观看日期等
- ✅ **封面图片上传** - 通过 Notion File Upload API 上传封面，解决豆瓣防盗链问题
- ✅ **个人评分提取** - 支持豆瓣新版 `rating{n}-t` CSS class 评分格式
- ✅ **主演智能截取** - 最多显示5位主演，超出自动添加"..."
- ✅ **增量同步** - 只同步新增电影，避免重复
- ✅ **进度保存** - 同步进度自动保存，支持断点续传
- ✅ **Cookie 验证** - 同步前自动验证 Cookie 有效性
- ✅ **重试机制** - 请求失败自动重试，带指数退避
- ✅ **GitHub Actions** - 支持云端自动同步，无需本地运行
- ✅ **可选 Selenium** - 遇到反爬时可启用 Selenium 渲染页面

## 项目结构

```
douban-to-notion/
├── .github/
│   └── workflows/
│       └── sync.yml          # GitHub Actions 工作流
├── config/
│   ├── config.yaml           # 配置文件（不提交）
│   ├── config.yaml.example   # 配置模板
│   └── requirements.txt      # 依赖列表
├── src/
│   ├── douban/
│   │   ├── __init__.py
│   │   ├── scraper.py        # 豆瓣爬虫（支持重试、Cookie验证）
│   │   └── models.py         # Movie 数据模型
│   ├── notion/
│   │   ├── __init__.py
│   │   ├── client.py         # Notion API 客户端
│   │   └── models.py         # NotionMovie 数据模型
│   ├── sync/
│   │   ├── __init__.py
│   │   ├── syncer.py         # 同步主逻辑（增量同步、进度保存）
│   │   └── scheduler.py      # 定时任务
│   ├── utils/
│   │   ├── __init__.py
│   │   └── logger.py         # 日志配置
│   └── main.py               # 主程序入口
├── logs/
│   └── sync.log              # 运行日志
├── .env.example              # 环境变量模板
├── .gitignore
└── README.md
```

## 快速开始

### 1. 环境设置

```bash
# 克隆仓库
git clone https://github.com/你的用户名/douban-to-notion.git
cd douban-to-notion

# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
venv\Scripts\activate  # Windows
# 或
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r config/requirements.txt

# 复制配置模板
cp config/config.yaml.example config/config.yaml
# 编辑 config/config.yaml 填入你的配置
```

### 2. 配置

编辑 `config/config.yaml`：

```yaml
# 豆瓣配置
douban:
  cookie: '你的豆瓣Cookie'
  user_id: "你的豆瓣用户ID"
  use_selenium: false

# Notion配置
notion:
  api_token: "你的Notion API Token"
  database_id: "你的数据库ID"  # 32位UUID

# 同步配置
sync:
  max_items: -1        # -1 表示同步全部
  incremental: true    # 增量同步，只同步新电影
```

### 3. 创建 Notion 数据库

在 Notion 中创建数据库，添加以下字段：

| 字段名 | 类型 | 说明 |
|-------|------|------|
| 电影名 | 标题 | 主键 |
| 我的评分 | 单选 | 选项：⭐、⭐⭐、⭐⭐⭐、⭐⭐⭐⭐、⭐⭐⭐⭐⭐ |
| 豆瓣评分 | 数字 | 豆瓣电影评分 |
| 观看日期 | 日期 | 标记观看的日期 |
| 短评 | 文本 | 个人影评 |
| 豆瓣链接 | URL | 电影详情页链接 |
| 发行年份 | 数字 | 上映年份 |
| 时长 | 数字 | 电影时长（分钟） |
| 导演 | 文本 | 导演名字 |
| 主演 | 文本 | 主演名字（最多5位） |
| 类型 | 多选 | 电影类型 |
| 封面 | 文件 | 电影海报 |

### 4. 运行

```bash
# 手动同步（基础信息，速度快）
python src/main.py --sync-now

# 带详情同步（含封面、导演、主演等）
python src/main.py --sync-now --with-details

# 启动定时同步
python src/main.py --auto --with-details
```

## GitHub Actions 自动同步

### 配置步骤

1. **Fork 或推送代码到 GitHub**

2. **设置 Secrets**
   
   在仓库页面：Settings → Secrets and variables → Actions → New repository secret

   | Secret 名称 | 说明 |
   |------------|------|
   | `DOUBAN_COOKIE` | 豆瓣 Cookie |
   | `DOUBAN_USER_ID` | 豆瓣用户 ID |
   | `NOTION_API_TOKEN` | Notion API Token |
   | `NOTION_DATABASE_ID` | Notion 数据库 ID |

3. **启用 Actions**
   
   在 Actions 页面启用工作流

4. **手动触发或等待定时触发**
   
   - 每天 UTC 19:00（北京时间凌晨 3 点）自动运行
   - 或在 Actions 页面手动触发

### 手动触发选项

| 选项 | 说明 |
|------|------|
| `with_details` | 是否获取详细信息（封面、导演、主演等） |
| `max_items` | 最大同步数量（-1 表示全部） |

## 配置说明

### 获取豆瓣 Cookie

1. 在浏览器登录豆瓣
2. 打开开发者工具 (F12)
3. 切换到 Network 标签
4. 刷新页面，点击任意请求
5. 在 Headers 中找到 Cookie，复制完整值

### 获取 Notion API Token

1. 访问 https://www.notion.so/my-integrations
2. 点击 "New integration" 创建集成
3. 复制 "Internal Integration Token"

### 获取 Database ID

1. 打开你的 Notion 数据库页面
2. 从 URL 中提取 32 位 UUID
   - URL 格式：`https://www.notion.so/your-workspace/DATABASE_ID?v=...`
   - 只需复制 `DATABASE_ID` 部分

### 授权 Integration

1. 打开你的 Notion 数据库
2. 点击右上角 "..." → "Add connections"
3. 选择你创建的 Integration

## 命令行参数

| 参数 | 说明 |
|------|------|
| `--sync-now` | 立即执行一次同步 |
| `--with-details` | 同步时获取电影详细信息（封面、导演、主演等） |
| `--auto` | 启动定时同步 |
| `--config` | 指定配置文件路径（默认 config/config.yaml） |

## 新增功能说明

### 增量同步

默认启用增量同步，只同步 Notion 中不存在的电影：
- 同步前查询 Notion 中已存在的电影 ID
- 过滤掉已存在的电影，只同步新电影
- 大幅减少同步时间

### 进度保存

- 每同步 50 部电影自动保存进度
- 同步中断后可查看 `logs/progress.json`
- 即使出错也会保存已同步的进度

### Cookie 验证

- 同步前自动验证 Cookie 是否有效
- Cookie 过期时提示用户重新获取

### 重试机制

- 请求失败自动重试（最多 3 次）
- 指数退避延迟（2s → 4s → 8s）
- 随机延迟避免触发反爬

## 已知限制

| 限制 | 说明 |
|------|------|
| Cookie 会过期 | 需要定期更新（GitHub Secrets 或本地配置） |
| 豆瓣图片反爬 | 频繁请求会触发反爬，封面可能上传失败 |
| 列表页信息有限 | 个人评分仅在列表页可获取 |
| GitHub Actions 时区 | 定时任务使用 UTC 时间 |

## 依赖包

```
requests==2.31.0
beautifulsoup4==4.12.2
notion-client==2.2.1
pyyaml==6.0
schedule==1.2.0
python-dotenv==1.0.0
lxml==4.9.3
```

可选依赖（用于 Selenium 模式）：
```
selenium
webdriver-manager
```

## 常见问题

### Q: GitHub Actions 如何更新 Cookie？

A: 在仓库的 Settings → Secrets → Actions 中更新 `DOUBAN_COOKIE` 的值。

### Q: 为什么增量同步没有生效？

A: 确保 `config.yaml` 中 `sync.incremental` 设置为 `true`。

### Q: 封面图片显示不出来怎么办？

A: 豆瓣图片有防盗链，频繁请求会触发反爬。可以：
1. 减少同步频率
2. 等待一段时间后重新运行
3. 手动在 Notion 中上传封面

### Q: 如何查看同步日志？

A: 
- 本地运行：查看 `logs/sync.log`
- GitHub Actions：在 Actions 页面查看运行日志，或下载日志 artifact

## 更新日志

### v1.2.0 (2026-05-17)

- ✨ 新增 GitHub Actions 支持，云端自动同步
- ✨ 新增增量同步，只同步新电影
- ✨ 新增进度保存和断点续传
- ✨ 新增 Cookie 有效性验证
- ✨ 新增请求重试机制（指数退避）
- ✨ 支持环境变量读取配置
- 🐛 修复各种同步问题

### v1.1.0 (2026-05-17)

- ✨ 新增 Notion File Upload API 封面上传
- ✨ 新增主演字段支持（最多5位）
- 🐛 修复豆瓣新版 HTML 解析问题
- 🐛 修复个人评分提取
- 🐛 修复 Selenium 回退问题

### v1.0.0

- 初始版本

## 许可证

MIT
