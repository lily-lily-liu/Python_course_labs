from pathlib import Path
from zipfile import BadZipFile

import pandas as pd


REQUIRED_COLUMNS = ("日期", "销售员", "产品", "数量", "单价", "地区")
REVENUE_COLUMN = "销售额"
DETAIL_SHEET = "明细清洗后"
SALESPERSON_SHEET = "按销售员"
REGION_SHEET = "按地区"
OVERVIEW_SHEET = "总览"
MONTH_COLUMN = "月份"


class SalesReportError(Exception):
    """销售报表处理失败时提供可读的中文错误信息。"""


def clean_sales_data(data: pd.DataFrame) -> pd.DataFrame:
    """清洗销售明细，并为有效记录计算销售额。"""
    missing_columns = [column for column in REQUIRED_COLUMNS if column not in data.columns]
    if missing_columns:
        raise SalesReportError(f"输入文件缺少必需字段：{', '.join(missing_columns)}")

    cleaned = data.copy()
    for column in ("销售员", "产品", "地区"):
        cleaned[column] = cleaned[column].map(
            lambda value: value.strip() if isinstance(value, str) else value
        )
        cleaned[column] = cleaned[column].replace("", pd.NA)

    cleaned = cleaned.dropna(subset=list(REQUIRED_COLUMNS))
    try:
        cleaned["数量"] = pd.to_numeric(cleaned["数量"], errors="raise")
        cleaned["单价"] = pd.to_numeric(cleaned["单价"], errors="raise")
        cleaned["日期"] = pd.to_datetime(cleaned["日期"], errors="raise")
    except (TypeError, ValueError) as error:
        raise SalesReportError(f"输入数据格式无效：{error}") from error

    cleaned = cleaned.loc[cleaned["数量"] > 0]
    cleaned = cleaned.drop_duplicates(keep="first")
    if cleaned.empty:
        raise SalesReportError("清洗后没有有效销售数据。")

    cleaned[REVENUE_COLUMN] = cleaned["数量"] * cleaned["单价"]
    return cleaned.reset_index(drop=True)


def generate_report(
    input_path: str | Path,
    output_path: str | Path = "report.xlsx",
) -> Path:
    """只读读取销售原始 Excel，清洗并生成包含四个工作表的报表。"""
    source = Path(input_path)
    destination = Path(output_path)
    if not source.is_file():
        raise SalesReportError(f"输入文件不存在：{source}")
    if source.resolve() == destination.resolve() or (
        destination.exists() and source.samefile(destination)
    ):
        raise SalesReportError("输出文件不能与输入文件相同，以免覆盖原始数据。")

    try:
        raw_data = pd.read_excel(source, engine="openpyxl")
    except (BadZipFile, OSError, ValueError, ImportError) as error:
        raise SalesReportError(f"无法读取Excel文件（文件可能已损坏）：{source}") from error
    except Exception as error:
        raise SalesReportError(f"读取Excel文件失败：{source}；{error}") from error

    details = clean_sales_data(raw_data)
    salesperson_summary = (
        details.groupby("销售员", as_index=False)[REVENUE_COLUMN]
        .sum()
        .sort_values("销售员")
    )
    region_summary = (
        details.groupby("地区", as_index=False)[REVENUE_COLUMN]
        .sum()
        .sort_values("地区")
    )
    month_values = details["日期"].dt.to_period("M").astype(str)
    overview = details.assign(**{MONTH_COLUMN: month_values})
    monthly_summary = (
        overview.groupby(MONTH_COLUMN, as_index=False)[REVENUE_COLUMN]
        .sum()
        .sort_values(MONTH_COLUMN)
    )

    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with pd.ExcelWriter(destination, engine="openpyxl") as writer:
            details.to_excel(writer, sheet_name=DETAIL_SHEET, index=False)
            salesperson_summary.to_excel(
                writer, sheet_name=SALESPERSON_SHEET, index=False
            )
            region_summary.to_excel(writer, sheet_name=REGION_SHEET, index=False)
            monthly_summary.to_excel(writer, sheet_name=OVERVIEW_SHEET, index=False)
    except (OSError, ValueError, ImportError) as error:
        raise SalesReportError(f"写入报表失败：{destination}；{error}") from error

    return destination
