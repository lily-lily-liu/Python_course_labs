"""
基于阿里云百炼 Qwen 的文档审查 Agent。

本模块读取本地 summary_report.txt 和原始文档片段，构造结构化 Prompt，
调用 DashScope SDK，并将模型返回内容保存为 Markdown 报告。
"""

import concurrent.futures
import os
from pathlib import Path
from typing import Optional


# 后续替换模型时只需修改这里，不需要改动调用逻辑。
QWEN_MODEL = "qwen-plus"
API_KEY_ENV_NAME = "DASHSCOPE_API_KEY"
REQUEST_TIMEOUT_SECONDS = 60


def read_text_with_fallback(file_path: Path) -> Optional[str]:
    """读取文本文件，优先 UTF-8，失败后尝试 GBK。"""
    try:
        return file_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return file_path.read_text(encoding="gbk")
        except (OSError, UnicodeDecodeError) as error:
            print(f"[警告] 无法读取文件片段 {file_path}：{error}")
            return None
    except OSError as error:
        print(f"[警告] 无法读取文件片段 {file_path}：{error}")
        return None


def build_prompt(
    summary_report_path: Path,
    input_dir: Path,
) -> Optional[str]:
    """
    读取 Top 50 报告和每个文档前 2000 个字符，拼接结构化 Prompt。
    """
    summary_report = read_text_with_fallback(summary_report_path)
    if summary_report is None:
        return None

    document_sections = []
    document_paths = sorted(
        path
        for path in input_dir.rglob("*")
        if path.is_file() and path.suffix.lower() in {".txt", ".md"}
    )

    for document_path in document_paths:
        content = read_text_with_fallback(document_path)
        if content is None:
            continue
        relative_name = document_path.relative_to(input_dir)
        document_sections.append(
            f"### 文件：{relative_name}\n"
            f"核心文本片段（前 2000 字符）：\n"
            f"{content[:2000]}"
        )

    documents_text = "\n\n".join(document_sections)
    return f"""你是一名严谨的中文文档审查专家。请根据以下本地分析资料，
输出结构化的文档审查意见。不得虚构原文中不存在的事实；资料不足时请明确说明。

## 本地词频报告
以下内容来自 summary_report.txt，请重点使用其中的“全局 Top 50 高频词”数据：
{summary_report}

## 文档核心片段
{documents_text or "没有可读取的文档片段。"}

## 输出格式要求
请严格使用以下四个 Markdown 标题，并用中文回答：

## 一、文档主题概括
在 100 字以内概括整体主题。

## 二、核心关键词解读
结合 Top 50 关键词及其词频，解释主要关注点和关键词之间的关系。

## 三、内容风险或缺失点提示
指出可以从资料中识别出的风险、信息缺失或需要进一步核实的地方。
不要把推测写成事实。

## 四、改进建议
只给出 3 条具体、可执行的改进建议，并使用编号列表。
"""


def extract_response_text(response: object) -> str:
    """兼容 DashScope 响应对象和字典，提取模型正文。"""
    output = getattr(response, "output", None)
    if output is None and isinstance(response, dict):
        output = response.get("output")

    choices = getattr(output, "choices", None)
    if choices is None and isinstance(output, dict):
        choices = output.get("choices")
    if not choices:
        return ""

    first_choice = choices[0]
    message = getattr(first_choice, "message", None)
    if message is None and isinstance(first_choice, dict):
        message = first_choice.get("message")

    content = getattr(message, "content", None)
    if content is None and isinstance(message, dict):
        content = message.get("content")
    if isinstance(content, list):
        return "\n".join(
            item.get("text", "")
            for item in content
            if isinstance(item, dict)
        ).strip()
    return str(content or "").strip()


def call_qwen(prompt: str, api_key: str) -> Optional[str]:
    """在超时限制内调用 DashScope Qwen 模型。"""
    try:
        from dashscope import Generation
    except ImportError:
        print("[警告] 未安装 dashscope，跳过云端文档审查。")
        print("       请执行：pip install dashscope")
        return None

    def request() -> object:
        return Generation.call(
            api_key=api_key,
            model=QWEN_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": "你负责输出准确、克制、结构化的中文文档审查意见。",
                },
                {"role": "user", "content": prompt},
            ],
            result_format="message",
        )

    try:
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        future = executor.submit(request)
        try:
            response = future.result(timeout=REQUEST_TIMEOUT_SECONDS)
        finally:
            # 不等待已经超时的网络请求，保证本地流程可以及时结束。
            executor.shutdown(wait=False, cancel_futures=True)
        text = extract_response_text(response)
        if not text:
            print("[警告] Qwen 返回内容为空，未生成云端审查报告。")
            return None
        return text
    except concurrent.futures.TimeoutError:
        print(
            f"[警告] Qwen 请求超过 {REQUEST_TIMEOUT_SECONDS} 秒，"
            "已跳过云端审查。"
        )
    except Exception as error:
        print(f"[警告] Qwen API 调用失败，已跳过云端审查：{error}")
    return None


def generate_review_report(
    summary_report_path: Path,
    input_dir: Path,
    output_dir: Path,
) -> Optional[Path]:
    """生成并保存 review_report.md；失败时不影响本地分析流程。"""
    api_key = os.getenv(API_KEY_ENV_NAME)
    if not api_key:
        print(
            f"[提示] 未配置环境变量 {API_KEY_ENV_NAME}，"
            "跳过云端文档审查。"
        )
        return None

    prompt = build_prompt(summary_report_path, input_dir)
    if not prompt:
        print("[警告] 无法构造云端审查 Prompt，跳过云端审查。")
        return None

    result = call_qwen(prompt, api_key)
    if not result:
        return None

    output_dir.mkdir(parents=True, exist_ok=True)
    report_path = output_dir / "review_report.md"
    try:
        report_path.write_text(
            f"# 文档智能审查意见\n\n"
            f"> 模型：{QWEN_MODEL}\n\n"
            f"{result}\n",
            encoding="utf-8",
        )
    except OSError as error:
        print(f"[警告] 云端审查结果保存失败：{error}")
        return None

    print(f"[成功] AI 审查报告已保存：{report_path}")
    return report_path
