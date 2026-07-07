# Pass 2 Changelog

## Added

- Workspace management foundation in `workspace.py`.
- Command execution and artifact logging in `command_runner.py`.
- Tool metadata schema helpers in `tool_schema.py`.
- CLI workspace manager available from the main menu with `w`.
- Active workspace and scope display in CLI and GUI.
- Per-command result folders under `~/.hackingtool/workspaces/<workspace>/results/`.
- Per-workspace `history.jsonl` command log.
- CLI health check action for tools.
- GUI terminal output capture into workspace artifacts.
- Project validation script at `scripts/healthcheck.py`.
- Detailed implementation roadmap at `docs/IMPLEMENTATION_PLAN.md`.

## Changed

- CLI install, uninstall, update, and run flows now use the shared command runner where practical.
- CLI tool runs now stream output while also saving artifacts.
- Workspace scope can warn or block out-of-scope command targets depending on `block_out_of_scope` in config.
- Default config now includes active workspace and scope blocking options.

## Not completed in this pass

- Full conversion of every existing tool into a declarative plugin schema.
- Full GUI workspace editor.
- Advanced parameter builders for every tool.
- Markdown/HTML/PDF reporting.

These are intentionally split into later phases to keep this pass testable and avoid destabilising the current launcher.
