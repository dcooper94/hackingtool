"""Schema helpers for normalising tool metadata."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RunProfile:
    name: str
    command: str
    description: str = ""
    requires_target: bool = False


@dataclass
class ToolSchema:
    name: str
    category: str = "uncategorised"
    description: str = ""
    tags: list[str] = field(default_factory=list)
    supported_os: list[str] = field(default_factory=lambda: ["linux", "macos"])
    requires_root: bool = False
    requires_network: bool = False
    requires_api_key: bool = False
    project_url: str = ""
    install_commands: list[str] = field(default_factory=list)
    run_profiles: list[RunProfile] = field(default_factory=list)
    healthcheck_commands: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def schema_from_tool(tool: Any, category: str = "") -> ToolSchema:
    run_commands = list(getattr(tool, "RUN_COMMANDS", []) or [])
    profiles = []
    explicit = getattr(tool, "RUN_PROFILES", None)
    if explicit:
        for item in explicit:
            if isinstance(item, RunProfile):
                profiles.append(item)
            elif isinstance(item, dict):
                profiles.append(RunProfile(**item))
    else:
        profiles = [RunProfile(name=f"Command {i}", command=cmd) for i, cmd in enumerate(run_commands, start=1)]
    return ToolSchema(
        name=getattr(tool, "TITLE", tool.__class__.__name__),
        category=category,
        description=getattr(tool, "DESCRIPTION", ""),
        tags=list(getattr(tool, "TAGS", []) or []),
        supported_os=list(getattr(tool, "SUPPORTED_OS", ["linux", "macos"])),
        requires_root=bool(getattr(tool, "REQUIRES_ROOT", False)),
        requires_network=bool(getattr(tool, "REQUIRES_NETWORK", False)),
        requires_api_key=bool(getattr(tool, "REQUIRES_API_KEY", False)),
        project_url=getattr(tool, "PROJECT_URL", ""),
        install_commands=list(getattr(tool, "INSTALL_COMMANDS", []) or []),
        run_profiles=profiles,
        healthcheck_commands=list(getattr(tool, "HEALTHCHECK_COMMANDS", []) or []),
    )
