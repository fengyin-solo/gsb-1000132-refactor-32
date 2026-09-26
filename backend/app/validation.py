"""共用输入校验：字段规则、统一错误说明与判定顺序都收在这一份里。

后端接口与前端页面按同一套规则下结论，避免同一处输入在不同入口得到不同结果。
规则覆盖四类问题：缺失（必填为空）、异常值（应为数值却无法解析）、超限（数值越界）、
重复（唯一字段撞号）。前端镜像见 frontend/src/validation/environment.ts。
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

# 数值口径与前端保持一致：只接受常规十进制写法，排除 inf、nan、下划线等解析歧义
NUMBER_PATTERN = re.compile(r"^[+-]?(\d+(\.\d+)?|\.\d+)$")

# 统一错误说明模板：接口与页面共用同一套措辞
MESSAGES = {
    "missing": "缺少必填字段：{field}",
    "not_number": "{field}应为数值，当前内容无法解析：{value}",
    "out_of_range": "{field}超出允许范围（{minimum}~{maximum}），当前值：{value}",
    "duplicate": "{field}「{value}」已存在，请勿重复登记",
}


@dataclass(frozen=True)
class FieldRule:
    """单个字段的校验规则：是否必填、是否唯一、数值上下限。"""

    name: str
    required: bool = False
    unique: bool = False
    numeric: bool = False
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class FieldIssue:
    """一条校验结论：出问题的字段、问题类型与面向用户的统一说明。"""

    field: str
    code: str  # missing / not_number / out_of_range / duplicate
    message: str


def _text_of(value: Any) -> str:
    """把输入统一成去空白文本；None 视为空，0 等数值不会被误判为空。"""
    if value is None:
        return ""
    return str(value).strip()


def parse_number(value: Any) -> float | None:
    """把输入解析成数值；无法解析时返回 None，由调用方按异常值处理。"""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = _text_of(value)
    if not text or not NUMBER_PATTERN.match(text):
        return None
    return float(text)


def _format_limit(limit: float) -> str:
    """上下限的展示口径：整数不带小数点，与前端 String(number) 的写法保持一致。"""
    return f"{limit:g}"


def _row_id(row: Mapping[str, Any]) -> int:
    try:
        return int(row.get("id", 0))
    except (TypeError, ValueError):
        return 0


def _is_duplicate(
    field: str,
    text: str,
    rows: Iterable[Mapping[str, Any]],
    exclude_id: int | None,
) -> bool:
    for row in rows:
        if exclude_id is not None and _row_id(row) == exclude_id:
            continue
        if _text_of(row.get(field)) == text:
            return True
    return False


def validate_entry(
    values: Mapping[str, Any],
    rules: Iterable[FieldRule],
    *,
    existing_rows: Iterable[Mapping[str, Any]] = (),
    exclude_id: int | None = None,
) -> list[FieldIssue]:
    """按规则顺序校验一份登记数据，返回全部问题；空列表代表通过。

    判定顺序固定为：缺失 → 异常值 → 超限 → 重复，保证各入口结论一致。
    existing_rows 用于唯一性判断；exclude_id 在修改场景下排除记录自身。
    """
    issues: list[FieldIssue] = []
    for rule in rules:
        text = _text_of(values.get(rule.name))
        if rule.required and not text:
            issues.append(FieldIssue(rule.name, "missing", MESSAGES["missing"].format(field=rule.name)))
            continue
        if not text:
            continue  # 选填且留空：不再做数值与重复判断
        if rule.numeric:
            number = parse_number(values.get(rule.name))
            if number is None:
                issues.append(FieldIssue(
                    rule.name,
                    "not_number",
                    MESSAGES["not_number"].format(field=rule.name, value=text),
                ))
                continue
            out_of_range = (
                (rule.minimum is not None and number < rule.minimum)
                or (rule.maximum is not None and number > rule.maximum)
            )
            if out_of_range:
                issues.append(FieldIssue(
                    rule.name,
                    "out_of_range",
                    MESSAGES["out_of_range"].format(
                        field=rule.name,
                        minimum=_format_limit(rule.minimum) if rule.minimum is not None else "不限",
                        maximum=_format_limit(rule.maximum) if rule.maximum is not None else "不限",
                        value=text,
                    ),
                ))
                continue
        if rule.unique and _is_duplicate(rule.name, text, existing_rows, exclude_id):
            issues.append(FieldIssue(
                rule.name,
                "duplicate",
                MESSAGES["duplicate"].format(field=rule.name, value=text),
            ))
    return issues
