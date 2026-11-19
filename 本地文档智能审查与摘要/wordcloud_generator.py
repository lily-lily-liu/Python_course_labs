"""
词云生成模块。

接收文本处理模块生成的词频统计结果，生成并保存中文词云。
"""

from collections import Counter
from pathlib import Path
from typing import Dict, Optional, Union

import matplotlib

# 使用非交互后端，避免 PyCharm 中显示窗口导致程序阻塞。
matplotlib.use("Agg")

import matplotlib.pyplot as plt
from wordcloud import WordCloud


PRIMARY_FONT_PATH = Path("C:/Windows/Fonts/msyh.ttc")
FALLBACK_FONT_PATH = Path("C:/Windows/Fonts/simhei.ttf")


def find_chinese_font() -> Optional[Path]:
    """按优先级查找 Windows 中文字体。"""
    if PRIMARY_FONT_PATH.exists():
        return PRIMARY_FONT_PATH
    if FALLBACK_FONT_PATH.exists():
        print(f"[提示] 未找到微软雅黑，使用备用字体：{FALLBACK_FONT_PATH}")
        return FALLBACK_FONT_PATH

    print(
        "[警告] 未找到可用中文字体："
        f"{PRIMARY_FONT_PATH} 和 {FALLBACK_FONT_PATH} 均不存在。"
    )
    print(
        "[警告] 词云会显示为方框的原因是缺少中文字体，"
        "程序仍会尝试生成图片。"
    )
    return None


def resolve_font_path(font_path: Optional[Path]) -> Optional[Path]:
    """优先使用命令行指定字体，否则查找 Windows 默认字体。"""
    if font_path is not None:
        if font_path.exists():
            return font_path
        print(f"[警告] 指定字体不存在：{font_path}")
        print("[警告] 将继续尝试 Windows 默认中文字体。")
    return find_chinese_font()


def generate_wordcloud(
    word_frequencies: Union[Counter, Dict[str, int]],
    output_dir: Path,
    show: bool = False,
    font_path: Optional[Path] = None,
) -> Optional[Path]:
    """根据 Top 50 词频生成词云并保存到 output_dir。"""
    top_50_frequencies = dict(
        sorted(
            word_frequencies.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:50]
    )
    if not top_50_frequencies:
        print("[提示] 没有可用于生成词云的词频数据。")
        return None

    selected_font_path = resolve_font_path(font_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "document_wordcloud.png"

    try:
        wordcloud = WordCloud(
            font_path=(
                str(selected_font_path)
                if selected_font_path
                else None
            ),
            width=1000,
            height=800,
            background_color="white",
            max_words=50,
            collocations=False,
        )
        wordcloud.generate_from_frequencies(top_50_frequencies)

        plt.figure(figsize=(10, 8))
        plt.imshow(wordcloud, interpolation="bilinear")
        plt.axis("off")
        plt.tight_layout(pad=0)
        plt.savefig(output_path, dpi=150, bbox_inches="tight")

        if show:
            plt.show()
        plt.close()
        print(f"[成功] 词云已保存：{output_path}")
        return output_path
    except (OSError, ValueError, RuntimeError) as error:
        plt.close()
        print(f"[错误] 词云生成失败：{error}")
        return None
