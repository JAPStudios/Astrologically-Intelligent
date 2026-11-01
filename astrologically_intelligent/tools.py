"""Small, auditable tool registry; external side effects are deliberately absent by default."""
from __future__ import annotations

import json
from typing import Any, Callable

from .storage import Store


class ToolRegistry:
    def __init__(self, store: Store):
        self.store = store
        self._tools: dict[str, tuple[dict[str, Any], Callable[..., Any]]] = {}
        self._register_builtins()

    def register(self, name: str, description: str, parameters: dict[str, Any], handler: Callable[..., Any]) -> None:
        if not name or name in self._tools:
            raise ValueError(f"Invalid or duplicate tool: {name}")
        self._tools[name] = ({
            "type": "function",
            "function": {"name": name, "description": description, "parameters": parameters},
        }, handler)

    def definitions(self) -> list[dict[str, Any]]:
        return [item[0] for item in self._tools.values()]

    def execute(self, name: str, arguments: str | dict[str, Any]) -> str:
        if name not in self._tools:
            return json.dumps({"error": f"Tool not found: {name}"})
        try:
            parsed = json.loads(arguments) if isinstance(arguments, str) else arguments
            if not isinstance(parsed, dict):
                raise ValueError("Tool arguments must be a JSON object")
            result = self._tools[name][1](**parsed)
            return json.dumps(result, ensure_ascii=False, default=str)
        except (TypeError, ValueError) as exc:
            return json.dumps({"error": str(exc)})

    def _register_builtins(self) -> None:
        obj = {"type": "object", "additionalProperties": False}
        self.register("memory.remember", "Save a user-approved fact in persistent private memory.",
            {**obj, "properties": {"namespace": {"type": "string"}, "key": {"type": "string"},
             "value": {}}, "required": ["namespace", "key", "value"]},
            lambda namespace, key, value: self._remember(namespace, key, value))
        self.register("memory.recall", "Retrieve saved memory by namespace, optionally by key.",
            {**obj, "properties": {"namespace": {"type": "string"}, "key": {"type": "string"}},
             "required": ["namespace"]},
            lambda namespace, key=None: self.store.recall(namespace, key))
        self.register("work.create", "Create a trackable work item for the assistant or a human.",
            {**obj, "properties": {"title": {"type": "string"}, "description": {"type": "string"},
             "assignee": {"type": ["string", "null"]}}, "required": ["title"]},
            lambda title, description="", assignee=None: self.store.create_task(title, description, assignee))
        self.register("work.list", "List work items, optionally filtered by status.",
            {**obj, "properties": {"status": {"type": "string", "enum": ["open", "in_progress", "blocked", "done", "cancelled"]}}},
            lambda status=None: self.store.list_tasks(status))
        self.register("work.update", "Update a work item's status and optionally assign it.",
            {**obj, "properties": {"task_id": {"type": "string"},
             "status": {"type": "string", "enum": ["open", "in_progress", "blocked", "done", "cancelled"]},
             "assignee": {"type": ["string", "null"]}}, "required": ["task_id", "status"]},
            lambda task_id, status, assignee=None: self._update_task(task_id, status, assignee))

    def _remember(self, namespace: str, key: str, value: Any) -> dict[str, bool]:
        self.store.remember(namespace, key, value)
        return {"saved": True}

    def _update_task(self, task_id: str, status: str, assignee: str | None = None) -> dict[str, Any]:
        task = self.store.update_task(task_id, status, assignee)
        return task or {"error": "Task not found"}
