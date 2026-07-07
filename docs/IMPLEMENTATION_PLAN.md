# HackingTool Product Implementation Plan

## Product intent

HackingTool is intended to become a unified cybersecurity operator workbench: a GUI and CLI application that helps an operator browse, install, validate, run, and track a curated catalogue of security tools.

The existing project already works as a tool launcher. The missing product layer is the operational model around tool usage: workspaces, scope, command history, captured outputs, health checks, structured run profiles, and reporting.

## Implementation phases

### Phase 1 — Durable operator foundation

Implemented in this pass.

- Add workspace model under `~/.hackingtool/workspaces/`.
- Add active workspace tracking.
- Add per-workspace scope entries.
- Add per-run output directories.
- Capture command, stdout, stderr, metadata, duration, exit code, and scope result.
- Append JSONL command history per workspace.
- Add command execution wrapper for CLI flows.
- Add GUI terminal artifact capture and history recording.
- Add initial tool schema helpers for future plugin/catalogue conversion.
- Add health check script for syntax/import/workspace validation.

### Phase 2 — Tool catalogue normalisation

- Convert hardcoded class metadata into a unified schema.
- Add `RUN_PROFILES` for high-value tools.
- Add `HEALTHCHECK_COMMANDS` to tools where binary/service/config validation matters.
- Add `requires_target`, `requires_root`, `requires_network`, `requires_api_key`, and `supported_os` consistently.
- Export the registry as JSON for GUI/search/reporting.

### Phase 3 — Command builders

- Replace plain `RUN_COMMANDS` for common tools with profile-driven builders.
- Add target prompts and output-folder interpolation.
- Add workspace-aware defaults such as `-oA`/`-oJ`/`--output` where tools support it.
- Add dry-run command preview.

### Phase 4 — Installer orchestration

- Add install queue state.
- Store install logs as artifacts.
- Add retry failed/skip installed.
- Add package-manager abstraction for apt, brew, pip/uv, gem, go, docker.
- Add offline/fallback behaviour where possible.

### Phase 5 — Reporting

- Export workspace history and results to Markdown.
- Add HTML/PDF report generation after a workspace run.
- Add tool inventory export.
- Add findings folder and finding templates.

### Phase 6 — Plugin architecture

- Load external tool definitions from `plugins/*.yaml` or `plugins/*.json`.
- Keep Python classes only for advanced tools needing custom behaviour.
- Make the CLI and GUI consume the same registry.

## Validation gates

Every pass should run:

```bash
python3 -m compileall -q .
python3 scripts/healthcheck.py
```

Optional GUI validation on a host with Tk installed:

```bash
python3 -m py_compile gui.py
python3 gui.py
```
