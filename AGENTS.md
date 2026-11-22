# AGENTS.md

The full repository instructions are in [CLAUDE.md](CLAUDE.md). This file repeats only what an agent needs before it reads that.

## Test commands

```
python -m unittest discover -s tests -t .
```

(`python3` on Linux.) Python 3.12 or newer, standard library only. There is no lint step, no build step and no package manifest. Do not add pip or npm dependencies.

## Run

```
python -m design_canvas --data-dir ./data --port 8750
```

Both arguments are required. `--port 0` picks a free port and prints the address. The server binds `127.0.0.1` only. Stop it with Ctrl+C.

## Ticket work

To implement an issue, follow [.claude/skills/implement-ticket/SKILL.md](.claude/skills/implement-ticket/SKILL.md) and the section "Agent roles and ticket work" in [CLAUDE.md](CLAUDE.md). Each role file in `.claude/agents/` starts with a section "In this repository". An agent that cannot launch those roles as subagents does each step itself with that section as its checklist, and says so in the pull request.

## Loop conventions

- The loop runs at L1: report-only, started by hand. It proposes; it does not label, comment, close, edit source, push or merge.
- No scheduler and no workflow file is installed. Do not add one without the owner's approval.
- See [LOOP.md](LOOP.md) for the manual command and the human gates.
