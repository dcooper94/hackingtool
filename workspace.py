"""Workspace, scope, run history, and artifact management for HackingTool.

This module deliberately uses only the Python standard library so it works on
fresh Kali/Raspberry Pi installs before optional dependencies are installed.
"""
from __future__ import annotations

import ipaddress
import json
import os
import re
import socket
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from constants import USER_CONFIG_DIR

WORKSPACES_DIR = USER_CONFIG_DIR / "workspaces"
ACTIVE_WORKSPACE_FILE = USER_CONFIG_DIR / "active_workspace"
DEFAULT_WORKSPACE_NAME = "default"

_HOST_RE = re.compile(r"(?<![A-Za-z0-9_.-])([A-Za-z0-9][A-Za-z0-9_.-]{1,253})(?![A-Za-z0-9_.-])")
_IPV4_RE = re.compile(r"(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?(?!\d)")
_IPV6_RE = re.compile(r"(?<![A-Fa-f0-9:])(?:[A-Fa-f0-9]{0,4}:){2,}[A-Fa-f0-9]{0,4}(?:/\d{1,3})?(?![A-Fa-f0-9:])")


@dataclass
class Workspace:
    name: str
    description: str = "Default HackingTool workspace"
    scope: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @property
    def safe_name(self) -> str:
        return safe_workspace_name(self.name)

    @property
    def path(self) -> Path:
        return WORKSPACES_DIR / self.safe_name

    @property
    def results_dir(self) -> Path:
        return self.path / "results"

    @property
    def history_file(self) -> Path:
        return self.path / "history.jsonl"

    @property
    def metadata_file(self) -> Path:
        return self.path / "workspace.json"


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def safe_workspace_name(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_.-]+", "-", name.strip()).strip(".-")
    return cleaned or DEFAULT_WORKSPACE_NAME


def ensure_workspace_dirs(workspace: Workspace) -> None:
    workspace.path.mkdir(parents=True, exist_ok=True)
    workspace.results_dir.mkdir(parents=True, exist_ok=True)
    (workspace.path / "notes").mkdir(parents=True, exist_ok=True)
    (workspace.path / "findings").mkdir(parents=True, exist_ok=True)


def save_workspace(workspace: Workspace) -> Workspace:
    ensure_workspace_dirs(workspace)
    workspace.updated_at = datetime.now(timezone.utc).isoformat()
    workspace.metadata_file.write_text(json.dumps(asdict(workspace), indent=2, sort_keys=True))
    return workspace


def load_workspace(name: str) -> Workspace:
    safe = safe_workspace_name(name)
    path = WORKSPACES_DIR / safe / "workspace.json"
    if not path.exists():
        ws = Workspace(name=safe)
        return save_workspace(ws)
    data = json.loads(path.read_text())
    return Workspace(**data)


def get_active_workspace() -> Workspace:
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if ACTIVE_WORKSPACE_FILE.exists():
        raw = ACTIVE_WORKSPACE_FILE.read_text().strip()
        if raw:
            return load_workspace(raw)
    ws = load_workspace(DEFAULT_WORKSPACE_NAME)
    set_active_workspace(ws.name)
    return ws


def set_active_workspace(name: str) -> Workspace:
    ws = load_workspace(name)
    USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    ACTIVE_WORKSPACE_FILE.write_text(ws.safe_name)
    return ws


def list_workspaces() -> list[Workspace]:
    if not WORKSPACES_DIR.exists():
        return [get_active_workspace()]
    results: list[Workspace] = []
    for item in sorted(WORKSPACES_DIR.iterdir()):
        meta = item / "workspace.json"
        if meta.exists():
            try:
                data = json.loads(meta.read_text())
                results.append(Workspace(**data))
            except Exception:
                continue
    if not results:
        results.append(get_active_workspace())
    return results


def create_result_dir(tool_name: str, command_index: int = 1, workspace: Workspace | None = None) -> Path:
    ws = workspace or get_active_workspace()
    ensure_workspace_dirs(ws)
    tool_slug = safe_workspace_name(tool_name).lower()
    result_dir = ws.results_dir / tool_slug / f"{utc_stamp()}-{command_index:02d}"
    result_dir.mkdir(parents=True, exist_ok=True)
    return result_dir


def append_history(record: dict[str, Any], workspace: Workspace | None = None) -> None:
    ws = workspace or get_active_workspace()
    ensure_workspace_dirs(ws)
    payload = dict(record)
    payload.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
    with ws.history_file.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(payload, sort_keys=True) + "\n")


def read_history(limit: int = 50, workspace: Workspace | None = None) -> list[dict[str, Any]]:
    ws = workspace or get_active_workspace()
    if not ws.history_file.exists():
        return []
    rows: list[dict[str, Any]] = []
    for line in ws.history_file.read_text(errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return rows[-limit:]


def set_scope(scope_items: Iterable[str], workspace: Workspace | None = None) -> Workspace:
    ws = workspace or get_active_workspace()
    cleaned = []
    for item in scope_items:
        s = item.strip()
        if s and s not in cleaned:
            cleaned.append(s)
    ws.scope = cleaned
    return save_workspace(ws)


def _scope_networks(scope: Iterable[str]) -> tuple[list[ipaddress._BaseNetwork], list[str]]:
    nets = []
    hosts = []
    for item in scope:
        raw = item.strip().lower()
        if not raw:
            continue
        try:
            nets.append(ipaddress.ip_network(raw, strict=False))
            continue
        except ValueError:
            pass
        hosts.append(raw)
    return nets, hosts


def extract_targets_from_command(command: str) -> list[str]:
    targets: list[str] = []
    for match in _IPV4_RE.findall(command) + _IPV6_RE.findall(command):
        if match not in targets:
            targets.append(match)
    # Conservative hostname extraction: skip flags, shell keywords, URLs' schemes, and common executable names.
    skip = {"sudo", "python", "python3", "bash", "sh", "cd", "git", "clone", "curl", "wget", "http", "https"}
    for match in _HOST_RE.findall(command):
        token = match.strip().lower()
        if token in skip or token.startswith("-") or token.isdigit() or "." not in token:
            continue
        if token not in targets:
            targets.append(token)
    return targets


def target_in_scope(target: str, scope: Iterable[str]) -> bool:
    nets, hosts = _scope_networks(scope)
    t = target.strip().lower()
    try:
        if "/" in t:
            target_net = ipaddress.ip_network(t, strict=False)
            return any(target_net.subnet_of(net) or target_net == net for net in nets)
        ip = ipaddress.ip_address(t)
        return any(ip in net for net in nets)
    except ValueError:
        pass
    if t in hosts:
        return True
    return any(t.endswith("." + h.lstrip("*.")) for h in hosts if h.startswith("*."))


def scope_check(command: str, workspace: Workspace | None = None) -> dict[str, Any]:
    ws = workspace or get_active_workspace()
    targets = extract_targets_from_command(command)
    if not ws.scope:
        return {"mode": "no_scope", "targets": targets, "out_of_scope": [], "allowed": True}
    out = [target for target in targets if not target_in_scope(target, ws.scope)]
    return {"mode": "enforced", "targets": targets, "out_of_scope": out, "allowed": not out}
