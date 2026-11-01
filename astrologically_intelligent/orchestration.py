"""Persistent multi-agent organization, goal, approval, budget, and heartbeat primitives."""
from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any

AGENT_STATES = {"active", "paused", "disabled"}
APPROVAL_STATES = {"pending", "approved", "rejected", "cancelled"}


class Orchestrator:
    """SQLite-backed control plane. Execution is delegated to registered agent adapters."""

    def __init__(self, database: str):
        self.database = str(database)
        self._lock = threading.RLock()
        if self.database != ":memory:":
            Path(self.database).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(self.database, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys=ON")
        self._initialize()

    def _initialize(self):
        with self._lock, self.db:
            self.db.executescript("""
            CREATE TABLE IF NOT EXISTS org_agents(
              id TEXT PRIMARY KEY, name TEXT NOT NULL, adapter TEXT NOT NULL,
              model TEXT, role TEXT NOT NULL DEFAULT 'agent', state TEXT NOT NULL DEFAULT 'active',
              config TEXT NOT NULL DEFAULT '{}', heartbeat_seconds INTEGER NOT NULL DEFAULT 0,
              last_heartbeat REAL, created_at REAL NOT NULL, updated_at REAL NOT NULL
            );
            CREATE TABLE IF NOT EXISTS org_goals(
              id TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT NOT NULL DEFAULT '',
              parent_id TEXT, owner_agent_id TEXT, status TEXT NOT NULL DEFAULT 'active',
              created_at REAL NOT NULL, updated_at REAL NOT NULL,
              FOREIGN KEY(parent_id) REFERENCES org_goals(id),
              FOREIGN KEY(owner_agent_id) REFERENCES org_agents(id)
            );
            CREATE TABLE IF NOT EXISTS org_approvals(
              id TEXT PRIMARY KEY, agent_id TEXT, action TEXT NOT NULL, details TEXT NOT NULL,
              status TEXT NOT NULL DEFAULT 'pending', decided_by TEXT, decision_note TEXT,
              created_at REAL NOT NULL, decided_at REAL,
              FOREIGN KEY(agent_id) REFERENCES org_agents(id)
            );
            CREATE TABLE IF NOT EXISTS org_budgets(
              id TEXT PRIMARY KEY, agent_id TEXT, period TEXT NOT NULL, limit_amount REAL NOT NULL,
              spent_amount REAL NOT NULL DEFAULT 0, currency TEXT NOT NULL DEFAULT 'USD',
              updated_at REAL NOT NULL, UNIQUE(agent_id, period),
              FOREIGN KEY(agent_id) REFERENCES org_agents(id)
            );
            CREATE TABLE IF NOT EXISTS org_runs(
              id TEXT PRIMARY KEY, agent_id TEXT NOT NULL, task_id TEXT, status TEXT NOT NULL,
              input TEXT NOT NULL DEFAULT '{}', output TEXT NOT NULL DEFAULT '{}',
              cost_amount REAL NOT NULL DEFAULT 0, started_at REAL NOT NULL, finished_at REAL,
              FOREIGN KEY(agent_id) REFERENCES org_agents(id)
            );
            CREATE INDEX IF NOT EXISTS org_agents_state ON org_agents(state);
            CREATE INDEX IF NOT EXISTS org_approvals_status ON org_approvals(status, created_at);
            CREATE INDEX IF NOT EXISTS org_runs_agent_time ON org_runs(agent_id, started_at);
            """)

    @staticmethod
    def _dict(row):
        return dict(row) if row else None

    def register_agent(self, name: str, adapter: str, model: str | None = None,
                       role: str = "agent", config: dict | None = None,
                       heartbeat_seconds: int = 0) -> dict[str, Any]:
        if not name.strip() or not adapter.strip():
            raise ValueError("Agent name and adapter are required")
        if heartbeat_seconds < 0:
            raise ValueError("heartbeat_seconds cannot be negative")
        now, agent_id = time.time(), uuid.uuid4().hex
        with self._lock, self.db:
            self.db.execute("""INSERT INTO org_agents
              (id,name,adapter,model,role,state,config,heartbeat_seconds,created_at,updated_at)
              VALUES(?,?,?,?,?,'active',?,?,?,?)""",
              (agent_id,name.strip(),adapter.strip(),model,role,json.dumps(config or {}),heartbeat_seconds,now,now))
        return self.get_agent(agent_id)

    def get_agent(self, agent_id: str):
        with self._lock:
            return self._dict(self.db.execute("SELECT * FROM org_agents WHERE id=?", (agent_id,)).fetchone())

    def list_agents(self, state: str | None = None):
        with self._lock:
            rows = self.db.execute("SELECT * FROM org_agents WHERE state=? ORDER BY created_at", (state,)).fetchall() if state else self.db.execute("SELECT * FROM org_agents ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]

    def set_agent_state(self, agent_id: str, state: str):
        if state not in AGENT_STATES:
            raise ValueError("state must be active, paused, or disabled")
        with self._lock, self.db:
            cur = self.db.execute("UPDATE org_agents SET state=?,updated_at=? WHERE id=?", (state,time.time(),agent_id))
        return self.get_agent(agent_id) if cur.rowcount else None

    def create_goal(self, title: str, description: str = "", parent_id: str | None = None,
                    owner_agent_id: str | None = None):
        if not title.strip():
            raise ValueError("Goal title is required")
        now, goal_id = time.time(), uuid.uuid4().hex
        with self._lock, self.db:
            self.db.execute("""INSERT INTO org_goals(id,title,description,parent_id,owner_agent_id,status,created_at,updated_at)
              VALUES(?,?,?,?,?,'active',?,?)""", (goal_id,title.strip(),description,parent_id,owner_agent_id,now,now))
        return self.get_goal(goal_id)

    def get_goal(self, goal_id: str):
        with self._lock:
            return self._dict(self.db.execute("SELECT * FROM org_goals WHERE id=?", (goal_id,)).fetchone())

    def list_goals(self, status: str | None = None):
        with self._lock:
            rows = self.db.execute("SELECT * FROM org_goals WHERE status=? ORDER BY created_at",(status,)).fetchall() if status else self.db.execute("SELECT * FROM org_goals ORDER BY created_at").fetchall()
        return [dict(r) for r in rows]

    def request_approval(self, action: str, details: dict, agent_id: str | None = None):
        if not action.strip():
            raise ValueError("Approval action is required")
        approval_id, now = uuid.uuid4().hex, time.time()
        with self._lock, self.db:
            self.db.execute("""INSERT INTO org_approvals(id,agent_id,action,details,status,created_at)
              VALUES(?,?,?,?,'pending',?)""", (approval_id,agent_id,action.strip(),json.dumps(details),now))
        return self.get_approval(approval_id)

    def get_approval(self, approval_id: str):
        with self._lock:
            row = self.db.execute("SELECT * FROM org_approvals WHERE id=?", (approval_id,)).fetchone()
        if not row: return None
        result = dict(row); result["details"] = json.loads(result["details"]); return result

    def list_approvals(self, status: str = "pending"):
        with self._lock:
            rows = self.db.execute("SELECT id FROM org_approvals WHERE status=? ORDER BY created_at",(status,)).fetchall()
        return [self.get_approval(r["id"]) for r in rows]

    def decide_approval(self, approval_id: str, decision: str, decided_by: str, note: str = ""):
        if decision not in {"approved","rejected","cancelled"}:
            raise ValueError("decision must be approved, rejected, or cancelled")
        with self._lock, self.db:
            cur = self.db.execute("""UPDATE org_approvals SET status=?,decided_by=?,decision_note=?,decided_at=?
              WHERE id=? AND status='pending'""",(decision,decided_by,note,time.time(),approval_id))
        return self.get_approval(approval_id) if cur.rowcount else None

    def set_budget(self, limit_amount: float, period: str, agent_id: str | None = None, currency: str = "USD"):
        if limit_amount < 0 or not period.strip() or len(currency) != 3:
            raise ValueError("A non-negative limit, period, and three-letter currency are required")
        budget_id, now = uuid.uuid4().hex, time.time()
        with self._lock, self.db:
            self.db.execute("""INSERT INTO org_budgets(id,agent_id,period,limit_amount,spent_amount,currency,updated_at)
              VALUES(?,?,?,?,0,?,?) ON CONFLICT(agent_id,period) DO UPDATE SET
              limit_amount=excluded.limit_amount,currency=excluded.currency,updated_at=excluded.updated_at""",
              (budget_id,agent_id,period,limit_amount,currency.upper(),now))
            row = self.db.execute("SELECT * FROM org_budgets WHERE agent_id IS ? AND period=?",(agent_id,period)).fetchone()
        return dict(row)

    def record_cost(self, amount: float, period: str, agent_id: str | None = None):
        if amount < 0: raise ValueError("Cost cannot be negative")
        with self._lock, self.db:
            row = self.db.execute("SELECT * FROM org_budgets WHERE agent_id IS ? AND period=?",(agent_id,period)).fetchone()
            if not row: raise ValueError("No budget configured for this agent and period")
            if row["spent_amount"] + amount > row["limit_amount"]:
                raise ValueError("Budget limit would be exceeded")
            self.db.execute("UPDATE org_budgets SET spent_amount=spent_amount+?,updated_at=? WHERE id=?",(amount,time.time(),row["id"]))
            updated = self.db.execute("SELECT * FROM org_budgets WHERE id=?",(row["id"],)).fetchone()
        return dict(updated)

    def budgets(self):
        with self._lock:
            return [dict(r) for r in self.db.execute("SELECT * FROM org_budgets ORDER BY period,agent_id").fetchall()]

    def start_run(self, agent_id: str, task_id: str | None = None, input_data: dict | None = None):
        if not self.get_agent(agent_id): raise ValueError("Agent not found")
        run_id, now = uuid.uuid4().hex, time.time()
        with self._lock, self.db:
            self.db.execute("""INSERT INTO org_runs(id,agent_id,task_id,status,input,started_at)
              VALUES(?,?,?,'running',?,?)""",(run_id,agent_id,task_id,json.dumps(input_data or {}),now))
        return self.get_run(run_id)

    def finish_run(self, run_id: str, status: str, output: dict | None = None, cost_amount: float = 0):
        if status not in {"succeeded","failed","cancelled"} or cost_amount < 0:
            raise ValueError("Invalid terminal run status or cost")
        with self._lock, self.db:
            cur = self.db.execute("""UPDATE org_runs SET status=?,output=?,cost_amount=?,finished_at=?
              WHERE id=? AND status='running'""",(status,json.dumps(output or {}),cost_amount,time.time(),run_id))
        return self.get_run(run_id) if cur.rowcount else None

    def get_run(self, run_id: str):
        with self._lock:
            row = self.db.execute("SELECT * FROM org_runs WHERE id=?",(run_id,)).fetchone()
        if not row: return None
        result=dict(row); result["input"]=json.loads(result["input"]); result["output"]=json.loads(result["output"]); return result

    def due_agents(self, now: float | None = None):
        now = time.time() if now is None else now
        with self._lock:
            rows=self.db.execute("""SELECT * FROM org_agents WHERE state='active' AND heartbeat_seconds>0
              AND (last_heartbeat IS NULL OR last_heartbeat + heartbeat_seconds <= ?) ORDER BY created_at""",(now,)).fetchall()
        return [dict(r) for r in rows]

    def mark_heartbeat(self, agent_id: str, at: float | None = None):
        at=time.time() if at is None else at
        with self._lock,self.db:
            cur=self.db.execute("UPDATE org_agents SET last_heartbeat=?,updated_at=? WHERE id=? AND state='active'",(at,at,agent_id))
        return self.get_agent(agent_id) if cur.rowcount else None

    def close(self):
        with self._lock: self.db.close()
