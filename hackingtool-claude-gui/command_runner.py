"""Command execution helpers with artifact logging and run history."""
from __future__ import annotations

import json
import os
import shlex
import signal
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from workspace import append_history, create_result_dir, get_active_workspace, scope_check

OutputCallback = Callable[[str], None]


@dataclass
class CommandResult:
    command: str
    returncode: int
    duration_seconds: float
    result_dir: Path
    stdout_file: Path
    stderr_file: Path
    metadata_file: Path
    blocked: bool = False


def command_to_display(command: str | list[str]) -> str:
    if isinstance(command, str):
        return command
    return " ".join(shlex.quote(str(part)) for part in command)


def execute_command(
    command: str | list[str],
    *,
    tool_name: str = "manual",
    command_index: int = 1,
    cwd: str | Path | None = None,
    check_scope: bool = True,
    block_out_of_scope: bool = False,
    output_callback: OutputCallback | None = None,
) -> CommandResult:
    """Run a command, stream output, and persist command artifacts.

    Shell commands are still supported because this project stores many existing
    tool invocations as shell snippets. The runner adds auditability and scope
    checks without forcing an immediate catalogue rewrite.
    """
    display_cmd = command_to_display(command)
    workspace = get_active_workspace()
    result_dir = create_result_dir(tool_name, command_index, workspace)
    stdout_file = result_dir / "stdout.log"
    stderr_file = result_dir / "stderr.log"
    metadata_file = result_dir / "metadata.json"
    command_file = result_dir / "command.txt"
    command_file.write_text(display_cmd + "\n", encoding="utf-8")

    scope = scope_check(display_cmd, workspace) if check_scope else {"allowed": True, "targets": [], "out_of_scope": []}
    if block_out_of_scope and not scope.get("allowed", True):
        metadata = {
            "tool": tool_name,
            "command": display_cmd,
            "cwd": str(cwd or os.getcwd()),
            "scope": scope,
            "status": "blocked_out_of_scope",
            "returncode": 126,
            "duration_seconds": 0.0,
            "artifacts": {"stdout": str(stdout_file), "stderr": str(stderr_file), "command": str(command_file)},
        }
        metadata_file.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
        stdout_file.write_text("", encoding="utf-8")
        stderr_file.write_text("Command blocked because one or more targets are outside the active workspace scope.\n", encoding="utf-8")
        append_history(metadata, workspace)
        return CommandResult(display_cmd, 126, 0.0, result_dir, stdout_file, stderr_file, metadata_file, blocked=True)

    start = time.monotonic()
    stdout_fh = stdout_file.open("w", encoding="utf-8", errors="replace")
    stderr_fh = stderr_file.open("w", encoding="utf-8", errors="replace")
    try:
        proc = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd else None,
            shell=isinstance(command, str),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=None,
            text=True,
            errors="replace",
            preexec_fn=os.setsid if os.name != "nt" else None,
        )
        assert proc.stdout is not None
        for line in proc.stdout:
            stdout_fh.write(line)
            stdout_fh.flush()
            if output_callback:
                output_callback(line)
        returncode = proc.wait()
    except KeyboardInterrupt:
        if 'proc' in locals() and proc.poll() is None:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            except Exception:
                proc.terminate()
        raise
    except Exception as exc:
        returncode = 1
        stderr_fh.write(f"{type(exc).__name__}: {exc}\n")
        if output_callback:
            output_callback(f"{type(exc).__name__}: {exc}\n")
    finally:
        stdout_fh.close()
        stderr_fh.close()

    duration = round(time.monotonic() - start, 3)
    metadata = {
        "tool": tool_name,
        "command": display_cmd,
        "cwd": str(cwd or os.getcwd()),
        "scope": scope,
        "status": "completed",
        "returncode": returncode,
        "duration_seconds": duration,
        "artifacts": {"stdout": str(stdout_file), "stderr": str(stderr_file), "command": str(command_file)},
    }
    metadata_file.write_text(json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8")
    append_history(metadata, workspace)
    return CommandResult(display_cmd, returncode, duration, result_dir, stdout_file, stderr_file, metadata_file)
