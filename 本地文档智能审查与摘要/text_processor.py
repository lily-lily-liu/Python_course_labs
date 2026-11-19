"""
文本处理模块：清洗、分词、停用词过滤和全局词频统计。

本模块只负责基础文本处理，不包含摘要、词云或其他后续功能。
"""

import re
import string
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Iterable, List, Set, Tuple

import jieba


# 停用词文件不存在时使用的基础停用词。
DEFAULT_STOPWORDS = {
    "的", "了", "和", "在", "是", "我", "你", "他", "我们", "他们",
    "为", "以", "等", "并", "对", "与",
}

# 用于删除 HTML 标签和 URL 的正则表达式。
HTML_TAG_PATTERN = re.compile(r"<[^>]*>")
URL_PATTERN = re.compile(r"https?://[^\s]+|www\.[^\s]+", re.IGNORECASE)


def load_user_dict(user_dict_path: Path) -> None:
    """加载自定义词典；词典不存在或加载失败时只警告，不中断程序。"""
    if not user_dict_path.exists():
        print(f"[警告] 自定义词典不存在，跳过加载：{user_dict_path}")
        return

    try:
        jieba.load_userdict(str(user_dict_path))
        print(f"[提示] 已加载自定义词典：{user_dict_path}")
    except (OSError, UnicodeDecodeError, ValueError) as error:
        print(f"[警告] 自定义词典加载失败，将继续运行：{error}")


def load_stopwords(stopwords_path: Path) -> Set[str]:
    """
    加载停用词，每行一个词并去除首尾空白。

    文件不存在时返回内置停用词；文件存在但读取失败时也使用内置词，
    避免停用词配置问题导致整个处理流程中断。
    """
    if not stopwords_path.exists():
        print(f"[警告] 停用词表不存在，使用内置基础停用词：{stopwords_path}")
        return set(DEFAULT_STOPWORDS)

    try:
        stopwords = {
            line.strip()
            for line in stopwords_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        print(f"[提示] 已加载停用词：{stopwords_path}（{len(stopwords)} 个）")
        return stopwords
    except (OSError, UnicodeDecodeError) as error:
        print(f"[警告] 停用词表读取失败，使用内置基础停用词：{error}")
        return set(DEFAULT_STOPWORDS)


def clean_text(text: str) -> str:
    """删除 HTML 标签、URL，并将连续空白字符压缩为一个空格。"""
    text_without_html = HTML_TAG_PATTERN.sub(" ", text)
    text_without_url = URL_PATTERN.sub(" ", text_without_html)
    return re.sub(r"\s+", " ", text_without_url).strip()


def is_punctuation_only(word: str) -> bool:
    """判断词语是否全部由标点或符号组成，兼容中文标点。"""
    return bool(word) and all(
        character in string.punctuation
        or unicodedata.category(character).startswith(("P", "S"))
        for character in word
    )


def tokenize_and_filter(text: str, stopwords: Set[str]) -> List[str]:
    """
    清洗文本后使用 jieba 精确模式分词，并应用全部过滤规则。

    过滤：长度 <= 1、停用词、纯数字、纯标点符号。
    """
    cleaned_text = clean_text(text)
    words = jieba.lcut(cleaned_text, cut_all=False)
    return [
        word.strip()
        for word in words
        if word.strip()
        and len(word.strip()) > 1
        and word.strip() not in stopwords
        and not word.strip().isdigit()
        and not is_punctuation_only(word.strip())
    ]


def count_words(
    documents: Iterable[str],
    stopwords: Set[str],
) -> Counter:
    """统计多个文档中过滤后的词语，返回全局 Counter。"""
    word_counter = Counter()
    for document in documents:
        word_counter.update(tokenize_and_filter(document, stopwords))
    return word_counter


def print_top_words(word_counter: Counter, limit: int = 50) -> None:
    """打印词频最高的前 limit 个词。"""
    print(f"\n全局词频 Top {limit}")
    print("-" * 40)
    if not word_counter:
        print("没有符合过滤条件的词语。")
        return

    for rank, (word, count) in enumerate(word_counter.most_common(limit), start=1):
        print(f"{rank:>2}. {word}: {count}")


def process_documents(
    documents: Iterable[str],
    project_dir: Path,
    stopwords_path: Path = None,
    user_dict_path: Path = None,
) -> Counter:
    """加载词典与停用词，完成批量文本处理并打印全局词频。"""
    if user_dict_path is None:
        user_dict_path = project_dir / "config" / "user_dict.txt"
    if stopwords_path is None:
        stopwords_path = project_dir / "config" / "stopwords.txt"

    load_user_dict(user_dict_path)
    stopwords = load_stopwords(stopwords_path)
    word_counter = count_words(documents, stopwords)
    print_top_words(word_counter)
    return word_counter


def analyze_documents(
    documents: Iterable[str],
    project_dir: Path,
    stopwords_path: Path = None,
    user_dict_path: Path = None,
) -> Tuple[Counter, List[Counter]]:
    """
    分析多个文档，同时返回全局词频和每个文档的词频。

    文档顺序与传入的 documents 顺序一致，便于将每个词频结果写回
    对应的文件报告。
    """
    document_list = list(documents)

    if user_dict_path is None:
        user_dict_path = project_dir / "config" / "user_dict.txt"
    if stopwords_path is None:
        stopwords_path = project_dir / "config" / "stopwords.txt"

    load_user_dict(user_dict_path)
    stopwords = load_stopwords(stopwords_path)

    per_document_counters = [
        Counter(tokenize_and_filter(document, stopwords))
        for document in document_list
    ]
    global_counter = Counter()
    for document_counter in per_document_counters:
        global_counter.update(document_counter)

    print_top_words(global_counter)
    return global_counter, per_document_counters
