"""环境记录登记的共用校验口径：缺失、超限、重复、异常值只在这里定义一次。

接口（app/services/environment.py）与页面（frontend/src/utils/entryValidation.ts）
按同一份规则与同一句文案给结论，同一个输入在任意入口得到的说明完全一致。

校验口径：
- 缺失：记录编号、监测区域、温度值、湿度值均为必填；
- 异常值：温度值、湿度值无法解析成有限数值（含 NaN、Inf）；
- 超限：温度值需在 10~30℃ 之间，湿度值需在 30~80% 之间；
- 重复：记录编号不允许与已有记录相同。
"""
from __future__ import annotations

import math
from typing import Any

# 文本字段：均为必填；记录编号额外要求不可重复。
TEXT_FIELDS: list[str] = ["记录编号", "监测区域"]

# 数值字段：均为必填，(下限, 上限, 单位)；超出量程即超限，无法解析即异常值。
NUMBER_FIELD_RULES: dict[str, tuple[float, float, str]] = {
    "温度值": (10.0, 30.0, "℃"),
    "湿度值": (30.0, 80.0, "%"),
}

REQUIRED_FIELDS: list[str] = [*TEXT_FIELDS, *NUMBER_FIELD_RULES]
UNIQUE_FIELDS: list[str] = ["记录编号"]


def _is_blank(value: Any) -> bool:
    return value is None or not str(value).strip()


def _parse_number(value: Any) -> float | None:
    """把输入解析成有限小数；无法解析（含 NaN、Inf）一律视为异常值。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
    else:
        try:
            number = float(str(value).strip())
        except ValueError:
            return None
    return number if math.isfinite(number) else None


def _fmt(number: float) -> str:
    """数值展示统一不带多余的尾零，与页面显示保持一致。"""
    return f"{number:g}"


def _display(value: Any) -> str:
    """异常值回显：布尔按 JSON 写法小写，与页面侧 String(value) 逐字一致。"""
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip()


def validate_environment_entry(
    values: dict[str, Any],
    *,
    existing_codes: list[str] | None = None,
) -> tuple[dict[str, Any], list[str]]:
    """按统一口径校验一条环境记录，返回 (清洗后的字段, 问题说明列表)。

    问题说明是可以直接展示的中文句子，页面与接口原样使用，不做二次包装。
    """
    problems: list[str] = []
    cleaned: dict[str, Any] = {}

    missing = [field for field in REQUIRED_FIELDS if _is_blank(values.get(field))]
    if missing:
        problems.append(f"缺少必填字段：{'、'.join(missing)}")

    for field in TEXT_FIELDS:
        raw = values.get(field)
        if _is_blank(raw):
            continue  # 缺失已在上面统一报告
        cleaned[field] = str(raw).strip()

    for field, (low, high, unit) in NUMBER_FIELD_RULES.items():
        raw = values.get(field)
        if _is_blank(raw):
            continue
        number = _parse_number(raw)
        if number is None:
            problems.append(f"{field}异常：「{_display(raw)}」不是有效数值")
            continue
        if number < low or number > high:
            problems.append(
                f"{field}超限：需在 {_fmt(low)}~{_fmt(high)}{unit} 之间，当前 {_fmt(number)}{unit}"
            )
            continue
        cleaned[field] = number

    for field in UNIQUE_FIELDS:
        code = cleaned.get(field)
        if code and existing_codes and code in existing_codes:
            problems.append(f"{field}重复：「{code}」已登记过，请更换")

    return cleaned, problems
