# 本地文档智能审查与摘要 Agent

当前版本支持批量读取本地文档、清洗文本、jieba 分词、停用词过滤、全局词频统计、词云生成和 Qwen 文档审查。

## 项目结构

```text
本地文档智能审查与摘要/
├── main.py                 # 程序入口
├── text_processor.py       # 文本清洗、分词和词频统计
├── wordcloud_generator.py  # 词云生成和保存
├── report_writer.py        # CSV 和 TXT 分析报告生成
├── llm_agent.py            # Qwen 文档审查 Agent
├── README.md               # 运行说明
├── docs/                   # 待分析文档（支持 .txt 和 .md）
│   ├── project_intro.txt
│   ├── review_notes.md
│   └── meeting_summary.txt
└── config/
    ├── stopwords.txt       # 停用词表，每行一个词
    └── user_dict.txt       # 自定义专业词典，每行一个词
└── output/
    ├── document_wordcloud.png  # 运行后自动生成的词云图片
    ├── summary_report.csv      # Excel 可打开的汇总报告
    ├── summary_report.txt      # 详细文本报告
    └── review_report.md        # 云端 AI 审查意见（需配置 API Key）
```

## 运行方式

### 在 PyCharm 中运行

1. 在 PyCharm 中打开 `本地文档智能审查与摘要` 目录。
2. 确认项目解释器使用 Python 3.9 或更高版本，并安装依赖：

   ```bash
   pip install jieba wordcloud matplotlib dashscope
   ```

3. 在左侧项目文件树中右键 `main.py`，选择 **Run 'main'**。
4. 在下方 Run 窗口查看文件读取统计、全局词频 Top 50、词云和报告保存提示。

也可以右键项目目录中的 `main.py`，选择 **Open In > Terminal**，执行：

```bash
python main.py
```

程序会先尝试使用 UTF-8 读取；如果遇到编码错误，会自动使用 GBK 兜底。单个文件读取失败时会打印错误状态，并继续处理其他文件。

完整流程为：读取文档 → 清洗和分词 → 全局词频统计 → 生成词云 → 生成 CSV/TXT 报告 → 调用 Qwen 生成 AI 审查意见。

### 配置阿里云百炼 API Key

程序不会把 API Key 写入代码，而是从环境变量 `DASHSCOPE_API_KEY` 读取。

Windows PowerShell（当前终端会话）：

```powershell
$env:DASHSCOPE_API_KEY = "你的阿里云百炼API Key"
python main.py
```

Windows CMD（当前命令行窗口）：

```cmd
set DASHSCOPE_API_KEY=你的阿里云百炼API Key
python main.py
```

如果希望永久配置，可以在 Windows“系统属性 → 环境变量”中新增用户变量
`DASHSCOPE_API_KEY`，然后重启 PyCharm。未配置 Key、网络超时、SDK 未安装或模型返回为空时，程序会给出提示，但本地词云和 CSV/TXT 报告仍会保留。

### 命令行参数

```bash
python main.py --input docs --output output ^
  --stopwords config/stopwords.txt ^
  --userdict config/user_dict.txt ^
  --font C:/Windows/Fonts/msyh.ttc
```

所有参数都有项目内默认值，直接执行 `python main.py` 即可。`--font` 不指定时自动尝试微软雅黑和黑体。

词云图片会自动保存到 `output/document_wordcloud.png`。程序使用 Agg 图形后端，默认不会弹出窗口；如需本地预览，可在 `main.py` 中将 `generate_wordcloud(..., show=False)` 改为 `show=True`。

在 Windows 中程序优先使用 `C:/Windows/Fonts/msyh.ttc`（微软雅黑），找不到时自动尝试 `C:/Windows/Fonts/simhei.ttf`（黑体）。如果两个字体都不存在，程序会给出提示；词云仍会尝试生成，但中文可能显示为方框。

## 添加待分析文件

将 `.txt` 或 `.md` 文件复制到 `docs/` 目录后重新运行即可。文件扩展名不区分大小写；`docs/` 下的子目录也会被遍历。

`config/stopwords.txt` 和 `config/user_dict.txt` 均采用 UTF-8 编码，每行放置一个词，供后续文本分析功能使用。

程序会先删除 HTML 标签、URL 和多余空白，再使用 jieba 精确模式分词，并过滤单字符、停用词、纯数字和纯标点词语。
