# 贡献指南

感谢你对这个项目的兴趣！本文档将指导你如何为项目做出贡献。

## 行为准则

- 遵守Microsoft代码行为准则
- 尊重他人的想法和反馈
- 保持讨论专业友好

## 如何贡献

### 报告Bug

1. 检查是否已有相似的issue
2. 提供以下信息：
   - 操作系统和Python版本
   - 错误的完整堆栈跟踪
   - 预期行为与实际行为
   - 重现步骤

### 建议功能

1. 使用描述性标题
2. 描述你想要的功能及其价值
3. 如可能，列举示例或参考

### 提交代码

#### 开发环境设置

1. Fork项目
2. 克隆你的fork

```bash
git clone https://github.com/your-username/douban-to-notion.git
cd douban-to-notion
```

3. 创建虚拟环境

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate  # Windows
```

4. 安装依赖

```bash
pip install -r config/requirements.txt
pip install pytest pytest-cov black flake8
```

#### 代码风格

- 使用 Black 格式化代码
- 遵循 PEP 8 规范
- 使用类型注解

```bash
black src/
flake8 src/
```

#### 添加功能

1. 创建feature分支

```bash
git checkout -b feature/your-feature-name
```

2. 编写代码并添加测试

```bash
# 编写功能代码
# 在 tests/ 中添加对应的测试

# 运行测试
pytest tests/
```

3. 提交代码

```bash
git add .
git commit -m "feat: add your feature description"
```

使用以下提交消息格式：
- `feat:` 新功能
- `fix:` 修复bug
- `docs:` 文档更新
- `test:` 测试代码
- `refactor:` 代码重构
- `style:` 代码格式

4. Push并创建Pull Request

```bash
git push origin feature/your-feature-name
```

然后在GitHub上创建Pull Request。

#### Pull Request检查清单

- [ ] 代码遵循项目的风格指南
- [ ] 添加了必要的测试
- [ ] 所有测试通过
- [ ] 更新了相关文档
- [ ] 提交消息有描述性

## 项目结构

```
douban-to-notion/
├── src/                 # 源代码
│   ├── douban/         # 豆瓣模块
│   ├── notion/         # Notion模块
│   ├── sync/           # 同步模块
│   ├── utils/          # 工具模块
│   └── main.py         # 入口文件
├── tests/              # 测试代码
├── config/             # 配置文件
├── logs/               # 日志文件
└── docs/               # 文档
```

## 开发工作流

1. 在 GitHub 上创建 Issue 讨论计划的更改
2. Fork 项目并创建你的分支
3. 实现功能或修复
4. 编写或更新相关测试
5. 确保所有测试通过
6. 提交 Pull Request
7. 等待审查反馈

## 测试

### 运行所有测试

```bash
pytest
```

### 运行特定测试文件

```bash
pytest tests/test_douban.py
```

### 生成覆盖率报告

```bash
pytest --cov=src tests/
```

## 文档

在以下地方更新文档：

- `README.md` - 项目概述
- `USAGE_GUIDE.md` - 使用说明
- `ARCHITECTURE.md` - 架构设计
- 代码中的 docstring

## 许可证

通过贡献代码，你同意你的贡献将在MIT许可证下发布。

## 联系方式

有问题？在GitHub上创建Issue进行讨论。

感谢你的贡献！🙏
