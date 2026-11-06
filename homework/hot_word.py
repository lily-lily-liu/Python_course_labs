# -*- coding: utf-8 -*-
"""
十五五发展规划报告热词频率统计
依赖: pip install jieba matplotlib wordcloud pandas openpyxl
用法: python word_freq.py 十五五规划.txt
"""
import re
import sys
from collections import Counter

import jieba
import jieba.posseg as pseg
import matplotlib.pyplot as plt
import pandas as pd

# ---------- 1. 停用词 ----------
STOPWORDS = set("""
的 了 和 与 及 或 是 在 有 也 就 都 而 及其 以及 等 等等 对 从 到 为 以 于 由 被 让 使 向 把 将
要 会 能 可 应 必须 需要 继续 不断 进一步 更加 全面 持续 加快 加强 推进 推动 支持 鼓励 促进 实现
坚持 完善 健全 深化 提高 提升 增强 扩大 优化 构建 建设 形成 发挥 巩固 统筹 协同 有效 积极 着力
这 那 其 该 各 每 一 二 三 四 五 六 七 八 九 十 个 项 方面 领域 工作 任务 要求 有关 相关 主要
我们 我国 国家 中国 中央 党 党中央 国务院 各级 各部门 各地区 人民 群众 社会 事业 水平 能力 体系
发展 改革 开放 制度 机制 政策 措施 举措 战略 方针 局面 步伐 基础 成果 成效 作用 意义 关系 问题
新 大 小 多 少 高 低 好 快 慢 上 下 中 内 外 前 后 年 月 日 亿元 万亿 以上 以下 左右 第一 第二 第三
""".split())

# ---------- 2. 同义词归并（核心：把概念合并）----------
SYNONYMS = {
    "人工智能+": "人工智能",
    "人工智能＋": "人工智能",
    "AI": "人工智能",
    "数智化": "数智",
    "数智技术": "数智",
    "科技创新": "科技创新",
    "科技": "科技",
    "新质生产力": "新质生产力",
    "中国式现代化": "中国式现代化",
    "高质量发展": "高质量发展",
    "科技自立自强": "科技自立自强",
    "现代化产业体系": "现代化产业体系",
    "国内大循环": "国内大循环",
    "国家安全": "安全",
    "粮食安全": "安全",
    "能源安全": "安全",
    "自主可控": "自主可控",
}

# ---------- 3. 允许保留的词性 ----------
KEEP_POS = {"n", "nz", "nrt", "nt", "nr", "vn", "an", "l", "i", "j"}

# 长度过滤：中文 2 字以上才进榜（1 字词几乎全是噪声）
MIN_LEN = 2


def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def clean(text: str) -> str:
    """去掉标题符号、页码、括号注释、非中文噪声，保留汉字与必要英文"""
    text = re.sub(r"[\ue000-\uf8ff]", "", text)          # 私用区字符
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"[\r\n\t]+", "。", text)              # 段落断句
    text = re.sub(r"[A-Za-z]{1,2}\d*", " ", text)        # 噪声短英文编号
    text = re.sub(r"\d+(\.\d+)?%?", " ", text)           # 数字、百分比
    text = re.sub(r"[^\u4e00-\u9fa5A-Za-z+]", " ", text) # 只留汉字与+
    return text


def word_freq(text: str, topn: int = 30) -> pd.DataFrame:
    words = []
    for w, flag in pseg.cut(text):
        w = w.strip()
        if len(w) < MIN_LEN:                 # 过滤单字
            continue
        if w in STOPWORDS:                   # 过滤停用词
            continue
        if flag not in KEEP_POS:             # 过滤非名词类
            continue
        w = SYNONYMS.get(w, w)               # 同义词归并
        words.append(w)

    counter = Counter(words)
    total = sum(counter.values())
    df = pd.DataFrame(
        [(w, c, round(c / total * 100, 2)) for w, c in counter.most_common(topn)],
        columns=["热词", "频次", "占比(%)"],
    )
    return df


def plot_bar(df: pd.DataFrame, out: str = "freq_bar.png") -> None:
    plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei"]
    plt.rcParams["axes.unicode_minus"] = False
    fig, ax = plt.subplots(figsize=(10, 8))
    ax.barh(df["热词"][::-1], df["频次"][::-1], color="#C0392B")
    ax.set_xlabel("出现频次")
    ax.set_title("“十五五”规划报告热词 Top %d" % len(df))
    for y, v in enumerate(df["频次"][::-1]):
        ax.text(v + 0.5, y, str(v), va="center", fontsize=9)
    plt.tight_layout()
    plt.savefig(out, dpi=200)
    print("已保存条形图:", out)


def plot_cloud(df: pd.DataFrame, out: str = "freq_cloud.png") -> None:
    from wordcloud import WordCloud
    wc = WordCloud(
        font_path="C:/Windows/Fonts/msyh.ttc",
        width=1200, height=800, background_color="white",
    ).generate_from_frequencies(dict(zip(df["热词"], df["频次"])))
    wc.to_file(out)
    print("已保存词云:", out)


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "十五五规划.txt"
    raw = load_text(path)
    df = word_freq(clean(raw), topn=30)
    print(df.to_string(index=False))
    df.to_excel("热词统计结果.xlsx", index=False)   # 可选
    plot_bar(df)
    plot_cloud(df)
