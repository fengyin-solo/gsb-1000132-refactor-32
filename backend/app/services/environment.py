"""环境监测业务规则：状态流转与筛选口径收在这里，登记校验走 app.validation 共用口径。"""
from __future__ import annotations

from typing import Any

from app.store import store
from app.validation import validate_environment_entry

MODULE = "environment"
STATUS_ORDER = ["正常", "预警", "超标", "已恢复"]
ACTION_RULES = {"登记预警": "预警", "确认超标": "超标", "标记恢复": "已恢复"}
NEGATIVE_ACTIONS = []


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

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        rows = store.rows(MODULE)
        existing_codes = [str(row.get("记录编号") or "").strip() for row in rows]
        cleaned, problems = validate_environment_entry(values, existing_codes=existing_codes)
        if problems:
            return None, problems
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update(cleaned)
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
