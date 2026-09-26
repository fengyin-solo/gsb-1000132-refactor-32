"""环境监测业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from typing import Any

from app.store import store
from app.validation import FieldIssue, FieldRule, validate_entry

MODULE = "environment"
STATUS_ORDER = ["正常", "预警", "超标", "已恢复"]
ACTION_RULES = {"登记预警": "预警", "确认超标": "超标", "标记恢复": "已恢复"}
NEGATIVE_ACTIONS: list[str] = []

# 记录编号、监测区域、温度值、湿度值的登记规则：页面与接口共用这一份结论，
# 前端镜像在 frontend/src/validation/environment.ts，改动时两边一起改。
FIELD_RULES = [
    FieldRule("记录编号", required=True, unique=True),
    FieldRule("监测区域", required=True),
    FieldRule("温度值", required=True, numeric=True, minimum=-50, maximum=50),
    FieldRule("湿度值", numeric=True, minimum=0, maximum=100),
]


class EnvironmentService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("记录编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[FieldIssue]]:
        rows = store.rows(MODULE)
        issues = validate_entry(values, FIELD_RULES, existing_rows=rows)
        if issues:
            return None, issues
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        for rule in FIELD_RULES:
            text = str(values.get(rule.name) if values.get(rule.name) is not None else "").strip()
            if text:
                entry[rule.name] = text
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"环境记录 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于环境监测可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"环境记录已{action}"
