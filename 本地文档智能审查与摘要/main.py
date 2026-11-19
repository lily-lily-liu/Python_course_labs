"""本地文档智能审查与摘要 Agent 程序入口。"""

import argparse
from collections import Counter
from pathlib import Path
from typing import List, Optional, Tuple

from llm_agent import generate_review_report
from report_writer import DocumentAnalysis, write_reports
from text_processor import analyze_documents
from wordcloud_generator import generate_wordcloud


SUPPORTED_SUFFIXES = {".txt", ".md"}


def read_document(file_path: Path) -> Tuple[Optional[str], str]:
    """按 UTF-8、GBK 顺序读取文档，并返回内容和状态。"""
    try:
        return file_path.read_text(encoding="utf-8"), "读取成功（UTF-8）"
    except UnicodeDecodeError:
        try:
            return file_path.read_text(encoding="gbk"), "读取成功（GBK 兜底）"
        except UnicodeDecodeError as error:
            return None, f"编码错误：UTF-8 和 GBK 均无法解码（{error}）"
        except OSError as error:
            return None, f"文件读取失败（GBK 兜底）：{error}"
    except OSError as error:
        return None, f"文件读取失败：{error}"


def scan_documents(
    docs_dir: Path,
) -> Tuple[List[DocumentAnalysis], List[str]]:
    """读取目录中的文档，并保留成功内容和失败记录。"""
    if not docs_dir.exists():
        print(f"[错误] 文档目录不存在：{docs_dir}")
        return [], []
    if not docs_dir.is_dir():
        print(f"[错误] 文档路径不是目录：{docs_dir}")
        return [], []

    document_paths = sorted(
        (
            path
            for path in docs_dir.rglob("*")
            if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
        ),
        key=lambda path: str(path).lower(),
    )
    if not document_paths:
        print(f"[提示] 没有找到 .txt 或 .md 文件：{docs_dir}")
        return [], []

    analyses: List[DocumentAnalysis] = []
    successful_contents: List[str] = []
    print(f"开始读取文档（目录：{docs_dir}）")
    print("-" * 72)

    for file_path in document_paths:
        content, status = read_document(file_path)
        display_name = str(file_path.relative_to(docs_dir))
        character_count = len(content) if content is not None else 0
        print(f"文件名：{display_name}")
        print(f"字符数：{character_count}")
        print(f"状态：{status}")
        print("-" * 72)
        analyses.append(
            DocumentAnalysis(
                filename=display_name,
                character_count=character_count,
                success=content is not None,
                status=status,
            )
        )
        if content is not None:
            successful_contents.append(content)

    return analyses, successful_contents


def parse_arguments(project_dir: Path) -> argparse.Namespace:
    """解析命令行参数，默认使用项目内的 docs、output 和 config。"""
    parser = argparse.ArgumentParser(
        description="读取文档、统计词频、生成词云和分析报告"
    )
    parser.add_argument("--input", type=Path, default=project_dir / "docs")
    parser.add_argument("--output", type=Path, default=project_dir / "output")
    parser.add_argument(
        "--stopwords",
        type=Path,
        default=project_dir / "config" / "stopwords.txt",
    )
    parser.add_argument(
        "--userdict",
        type=Path,
        default=project_dir / "config" / "user_dict.txt",
    )
    parser.add_argument("--font", type=Path, default=None)
    return parser.parse_args()


def main() -> None:
    """串联读取、文本处理、词云和报告生成的完整流程。"""
    project_dir = Path(__file__).resolve().parent
    arguments = parse_arguments(project_dir)
    analyses, successful_contents = scan_documents(arguments.input)

    if successful_contents:
        global_counter, per_document_counters = analyze_documents(
            successful_contents,
            project_dir,
            stopwords_path=arguments.stopwords,
            user_dict_path=arguments.userdict,
        )
        success_index = 0
        for analysis in analyses:
            if analysis.success:
                analysis.word_counter = per_document_counters[success_index]
                success_index += 1
        generate_wordcloud(
            global_counter,
            arguments.output,
            show=False,
            font_path=arguments.font,
        )
    else:
        global_counter = Counter()

    write_reports(analyses, global_counter, arguments.output)

    # 云端 Agent 是可选步骤；失败时不影响前面的本地结果。
    generate_review_report(
        arguments.output / "summary_report.txt",
        arguments.input,
        arguments.output,
    )


if __name__ == "__main__":
    main()
