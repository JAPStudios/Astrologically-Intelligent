"""Auditable tool registry with orchestration and installed-plugin support."""
from __future__ import annotations

import json
from typing import Any, Callable

from .storage import Store
from .orchestration import Orchestrator
from .plugins import PluginManager


class ToolRegistry:
    def __init__(self, store: Store):
        self.store = store
        self.orchestration = Orchestrator(store.path)
        self._tools: dict[str, tuple[dict[str, Any], Callable[..., Any]]] = {}
        self._register_builtins()
        self.plugins = PluginManager(self)
        self.plugins.load_all()

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

    def close(self):
        self.orchestration.close()

    def _register_builtins(self) -> None:
        obj = {"type": "object", "additionalProperties": False}
        def reg(name, description, properties, required, handler):
            self.register(name, description, {**obj, "properties": properties, "required": required}, handler)

        reg("memory.remember", "Save a user-approved fact in persistent private memory.",
            {"namespace":{"type":"string"},"key":{"type":"string"},"value":{}},
            ["namespace","key","value"], lambda namespace,key,value:self._remember(namespace,key,value))
        reg("memory.recall", "Retrieve saved memory by namespace, optionally by key.",
            {"namespace":{"type":"string"},"key":{"type":"string"}}, ["namespace"],
            lambda namespace,key=None:self.store.recall(namespace,key))
        reg("work.create", "Create a trackable work item for the assistant or a human.",
            {"title":{"type":"string"},"description":{"type":"string"},"assignee":{"type":["string","null"]}},
            ["title"], lambda title,description="",assignee=None:self.store.create_task(title,description,assignee))
        reg("work.list", "List work items, optionally filtered by status.",
            {"status":{"type":"string","enum":["open","in_progress","blocked","done","cancelled"]}}, [],
            lambda status=None:self.store.list_tasks(status))
        reg("work.update", "Update a work item's status and optionally assign it.",
            {"task_id":{"type":"string"},"status":{"type":"string","enum":["open","in_progress","blocked","done","cancelled"]},
             "assignee":{"type":["string","null"]}}, ["task_id","status"],
            lambda task_id,status,assignee=None:self._update_task(task_id,status,assignee))
        reg("skills.list", "List locally installed Markdown skill guides.", {}, [], lambda:self._list_skills())
        reg("skills.read", "Read a skill guide by its exact name.", {"name":{"type":"string"}}, ["name"],
            lambda name:self._read_skill(name))

        reg("agents.register","Register an agent adapter and execution configuration.",
            {"name":{"type":"string"},"adapter":{"type":"string"},"model":{"type":["string","null"]},
             "role":{"type":"string"},"config":{"type":"object"},"heartbeat_seconds":{"type":"integer","minimum":0}},
            ["name","adapter"],lambda name,adapter,model=None,role="agent",config=None,heartbeat_seconds=0:
                self.orchestration.register_agent(name,adapter,model,role,config,heartbeat_seconds))
        reg("agents.list","List registered agents, optionally by state.",{"state":{"type":"string"}},[],
            lambda state=None:self.orchestration.list_agents(state))
        reg("agents.set_state","Pause, activate, or disable a registered agent.",
            {"agent_id":{"type":"string"},"state":{"type":"string","enum":["active","paused","disabled"]}},
            ["agent_id","state"],lambda agent_id,state:self.orchestration.set_agent_state(agent_id,state) or {"error":"Agent not found"})
        reg("agents.due","List active agents whose heartbeat is due.",{},[],lambda:self.orchestration.due_agents())
        reg("goals.create","Create a goal, optionally linked to a parent goal and owner agent.",
            {"title":{"type":"string"},"description":{"type":"string"},"parent_id":{"type":["string","null"]},
             "owner_agent_id":{"type":["string","null"]}},["title"],
            lambda title,description="",parent_id=None,owner_agent_id=None:
                self.orchestration.create_goal(title,description,parent_id,owner_agent_id))
        reg("goals.list","List goals, optionally filtered by status.",{"status":{"type":"string"}},[],
            lambda status=None:self.orchestration.list_goals(status))
        reg("approvals.request","Create a pending approval request for a consequential action.",
            {"action":{"type":"string"},"details":{"type":"object"},"agent_id":{"type":["string","null"]}},
            ["action","details"],lambda action,details,agent_id=None:self.orchestration.request_approval(action,details,agent_id))
        reg("approvals.list","List approval requests by state.",{"status":{"type":"string","enum":["pending","approved","rejected","cancelled"]}},[],
            lambda status="pending":self.orchestration.list_approvals(status))
        reg("approvals.decide","Record an approval decision; pending requests can be decided only once.",
            {"approval_id":{"type":"string"},"decision":{"type":"string","enum":["approved","rejected","cancelled"]},
             "decided_by":{"type":"string"},"note":{"type":"string"}},["approval_id","decision","decided_by"],
            lambda approval_id,decision,decided_by,note="":self.orchestration.decide_approval(approval_id,decision,decided_by,note) or {"error":"Approval not found or already decided"})
        reg("budgets.set","Set a spending limit for an agent or the whole organization for a named period.",
            {"limit_amount":{"type":"number","minimum":0},"period":{"type":"string"},"agent_id":{"type":["string","null"]},
             "currency":{"type":"string"}},["limit_amount","period"],
            lambda limit_amount,period,agent_id=None,currency="USD":self.orchestration.set_budget(limit_amount,period,agent_id,currency))
        reg("budgets.record_cost","Record spend only when it remains within the configured period budget.",
            {"amount":{"type":"number","minimum":0},"period":{"type":"string"},"agent_id":{"type":["string","null"]}},
            ["amount","period"],lambda amount,period,agent_id=None:self.orchestration.record_cost(amount,period,agent_id))
        reg("budgets.list","List configured organization and agent budgets.",{},[],lambda:self.orchestration.budgets())
        reg("runs.start","Create a running execution record for a registered agent.",
            {"agent_id":{"type":"string"},"task_id":{"type":["string","null"]},"input_data":{"type":"object"}},
            ["agent_id"],lambda agent_id,task_id=None,input_data=None:self.orchestration.start_run(agent_id,task_id,input_data))
        reg("runs.finish","Finish a running execution record.",{"run_id":{"type":"string"},
             "status":{"type":"string","enum":["succeeded","failed","cancelled"]},"output":{"type":"object"},
             "cost_amount":{"type":"number","minimum":0}},["run_id","status"],
            lambda run_id,status,output=None,cost_amount=0:self.orchestration.finish_run(run_id,status,output,cost_amount) or {"error":"Run not found or already finished"})
        reg("plugins.discover","Discover installed Astrologically Intelligent plugin entry points.",{},[],
            lambda:self.plugins.discover() if hasattr(self,"plugins") else [])
        reg("plugins.status","Show installed plugin load results.",{},[],
            lambda:self.plugins.status() if hasattr(self,"plugins") else {"loaded":[],"errors":[]})

    def _list_skills(self) -> list[dict[str, str]]:
        from pathlib import Path
        root = Path("skills")
        if not root.is_dir(): return []
        results=[]
        for path in sorted(root.glob("*/SKILL.md")):
            content=path.read_text(encoding="utf-8")
            summary=next((line.lstrip("# ").strip() for line in content.splitlines() if line.strip()),"")
            results.append({"name":path.parent.name,"summary":summary[:200]})
        return results

    def _read_skill(self, name: str) -> dict[str, str]:
        import re
        from pathlib import Path
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}",name): raise ValueError("Invalid skill name")
        root=Path("skills").resolve()
        path=(root/name/"SKILL.md").resolve()
        if path.parent.parent != root or not path.is_file(): raise ValueError("Skill not found")
        if path.stat().st_size > 32768: raise ValueError("Skill exceeds 32 KiB limit")
        return {"name":name,"content":path.read_text(encoding="utf-8")}

    def _remember(self, namespace: str, key: str, value: Any) -> dict[str, bool]:
        self.store.remember(namespace,key,value)
        return {"saved":True}

    def _update_task(self, task_id: str, status: str, assignee: str | None = None):
        task=self.store.update_task(task_id,status,assignee)
        return task or {"error":"Task not found"}
