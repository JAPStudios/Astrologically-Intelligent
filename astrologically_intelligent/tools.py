"""Auditable tool registry with orchestration and installed-plugin support."""
from __future__ import annotations

import json
from typing import Any, Callable

from .storage import Store
from .orchestration import Orchestrator
from .plugins import PluginManager
from .integrations import n8n_client_from_env, paperclip_client_from_env, perplexity_client_from_env, openclaw_client_from_env


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

        reg("n8n.workflows.list","List workflows from a configured n8n instance.", 
            {"limit":{"type":"integer","minimum":1,"maximum":250},"cursor":{"type":"string"}},
            [],lambda limit=100,cursor=None:n8n_client_from_env().list_workflows(limit,cursor))
        reg("n8n.workflows.get","Retrieve a workflow definition from n8n by ID.",
            {"workflow_id":{"type":"string"}},["workflow_id"],
            lambda workflow_id:n8n_client_from_env().get_workflow(workflow_id))
        reg("n8n.workflows.activate","Activate a workflow in the configured n8n instance.",
            {"workflow_id":{"type":"string"}},["workflow_id"],
            lambda workflow_id:n8n_client_from_env().set_workflow_active(workflow_id,True))
        reg("n8n.workflows.deactivate","Deactivate a workflow in the configured n8n instance.",
            {"workflow_id":{"type":"string"}},["workflow_id"],
            lambda workflow_id:n8n_client_from_env().set_workflow_active(workflow_id,False))

        reg("paperclip.agents.list","List agents in a Paperclip company using the configured agent API token.",
            {"company_id":{"type":"string"}},["company_id"],
            lambda company_id:paperclip_client_from_env().list_agents(company_id))
        reg("paperclip.issues.list","List issues in a Paperclip company, optionally filtered by status, agent, or project.",
            {"company_id":{"type":"string"},"status":{"type":"string"},"assignee_agent_id":{"type":"string"},"project_id":{"type":"string"}},
            ["company_id"],lambda company_id,status=None,assignee_agent_id=None,project_id=None:
                paperclip_client_from_env().list_issues(company_id,status,assignee_agent_id,project_id))
        reg("paperclip.issues.create","Create a Paperclip issue in a company.",
            {"company_id":{"type":"string"},"title":{"type":"string"},"description":{"type":"string"},
             "status":{"type":"string"},"priority":{"type":"string"},"assignee_agent_id":{"type":"string"},
             "project_id":{"type":"string"},"goal_id":{"type":"string"}},
            ["company_id","title"],lambda company_id,title,description="",status="todo",priority="medium",
                assignee_agent_id=None,project_id=None,goal_id=None:
                paperclip_client_from_env().create_issue(company_id,title,description,status,priority,
                                                         assignee_agent_id,project_id,goal_id))
        reg("paperclip.goals.create","Create a goal in a Paperclip company.",
            {"company_id":{"type":"string"},"title":{"type":"string"},"description":{"type":"string"}},
            ["company_id","title"],lambda company_id,title,description="":
                paperclip_client_from_env().create_goal(company_id,title,description))
        reg("paperclip.approvals.list","List approval requests in a Paperclip company.",
            {"company_id":{"type":"string"},"status":{"type":"string"}},["company_id"],
            lambda company_id,status=None:paperclip_client_from_env().list_approvals(company_id,status))

        reg("perplexity.search","Search the web using the Perplexity Search API.",
            {"query":{"type":"string"},"max_results":{"type":"integer","minimum":1,"maximum":20}},
            ["query"],lambda query,max_results=5:perplexity_client_from_env().search(query,max_results))

        reg("openclaw.sessions.list","List sessions from a configured OpenClaw Gateway. This connector is read-only.",
            {"session_key":{"type":"string"}},[],lambda session_key="main":
                openclaw_client_from_env().list_sessions(session_key))

    def _list_skills(self) -> list[dict[str, str]]:
        from pathlib import Path
        roots = [(Path("skills"), ""), (Path("upstream"), "upstream/")]
        results=[]
        for root, prefix in roots:
            if not root.is_dir():
                continue
            for path in sorted(root.rglob("SKILL.md")):
                if ".git" in path.parts:
                    continue
                body=path.read_text(encoding="utf-8")
                summary=next((line.lstrip("# ").strip() for line in body.splitlines() if line.strip()),"")
                name=prefix + path.parent.relative_to(root).as_posix()
                results.append({"name":name,"summary":summary[:200]})
        return sorted(results, key=lambda item: item["name"])

    def _read_skill(self, name: str) -> dict[str, str]:
        import re
        from pathlib import Path
        if not isinstance(name, str) or len(name) > 256 or not re.fullmatch(r"[A-Za-z0-9_-]+(?:/[A-Za-z0-9_-]+)*",name):
            raise ValueError("Invalid skill name")
        skills_root=Path("skills").resolve()
        upstream_root=Path("upstream").resolve()
        if name.startswith("upstream/"):
            nested_skill=(skills_root/name/"SKILL.md").resolve()
            if nested_skill.is_relative_to(skills_root) and nested_skill.is_file():
                root, path = skills_root, nested_skill
            else:
                root=upstream_root
                path=(root/name[len("upstream/"):]/"SKILL.md").resolve()
        else:
            root=skills_root
            path=(root/name/"SKILL.md").resolve()
        if not path.is_relative_to(root) or not path.is_file(): raise ValueError("Skill not found")
        if path.stat().st_size > 131072: raise ValueError("Skill exceeds 128 KiB limit")
        return {"name":name,"content":path.read_text(encoding="utf-8")}

    def _remember(self, namespace: str, key: str, value: Any) -> dict[str, bool]:
        self.store.remember(namespace,key,value)
        return {"saved":True}

    def _update_task(self, task_id: str, status: str, assignee: str | None = None):
        task=self.store.update_task(task_id,status,assignee)
        return task or {"error":"Task not found"}
