"""Generate a self-contained exploratory data analysis report from a pandas DataFrame.

Usage:
    from explore import explore
    report_path = explore(df, "reports/my_data_eda.html")
"""

from __future__ import annotations

import base64
import html
import io
from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def _is_missing(value: Any) -> bool:
    """Return True only when value is a scalar pandas/NumPy missing value."""
    try:
        result = pd.isna(value)
        return bool(result) if np.ndim(result) == 0 else False
    except (TypeError, ValueError):
        return False


def _display_value(value: Any, limit: int = 90) -> str:
    if _is_missing(value):
        return "Missing"
    text = str(value).replace("\n", " ").replace("\r", " ")
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _html_table(frame: pd.DataFrame, *, index: bool = False) -> str:
    return frame.to_html(
        index=index,
        escape=True,
        border=0,
        classes="data-table",
        na_rep="—",
    )


def _figure_html(fig: plt.Figure, alt_text: str) -> str:
    buffer = io.BytesIO()
    fig.tight_layout()
    fig.savefig(buffer, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return (
        '<figure><img src="data:image/png;base64,'
        + encoded
        + '" alt="'
        + html.escape(alt_text, quote=True)
        + '"></figure>'
    )


def _sample_series(series: pd.Series, limit: int = 20_000) -> pd.Series:
    values = series.dropna()
    if len(values) > limit:
        return values.sample(limit, random_state=42)
    return values


def explore(
    df: pd.DataFrame,
    output_file: str | Path = "data_exploration_report.html",
    *,
    title: str = "Data Exploration Report",
    max_plot_columns: int = 8,
    top_categories: int = 10,
    sample_rows: int = 10,
) -> Path:
    """Create an HTML EDA report for the DataFrame and return its path.

    Args:
        df: DataFrame to explore.
        output_file: Destination HTML file. Parent folders are created as needed.
        title: Report heading.
        max_plot_columns: Maximum numeric and categorical columns to chart.
        top_categories: Number of frequent values shown per categorical column.
        sample_rows: Number of rows shown in the sample table.

    Returns:
        The path to the generated HTML report.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError("df must be a pandas DataFrame")
    if max_plot_columns < 0 or top_categories < 1 or sample_rows < 0:
        raise ValueError(
            "max_plot_columns and sample_rows must be non-negative; "
            "top_categories must be at least 1"
        )

    output_path = Path(output_file).expanduser()
    if output_path.suffix.lower() not in {".html", ".htm"}:
        output_path = output_path.with_suffix(".html")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    row_count, column_count = df.shape
    memory_bytes = int(df.memory_usage(index=True, deep=True).sum())
    duplicate_count = 0
    duplicate_check_note = ""
    try:
        duplicate_count = int(df.duplicated().sum())
    except (TypeError, ValueError):
        duplicate_check_note = (
            "Duplicate-row check was unavailable because some cells contain "
            "unhashable values."
        )

    column_info: list[dict[str, Any]] = []
    numeric_columns: list[tuple[str, pd.Series]] = []
    categorical_columns: list[tuple[str, pd.Series]] = []
    datetime_columns: list[tuple[str, pd.Series]] = []

    for position, original_name in enumerate(df.columns):
        series = df.iloc[:, position]
        label = str(original_name)
        if any(str(item) == label for item in df.columns[:position]):
            label = f"{label} [column {position + 1}]"

        count = int(series.count())
        missing_count = row_count - count
        try:
            unique_count: int | str = int(series.nunique(dropna=True))
        except (TypeError, ValueError):
            unique_count = "Unavailable"

        try:
            values = series.dropna().drop_duplicates().head(3).tolist()
        except (TypeError, ValueError):
            values = series.dropna().head(3).tolist()
        examples = [_display_value(value, 55) for value in values]

        column_info.append(
            {
                "Column": label,
                "Type": str(series.dtype),
                "Non-null": count,
                "Missing": missing_count,
                "Missing %": (100 * missing_count / row_count) if row_count else 0.0,
                "Unique": unique_count,
                "Unique %": (
                    100 * unique_count / row_count
                    if row_count and isinstance(unique_count, int)
                    else np.nan
                ),
                "Example values": ", ".join(examples) if examples else "—",
            }
        )

        if pd.api.types.is_numeric_dtype(series.dtype) and not pd.api.types.is_bool_dtype(
            series.dtype
        ):
            numeric_columns.append((label, series))
        elif pd.api.types.is_datetime64_any_dtype(series.dtype) or pd.api.types.is_timedelta64_dtype(
            series.dtype
        ):
            datetime_columns.append((label, series))
        else:
            categorical_columns.append((label, series))

    columns_frame = pd.DataFrame(column_info)
    if not columns_frame.empty:
        columns_frame["Missing %"] = columns_frame["Missing %"].map(
            lambda value: f"{value:.2f}%"
        )
        columns_frame["Unique %"] = columns_frame["Unique %"].map(
            lambda value: f"{value:.2f}%" if pd.notna(value) else "—"
        )

    quality_rows: list[dict[str, str]] = []
    total_cells = row_count * column_count
    total_missing = int(df.isna().sum().sum()) if total_cells else 0
    quality_rows.append(
        {
            "Check": "Missing cells",
            "Finding": (
                f"{total_missing:,} of {total_cells:,} cells "
                f"({100 * total_missing / total_cells:.2f}%) are missing."
                if total_cells
                else "The DataFrame has no cells."
            ),
        }
    )
    quality_rows.append(
        {
            "Check": "Duplicate rows",
            "Finding": f"{duplicate_count:,} duplicate rows found."
            if not duplicate_check_note
            else duplicate_check_note,
        }
    )

    constant_columns = [item["Column"] for item in column_info if item["Unique"] == 1]
    quality_rows.append(
        {
            "Check": "Constant columns",
            "Finding": ", ".join(constant_columns)
            if constant_columns
            else "No constant columns detected.",
        }
    )

    high_missing = [
        f"{item['Column']} ({item['Missing %']:.1f}%)"
        for item in column_info
        if row_count and item["Missing"] / row_count >= 0.5
    ]
    quality_rows.append(
        {
            "Check": "At least 50% missing",
            "Finding": ", ".join(high_missing)
            if high_missing
            else "No columns meet this threshold.",
        }
    )

    id_like: list[str] = []
    for item in column_info:
        unique_percent = item["Unique %"]
        if (
            row_count >= 20
            and isinstance(unique_percent, (int, float, np.floating))
            and pd.notna(unique_percent)
            and unique_percent >= 98
        ):
            id_like.append(item["Column"])
    quality_rows.append(
        {
            "Check": "Potential ID columns",
            "Finding": ", ".join(id_like)
            if id_like
            else "No columns have at least 98% unique values.",
        }
    )
    quality_frame = pd.DataFrame(quality_rows)

    numeric_rows: list[dict[str, Any]] = []
    for label, series in numeric_columns:
        clean = pd.to_numeric(series, errors="coerce").replace(
            [np.inf, -np.inf], np.nan
        ).dropna()
        row: dict[str, Any] = {
            "Column": label,
            "Count": int(clean.count()),
            "Missing": int(row_count - clean.count()),
            "Mean": clean.mean() if len(clean) else np.nan,
            "Std": clean.std() if len(clean) else np.nan,
            "Min": clean.min() if len(clean) else np.nan,
            "25%": clean.quantile(0.25) if len(clean) else np.nan,
            "Median": clean.median() if len(clean) else np.nan,
            "75%": clean.quantile(0.75) if len(clean) else np.nan,
            "Max": clean.max() if len(clean) else np.nan,
            "Skew": clean.skew() if len(clean) > 2 else np.nan,
            "Zeros": int((clean == 0).sum()),
            "IQR outliers": 0,
        }
        if len(clean):
            q1, q3 = clean.quantile([0.25, 0.75])
            spread = q3 - q1
            row["IQR outliers"] = int(
                ((clean < q1 - 1.5 * spread) | (clean > q3 + 1.5 * spread)).sum()
            )
        numeric_rows.append(row)
    numeric_frame = pd.DataFrame(numeric_rows)

    categorical_rows: list[dict[str, Any]] = []
    category_detail_rows: list[dict[str, str]] = []
    for label, series in categorical_columns:
        try:
            counts = series.value_counts(dropna=True)
            unique_count = int(counts.size)
            top_value = counts.index[0] if unique_count else "—"
            top_count = int(counts.iloc[0]) if unique_count else 0
            categorical_rows.append(
                {
                    "Column": label,
                    "Unique": unique_count,
                    "Top value": _display_value(top_value, 70),
                    "Top count": top_count,
                    "Top %": (100 * top_count / row_count) if row_count else 0.0,
                }
            )
            for value, count in counts.head(top_categories).items():
                category_detail_rows.append(
                    {
                        "Column": label,
                        "Value": _display_value(value, 100),
                        "Count": int(count),
                        "Percent": f"{100 * count / row_count:.2f}%"
                        if row_count
                        else "—",
                    }
                )
        except (TypeError, ValueError):
            categorical_rows.append(
                {
                    "Column": label,
                    "Unique": "Unavailable",
                    "Top value": "Unavailable for unhashable values",
                    "Top count": "—",
                    "Top %": "—",
                }
            )

    categorical_frame = pd.DataFrame(categorical_rows)
    if not categorical_frame.empty:
        categorical_frame["Top %"] = categorical_frame["Top %"].map(
            lambda value: f"{value:.2f}%"
            if isinstance(value, (int, float))
            else value
        )
    category_details = pd.DataFrame(category_detail_rows)

    datetime_rows: list[dict[str, str]] = []
    for label, series in datetime_columns:
        clean = series.dropna()
        datetime_rows.append(
            {
                "Column": label,
                "Count": f"{len(clean):,}",
                "Earliest": _display_value(clean.min()) if len(clean) else "—",
                "Latest": _display_value(clean.max()) if len(clean) else "—",
            }
        )
    datetime_frame = pd.DataFrame(datetime_rows)

    chart_html: list[str] = []
    if row_count and column_count:
        missing_by_position = [
            (i, int(df.iloc[:, i].isna().sum()))
            for i in range(column_count)
            if df.iloc[:, i].isna().any()
        ]
        if missing_by_position:
            names = [column_info[i]["Column"] for i, _ in missing_by_position]
            counts = [count for _, count in missing_by_position]
            fig, ax = plt.subplots(figsize=(max(7, min(14, len(names) * 0.6)), 4))
            ax.bar(range(len(names)), counts, color="#d97757")
            ax.set_xticks(range(len(names)))
            ax.set_xticklabels(names, rotation=55, ha="right")
            ax.set_ylabel("Missing values")
            ax.set_title("Missing values by column", parse_math=False)
            chart_html.append(_figure_html(fig, "Missing values by column"))
        else:
            chart_html.append("<p>No missing cells were found.</p>")

    for label, series in numeric_columns[:max_plot_columns]:
        values = _sample_series(
            pd.to_numeric(series, errors="coerce").replace([np.inf, -np.inf], np.nan)
        )
        if values.empty:
            continue
        fig, ax = plt.subplots(figsize=(7, 3.5))
        ax.hist(values, bins="auto", color="#4c78a8", edgecolor="white")
        ax.set_title(f"Distribution: {label}", parse_math=False)
        ax.set_xlabel(label)
        ax.set_ylabel("Rows")
        chart_html.append(_figure_html(fig, f"Numeric distribution of {label}"))

    for label, series in categorical_columns[:max_plot_columns]:
        try:
            counts = series.value_counts(dropna=True).head(top_categories)
        except (TypeError, ValueError):
            continue
        if counts.empty:
            continue
        labels = [_display_value(value, 35) for value in counts.index]
        fig, ax = plt.subplots(figsize=(max(7, min(12, len(labels) * 0.7)), 3.5))
        ax.bar(range(len(labels)), counts.to_numpy(), color="#59a14f")
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=45, ha="right")
        ax.set_title(f"Most frequent values: {label}", parse_math=False)
        ax.set_ylabel("Rows")
        chart_html.append(_figure_html(fig, f"Top values for {label}"))

    correlation_html = "<p>At least two numeric columns are required.</p>"
    if len(numeric_columns) >= 2:
        selected = numeric_columns[:30]
        numeric_matrix = pd.concat(
            [
                pd.to_numeric(series, errors="coerce").rename(label)
                for label, series in selected
            ],
            axis=1,
        )
        correlations = numeric_matrix.corr(method="pearson")
        figure_size = max(6, min(12, len(selected) * 0.45))
        fig, ax = plt.subplots(figsize=(figure_size, figure_size))
        image = ax.imshow(correlations.to_numpy(), vmin=-1, vmax=1, cmap="coolwarm")
        labels = correlations.columns.tolist()
        ax.set_xticks(range(len(labels)))
        ax.set_yticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=70, ha="right", fontsize=8)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_title("Pearson correlation (up to 30 numeric columns)", parse_math=False)
        fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
        if len(labels) <= 15:
            for i in range(len(labels)):
                for j in range(len(labels)):
                    value = correlations.iat[i, j]
                    if pd.notna(value):
                        ax.text(j, i, f"{value:.2f}", ha="center", va="center", fontsize=7)
        correlation_html = _figure_html(fig, "Pearson correlation heatmap")

    sample_frame = df.head(sample_rows).copy()
    sample_frame.columns = [item["Column"] for item in column_info]

    cards = (
        '<div class="cards">'
        f'<div><strong>{row_count:,}</strong><span>Rows</span></div>'
        f'<div><strong>{column_count:,}</strong><span>Columns</span></div>'
        f'<div><strong>{duplicate_count:,}</strong><span>Duplicate rows</span></div>'
        f'<div><strong>{memory_bytes / (1024 ** 2):,.2f} MB</strong><span>Memory usage</span></div>'
        "</div>"
    )

    numeric_html = (
        _html_table(numeric_frame)
        if not numeric_frame.empty
        else "<p>No numeric columns found.</p>"
    )
    category_html = (
        _html_table(categorical_frame)
        if not categorical_frame.empty
        else "<p>No categorical columns found.</p>"
    )
    category_details_html = (
        _html_table(category_details)
        if not category_details.empty
        else "<p>No category frequency table available.</p>"
    )
    datetime_html = (
        _html_table(datetime_frame)
        if not datetime_frame.empty
        else "<p>No date or time columns found.</p>"
    )

    document = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
:root {{ color-scheme: light; --ink:#202733; --muted:#667085; --line:#e4e7ec; --accent:#315b7d; }}
body {{ margin:0; color:var(--ink); background:#f5f7fa; font:15px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif; }}
main {{ max-width:1200px; margin:0 auto; padding:32px 22px 60px; }}
header {{ background:#17324d; color:white; padding:30px 22px; }}
header p {{ color:#d8e4ef; margin-bottom:0; }}
h1 {{ margin:0; font-size:2rem; }}
h2 {{ margin-top:0; color:#17324d; font-size:1.35rem; }}
section {{ background:white; border:1px solid var(--line); border-radius:12px; padding:22px; margin:20px 0; box-shadow:0 2px 8px #1018280a; overflow-x:auto; }}
.cards {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(160px,1fr)); gap:12px; margin:20px 0; }}
.cards div {{ background:#edf3f8; border-radius:10px; padding:16px; }}
.cards strong,.cards span {{ display:block; }}
.cards strong {{ font-size:1.35rem; color:#17324d; }}
.cards span,.note {{ color:var(--muted); }}
.data-table {{ width:100%; border-collapse:collapse; font-size:.9rem; }}
.data-table th,.data-table td {{ text-align:left; vertical-align:top; border-bottom:1px solid var(--line); padding:8px 10px; }}
.data-table th {{ background:#f2f5f8; position:sticky; top:0; }}
figure {{ margin:16px 0 24px; }}
figure img {{ display:block; max-width:100%; height:auto; margin:auto; }}
.charts {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(360px,1fr)); gap:12px; }}
code {{ background:#f2f4f7; padding:2px 5px; border-radius:4px; }}
@media(max-width:600px) {{ main {{ padding:16px 10px 40px; }} section {{ padding:14px; }} .charts {{ display:block; }} }}
</style>
</head>
<body>
<header>
  <h1>{html.escape(title)}</h1>
  <p>Generated by explore.py · {pd.Timestamp.now(tz="UTC").strftime("%Y-%m-%d %H:%M UTC")}</p>
</header>
<main>
<section><h2>Dataset overview</h2>{cards}
<p class="note">Memory usage includes the DataFrame index and a deep estimate of object columns.</p></section>
<section><h2>Column profile</h2>{_html_table(columns_frame) if not columns_frame.empty else "<p>No columns to profile.</p>"}</section>
<section><h2>Data quality checks</h2>{_html_table(quality_frame)}</section>
<section><h2>Numeric summary</h2>{numeric_html}</section>
<section><h2>Categorical summary</h2>{category_html}<h3>Frequent values</h3>{category_details_html}</section>
<section><h2>Date and time summary</h2>{datetime_html}</section>
<section><h2>Correlations</h2>{correlation_html}</section>
<section><h2>Distributions and missingness</h2><div class="charts">{''.join(chart_html)}</div>
<p class="note">Charts are limited to the first {max_plot_columns} numeric and {max_plot_columns} categorical columns; numeric charts sample at most 20,000 values. Correlations use the first 30 numeric columns.</p></section>
<section><h2>First {sample_rows} rows</h2>{_html_table(sample_frame)}</section>
</main>
</body>
</html>
"""
    output_path.write_text(document, encoding="utf-8")
    return output_path.resolve()
