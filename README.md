# paper-radar

paper-radar 是一个面向 LLM / 架构前沿论文的自动化监控脚本。它每天抓取 arXiv `cs.CL`、`cs.LG`、`cs.AI` 的近 7 天论文，用 Hugging Face Papers 的 `Daily` 与 `Trending` 作为热度辅助信号，再基于关键词、作者和机构白名单做评分，最终输出适合放进 Obsidian 的 Markdown 日报。

## 功能概览

- 抓取 arXiv RSS 并解析标题、摘要、作者、链接、发布时间
- 抓取 Hugging Face Papers 页面，失败时自动降级为空结果
- 做去重、跨源匹配、关键词/作者/机构/热度评分
- 默认写入 SQLite，初始化失败自动回退到 JSON 文件
- 生成中文 Markdown 日报，保留论文英文标题
- 支持本地运行、cron 和 GitHub Actions 定时执行

## 安装

```bash
git clone <your-repo-url>
cd paper-radar
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

或：

```bash
pip install -e .
```

如果你要跑测试：

```bash
pip install -e .[dev]
```

## 配置说明

配置全部位于 `config/`：

- `config/keywords.yaml`：高优先级、中优先级、负向关键词
- `config/authors.yaml`：重点机构与重点作者
- `config/sources.yaml`：arXiv feeds 与 Hugging Face 页面列表
- `config/settings.yaml`：时间窗口、阈值、语言、时区等

常用项：

- `lookback_days`：默认抓近几天论文
- `push_threshold_must_read`：进入“必看”的分数线
- `push_threshold_quick_scan`：进入“值得扫摘要”的分数线
- `max_items_in_report`：日报最多输出条数
- `timezone`：报告日期和新鲜度计算使用的时区

## 本地运行

```bash
paper-radar
```

也可以：

```bash
python scripts/main.py
python -m scripts
```

支持的参数：

```bash
python scripts/main.py --lookback-days 3 --dry-run
python scripts/main.py --output-path output/custom_report.md
python scripts/main.py --fuzzy-threshold 0.92
```

参数说明：

- `--lookback-days`：覆盖配置中的时间窗口
- `--dry-run`：不写 SQLite/JSON，只抓取、评分并生成报告
- `--output-path`：自定义 Markdown 输出路径
- `--fuzzy-threshold`：标题模糊匹配阈值，默认 `0.9`

## cron 示例

```cron
0 8 * * * /usr/bin/python3 /path/to/paper-radar/scripts/main.py >> /path/to/paper-radar/logs/cron.log 2>&1
```

## GitHub Actions 示例

仓库已经包含 [`.github/workflows/daily.yml`](.github/workflows/daily.yml)，它会：

- 每天定时运行一次
- 安装依赖
- 执行 `python scripts/main.py`
- 上传 `output/papers_today.md` 为 artifact

如果需要把结果提交回仓库，可在 workflow 中追加 commit/push 步骤。

## 输出样例

```markdown
# 论文雷达 - 2026-03-27

## 必看
### 1. Attention Residuals
- 分数：11.0
- 发布时间：2026-03-16
- 来源：arXiv, HF Daily
- 标签：residual connection, transformer architecture, depth
- 作者：Jane Doe, John Doe
- 链接：https://arxiv.org/abs/2603.12345
- 一句话总结：工作重点在层间残差路径而不是 token 级注意力改造。
- 推荐理由：
  - 命中高优先级关键词 residual connection
  - 命中重点团队
  - 出现在 HF Daily
```

## 测试

```bash
pytest
```

或：

```bash
make test
```

当前覆盖：

- 标题规范化
- 日期过滤
- 关键词打分
- arXiv / HF 匹配
- Markdown 渲染

## 目录结构

```text
paper-radar/
├── README.md
├── LICENSE
├── Makefile
├── requirements.txt
├── pyproject.toml
├── .gitignore
├── .env.example
├── config/
├── data/
├── logs/
├── output/
├── scripts/
├── tests/
└── .github/workflows/daily.yml
```

## 分享建议

- 提交仓库时不要包含 `data/*.db`、抓取结果 JSON 和 `output/papers_today.md`，项目已经通过 `.gitignore` 处理
- 推荐其他用户使用 Python 3.11 或 3.12
- 如果对方只想快速体验，执行 `pip install -r requirements.txt && python scripts/main.py --dry-run` 即可
- 如果希望作为命令行工具安装，执行 `pip install -e .` 后可直接使用 `paper-radar`

## 后续扩展方向

- 接入 OpenReview
- 接入 Semantic Scholar API 或本地 alerts 导入
- 增加邮件、Telegram、Slack、飞书推送
- 接入 LLM 自动生成摘要与点评
- 增加历史统计和趋势图
