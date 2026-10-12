"""生成一线城市电费模拟数据，并清洗后导出 CSV 与 Excel。

处理规则：
1. 日期、区域、用户类型、用电量、电价、电费金额任一字段为空时剔除。
2. 用电量、电价、电费金额必须为正数；负数、零值和无法转换的值剔除。
3. 按区域和用户类型计算用电量的保守 IQR 上界（Q3 + 3 * IQR），超过上界的记录视为异常值并剔除。模拟数据存在季节波动，因此使用 3 倍 IQR 避免误删正常峰值。
4. 对所有字段完全一致的记录去重，仅保留第一条。

默认运行：
    python citypower_Panel/generate_power_data.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd


SEED = 20261012
START_DATE = "2025-01-01"
END_DATE = "2025-12-31"
REQUIRED_COLUMNS = ["日期", "区域", "用户类型", "用电量(kWh)", "电价", "电费金额"]

REGIONS = {
    "北京": ["朝阳区", "海淀区"],
    "上海": ["浦东新区", "闵行区"],
    "广州": ["天河区", "番禺区"],
    "深圳": ["南山区", "龙岗区"],
}
USER_TYPES = ("居民", "商业", "工业")
BASE_USAGE = {"居民": 28_000, "商业": 115_000, "工业": 420_000}
PRICE_RANGE = {"居民": (0.48, 0.62), "商业": (0.82, 1.08), "工业": (0.58, 0.86)}


def generate_raw_data() -> pd.DataFrame:
    """生成完整年度的日粒度模拟数据，并注入可复现的脏数据。"""
    rng = np.random.default_rng(SEED)
    dates = pd.date_range(START_DATE, END_DATE, freq="D")
    rows: list[dict[str, object]] = []

    for date in dates:
        seasonal = 1 + 0.12 * np.sin(2 * np.pi * (date.dayofyear - 30) / 365)
        for city, districts in REGIONS.items():
            city_factor = {"北京": 1.00, "上海": 1.12, "广州": 0.94, "深圳": 1.08}[city]
            for district in districts:
                district_factor = rng.uniform(0.88, 1.16)
                for user_type in USER_TYPES:
                    usage = (
                        BASE_USAGE[user_type]
                        * city_factor
                        * district_factor
                        * seasonal
                        * rng.lognormal(mean=0, sigma=0.12)
                    )
                    price_low, price_high = PRICE_RANGE[user_type]
                    price = rng.uniform(price_low, price_high)
                    usage = round(float(usage), 2)
                    price = round(float(price), 4)
                    rows.append(
                        {
                            "日期": date.strftime("%Y-%m-%d"),
                            "区域": f"{city}{district}",
                            "用户类型": user_type,
                            "用电量(kWh)": usage,
                            "电价": price,
                            "电费金额": round(usage * price, 2),
                        }
                    )

    raw = pd.DataFrame(rows, columns=REQUIRED_COLUMNS)

    # 注入脏数据：空值、负数、异常大值、重复行。
    raw.loc[5, "电价"] = np.nan
    raw.loc[127, "区域"] = None
    raw.loc[256, "用电量(kWh)"] = -8_888.0
    raw.loc[389, "电费金额"] = -1_200.0
    raw.loc[512, "用电量(kWh)"] = 99_999_999.0
    raw.loc[513, "电费金额"] = 88_888_888.0
    raw = pd.concat([raw, raw.iloc[[20, 800, 1600]]], ignore_index=True)
    return raw


def clean_data(raw: pd.DataFrame) -> tuple[pd.DataFrame, dict[str, int]]:
    """按照固定规则清洗原始数据，返回清洗结果和各步骤剔除数量。"""
    missing_columns = set(REQUIRED_COLUMNS) - set(raw.columns)
    if missing_columns:
        raise ValueError(f"缺少必要字段：{', '.join(sorted(missing_columns))}")

    data = raw[REQUIRED_COLUMNS].copy()
    stats = {"原始行数": len(data)}

    data["日期"] = pd.to_datetime(data["日期"], errors="coerce")
    for column in ("用电量(kWh)", "电价", "电费金额"):
        data[column] = pd.to_numeric(data[column], errors="coerce")

    before = len(data)
    data = data.dropna(subset=REQUIRED_COLUMNS)
    stats["空值或格式错误"] = before - len(data)

    before = len(data)
    positive_mask = (
        (data["用电量(kWh)"] > 0)
        & (data["电价"] > 0)
        & (data["电费金额"] > 0)
    )
    data = data.loc[positive_mask].copy()
    stats["非正数"] = before - len(data)

    before = len(data)
    group_keys = ["区域", "用户类型"]
    bounds = data.groupby(group_keys)["用电量(kWh)"].quantile([0.25, 0.75]).unstack()
    bounds["上界"] = bounds[0.75] + 3 * (bounds[0.75] - bounds[0.25])
    row_groups = pd.MultiIndex.from_frame(data[group_keys])
    allowed = data["用电量(kWh)"].to_numpy() <= bounds["上界"].reindex(row_groups).to_numpy()
    data = data.loc[allowed].copy()
    stats["异常用电量"] = before - len(data)

    before = len(data)
    data = data.drop_duplicates(subset=REQUIRED_COLUMNS, keep="first").copy()
    stats["重复行"] = before - len(data)

    data["日期"] = data["日期"].dt.strftime("%Y-%m-%d")
    data["用电量(kWh)"] = data["用电量(kWh)"].round(2)
    data["电价"] = data["电价"].round(4)
    data["电费金额"] = data["电费金额"].round(2)
    data = data.sort_values(["日期", "区域", "用户类型"]).reset_index(drop=True)
    stats["清洗后行数"] = len(data)
    return data, stats


def save_outputs(raw: pd.DataFrame, cleaned: pd.DataFrame, stats: dict[str, int], output_dir: Path) -> None:
    """保存原始脏数据和清洗后的 CSV、Excel 文件。"""
    output_dir.mkdir(parents=True, exist_ok=True)
    raw.to_csv(output_dir / "city_power_raw.csv", index=False, encoding="utf-8-sig")
    cleaned.to_csv(output_dir / "city_power_cleaned.csv", index=False, encoding="utf-8-sig")

    with pd.ExcelWriter(output_dir / "city_power_cleaned.xlsx", engine="openpyxl") as writer:
        cleaned.to_excel(writer, sheet_name="清洗后明细", index=False)
        pd.DataFrame([stats]).to_excel(writer, sheet_name="清洗摘要", index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="生成并清洗一线城市电费模拟数据")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "data",
        help="输出目录，默认是 citypower_Panel/data",
    )
    args = parser.parse_args()

    raw = generate_raw_data()
    cleaned, stats = clean_data(raw)
    save_outputs(raw, cleaned, stats, args.output_dir)

    print(f"原始数据：{len(raw):,} 行（含人为注入的脏数据）")
    print(f"清洗数据：{len(cleaned):,} 行")
    print("剔除明细：" + "；".join(f"{key} {value} 行" for key, value in stats.items() if key not in {"原始行数", "清洗后行数"}))
    print(f"输出目录：{args.output_dir.resolve()}")


if __name__ == "__main__":
    main()
