"""一线城市电费数据交互式大屏看板。

启动：
    streamlit run citypower_Panel/visualize_power_data.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st


DATA_PATH = Path(__file__).resolve().parent / "data" / "city_power_cleaned.csv"

BG = "#061526"
PANEL = "#0B2038"
PANEL_ALT = "#102B46"
TEXT = "#F0F7FF"
MUTED = "#9DB6CC"
GRID = "#1C496B"
BLUE = "#1677FF"
CYAN = "#00D4FF"
COLORS = {"居民": "#36CFC9", "商业": "#FFC53D", "工业": "#7B61FF"}

st.set_page_config(
    page_title="一线城市电费运行分析看板",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_data
def load_data(path: str) -> pd.DataFrame:
    data = pd.read_csv(path, parse_dates=["日期"])
    data["月份"] = data["日期"].dt.to_period("M").astype(str)
    return data


def inject_styles() -> None:
    st.markdown(
        f"""
        <style>
        .stApp {{
            background: radial-gradient(circle at 50% -20%, #123552 0%, {BG} 48%);
            color: {TEXT};
        }}
        [data-testid="stHeader"] {{ background: transparent; }}
        [data-testid="stSidebar"] {{
            background: #081C30;
            border-right: 1px solid {GRID};
        }}
        [data-testid="stMetric"] {{
            background: linear-gradient(135deg, {PANEL_ALT}, {PANEL});
            border: 1px solid {GRID};
            border-radius: 10px;
            padding: 14px 18px;
            min-height: 112px;
        }}
        [data-testid="stMetricLabel"] {{
            color: {MUTED};
            font-size: 0.86rem;
        }}
        [data-testid="stMetricValue"] {{
            color: {CYAN};
            font-size: 1.55rem;
            font-weight: 700;
        }}
        .dashboard-title {{
            border-bottom: 1px solid {GRID};
            margin-bottom: 18px;
            padding: 12px 0 16px;
        }}
        .dashboard-title h1 {{
            color: {TEXT};
            font-size: 2.1rem;
            letter-spacing: 0.08em;
            margin: 0;
        }}
        .dashboard-subtitle {{
            color: {MUTED};
            font-size: 0.86rem;
            margin-top: 8px;
        }}
        .section-title {{
            color: {TEXT};
            font-size: 1.12rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            margin: 2px 0 10px;
        }}
        .section-title::before {{
            content: "";
            display: inline-block;
            width: 4px;
            height: 17px;
            background: {CYAN};
            border-radius: 2px;
            margin-right: 8px;
            vertical-align: -2px;
        }}
        .section-note {{
            color: {MUTED};
            font-size: 0.78rem;
            margin: -4px 0 10px 12px;
        }}
        div[data-testid="stVerticalBlockBorderWrapper"] {{
            background: rgba(11, 32, 56, 0.82);
            border: 1px solid {GRID};
            border-radius: 10px;
            padding: 12px 14px 4px;
        }}
        .stDataFrame {{
            border: 1px solid {GRID};
            border-radius: 8px;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def section_heading(title: str, note: str = "") -> None:
    st.markdown(f'<div class="section-title">{title}</div>', unsafe_allow_html=True)
    if note:
        st.markdown(f'<div class="section-note">{note}</div>', unsafe_allow_html=True)


def chart_layout(fig: go.Figure, height: int = 370) -> go.Figure:
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font={"color": TEXT, "family": "Microsoft YaHei, SimHei, sans-serif", "size": 12},
        margin={"l": 8, "r": 12, "t": 42, "b": 18},
        showlegend=True,
        legend={"orientation": "h", "y": 1.12, "x": 0},
        hoverlabel={"bgcolor": PANEL_ALT, "font_color": TEXT},
        xaxis={"gridcolor": GRID, "zerolinecolor": GRID, "linecolor": GRID},
        yaxis={"gridcolor": GRID, "zerolinecolor": GRID, "linecolor": GRID},
    )
    return fig


def main() -> None:
    inject_styles()
    if not DATA_PATH.exists():
        st.error(f"找不到清洗后的数据文件：{DATA_PATH}")
        st.stop()

    data = load_data(str(DATA_PATH))
    cities = sorted(data["区域"].str[:2].unique())
    min_date = data["日期"].min().date()
    max_date = data["日期"].max().date()

    with st.sidebar:
        st.markdown("### ⚙ 筛选条件")
        selected_cities = st.multiselect("城市", cities, default=cities)
        selected_types = st.multiselect("用户类型", list(COLORS), default=list(COLORS))
        selected_dates = st.date_input(
            "统计日期",
            (min_date, max_date),
            min_value=min_date,
            max_value=max_date,
        )
        st.divider()
        st.caption("数据口径")
        st.caption("来源：清洗后的模拟电费明细")
        st.caption(f"更新时间：{max_date.strftime('%Y-%m-%d')}")

    st.markdown(
        """
        <div class="dashboard-title">
            <h1>⚡ 一线城市电费运行分析看板</h1>
            <div class="dashboard-subtitle">
                居民与工商业用电 · 区域对比 · 时间趋势 · 数据明细
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if len(selected_dates) != 2:
        st.warning("请选择完整的开始日期和结束日期。")
        st.stop()
    if not selected_cities or not selected_types:
        st.warning("请至少选择一个城市和一种用户类型。")
        st.stop()

    start_date, end_date = pd.to_datetime(selected_dates)
    filtered = data[
        data["区域"].str[:2].isin(selected_cities)
        & data["用户类型"].isin(selected_types)
        & data["日期"].between(start_date, end_date)
    ].copy()
    if filtered.empty:
        st.warning("当前筛选条件没有数据，请调整筛选条件。")
        st.stop()

    total_usage = filtered["用电量(kWh)"].sum()
    total_revenue = filtered["电费金额"].sum()
    avg_price = total_revenue / total_usage
    monthly = filtered.groupby("月份")["用电量(kWh)"].sum().sort_index()
    month_numbers = monthly.index.str[-2:].astype(int)
    first_half = monthly[month_numbers <= 6].sum()
    second_half = monthly[month_numbers >= 7].sum()
    growth_rate = (second_half / first_half - 1) * 100 if first_half else 0

    with st.container(border=True):
        section_heading("数据概览", "当前筛选范围内的核心运行指标")
        cards = st.columns(4, gap="medium")
        cards[0].metric("总用电量", f"{total_usage / 1e8:.2f} 亿 kWh")
        cards[1].metric("总电费收入", f"{total_revenue / 1e8:.2f} 亿元")
        cards[2].metric("平均电价", f"{avg_price:.4f} 元/kWh")
        cards[3].metric(
            "增长率（阶段代理）",
            f"{growth_rate:+.2f}%",
            help="当前数据覆盖单个年度，采用下半年相对上半年增长率。",
        )

    with st.container(border=True):
        section_heading("维度统计区", "按区域和用户类型观察电费收入结构")
        left, right = st.columns(2, gap="large")
        with left:
            revenue = (
                filtered.groupby("区域", as_index=False)["电费金额"]
                .sum()
                .sort_values("电费金额")
            )
            revenue["电费收入（亿元）"] = revenue["电费金额"] / 1e8
            fig = px.bar(
                revenue,
                x="电费收入（亿元）",
                y="区域",
                orientation="h",
                text="电费收入（亿元）",
                color_discrete_sequence=[BLUE],
                title="各区域电费收入对比",
            )
            fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
            fig.update_layout(showlegend=False)
            st.plotly_chart(chart_layout(fig), use_container_width=True, key="region_revenue")
        with right:
            type_revenue = filtered.groupby("用户类型", as_index=False)["电费金额"].sum()
            fig = px.pie(
                type_revenue,
                names="用户类型",
                values="电费金额",
                hole=0.58,
                color="用户类型",
                color_discrete_map=COLORS,
                title="居民 / 商业 / 工业电费占比",
            )
            fig.update_traces(
                textinfo="label+percent",
                hovertemplate="%{label}<br>%{value:,.2f} 元<extra></extra>",
            )
            st.plotly_chart(chart_layout(fig), use_container_width=True, key="type_revenue")

    with st.container(border=True):
        section_heading("趋势分析区", "按月汇总用电量，识别年度波动和峰值")
        trend = filtered.groupby("月份", as_index=False)["用电量(kWh)"].sum()
        trend["用电量（亿 kWh）"] = trend["用电量(kWh)"] / 1e8
        fig = px.line(
            trend,
            x="月份",
            y="用电量（亿 kWh）",
            markers=True,
            title="全年每月用电量时间变化趋势",
            color_discrete_sequence=[CYAN],
        )
        fig.update_traces(
            line={"width": 3},
            fill="tozeroy",
            fillcolor="rgba(0,212,255,0.12)",
            hovertemplate="%{x}<br>用电量：%{y:.2f} 亿 kWh<extra></extra>",
        )
        st.plotly_chart(chart_layout(fig, height=390), use_container_width=True, key="monthly_usage")

    with st.container(border=True):
        section_heading("明细数据区", "支持查看、排序和下载当前筛选结果")
        detail = filtered.sort_values(["日期", "区域", "用户类型"], ascending=False)
        display_detail = detail[
            ["日期", "区域", "用户类型", "用电量(kWh)", "电价", "电费金额"]
        ].copy()
        display_detail["日期"] = display_detail["日期"].dt.strftime("%Y-%m-%d")
        display_detail["用电量(kWh)"] = display_detail["用电量(kWh)"].map(lambda value: f"{value:,.2f}")
        display_detail["电价"] = display_detail["电价"].map(lambda value: f"{value:.4f}")
        display_detail["电费金额"] = display_detail["电费金额"].map(lambda value: f"{value:,.2f}")
        st.dataframe(display_detail, use_container_width=True, hide_index=True, height=360)
        st.download_button(
            "下载当前筛选明细 CSV",
            data=display_detail.to_csv(index=False).encode("utf-8-sig"),
            file_name="city_power_filtered_detail.csv",
            mime="text/csv",
        )


if __name__ == "__main__":
    main()
