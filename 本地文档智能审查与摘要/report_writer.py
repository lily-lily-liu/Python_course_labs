"""分析报告生成模块。"""

import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional


@dataclass
class DocumentAnalysis:
    """单个文档的读取和分析结果。"""

    filename: str
    character_count: int
    success: bool
    status: str
    word_counter: Optional[Counter] = None


def write_csv_report(
    analyses: Iterable[DocumentAnalysis],
    output_dir: Path,
) -> Path:
    """生成带 UTF-8 BOM 的 CSV，确保 Excel 打开中文不乱码。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "summary_report.csv"

    with report_path.open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["文件名", "字符数", "Top10关键词"])
        for analysis in analyses:
            top_words = (
                analysis.word_counter.most_common(10)
                if analysis.word_counter is not None
                else []
            )
            writer.writerow(
                [
                    analysis.filename,
                    analysis.character_count,
                    ";".join(word for word, _ in top_words),
                ]
            )

    print(f"[成功] CSV 报告已保存：{report_path}")
    return report_path


def write_text_report(
    analyses: Iterable[DocumentAnalysis],
    global_counter: Counter,
    output_dir: Path,
) -> Path:
    """生成全局词频、文件词频和处理统计 TXT 报告。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "summary_report.txt"
    analysis_list = list(analyses)
    successful = [item for item in analysis_list if item.success]
    failed = [item for item in analysis_list if not item.success]

    with report_path.open("w", encoding="utf-8") as file:
        file.write("本地文档智能审查与摘要 Agent 分析报告\n")
        file.write("=" * 60 + "\n\n")
        file.write("一、全局 Top 50 高频词\n")
        file.write("-" * 60 + "\n")
        for rank, (word, count) in enumerate(
            global_counter.most_common(50), start=1
        ):
            file.write(f"{rank:>2}. {word}: {count}\n")
        if not global_counter:
            file.write("无可用词频数据。\n")

        file.write("\n二、每个文件的 Top 10 关键词\n")
        file.write("-" * 60 + "\n")
        for analysis in analysis_list:
            file.write(f"\n文件：{analysis.filename}\n")
            if analysis.word_counter is None:
                file.write(f"状态：{analysis.status}\n")
                continue
            keywords = "；".join(
                f"{word}（{count}）"
                for word, count in analysis.word_counter.most_common(10)
            )
            file.write(f"Top10：{keywords or '无'}\n")

        file.write("\n三、处理统计\n")
        file.write("-" * 60 + "\n")
        file.write(f"总文件数：{len(analysis_list)}\n")
        file.write(f"成功数：{len(successful)}\n")
        file.write(f"失败数：{len(failed)}\n")
        file.write("失败文件清单：\n")
        if failed:
            for analysis in failed:
                file.write(f"- {analysis.filename}：{analysis.status}\n")
        else:
            file.write("无\n")

    print(f"[成功] TXT 报告已保存：{report_path}")
    return report_path


def write_reports(
    analyses: Iterable[DocumentAnalysis],
    global_counter: Counter,
    output_dir: Path,
) -> None:
    """一次性生成 CSV 和 TXT 两种报告。"""
    analysis_list = list(analyses)
    write_csv_report(analysis_list, output_dir)
    write_text_report(analysis_list, global_counter, output_dir)
