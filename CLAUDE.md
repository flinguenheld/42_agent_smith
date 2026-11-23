# CLAUDE.md

42 project **agent_smith**: an LLM agent that solves MBPP and SWE-bench tasks
(see `docs/subject.md`). Two-person team; the current plan is in
`docs/sprint1.md`.

## Workflow

1. **Talk first.** Propose the change in the chat: what and where
   (`file:line`), a small snippet, and why. When there is a real choice,
   give the options and a recommendation.
2. **Wait for an explicit go** ("write it", "fix it", "add it", "do it").
   "Ok", "let's do X" or "good idea" are not a go. "Just talk" means no
   edits at all. When unsure, ask.
3. **One step at a time.** One small change per reply; build a feature,
   then use it, as separate steps. List other ideas at the end, for later.
4. **Minimal code**, with the *why* of each non-obvious choice, so both of
   us can defend it at the review.
5. **Check and sum up:** run `make test` and `make lint`, then say what
   changed per file and why.

Always: never commit, push or touch git history (we commit ourselves).
Read-only commands (`make test`, `make lint`, `git diff`, reading files) are
fine without asking. If a request conflicts with `docs/subject.md`, say so
first.

## English

Start each reply by correcting the mistakes in our message: our wording → the
correct wording, with a few words on why. Only real mistakes, at most ~5.
Skip it when there's nothing to fix.

## Project

```text
src/
├─ agent_mbpp/     entry point: python -m agent_mbpp (thin)
└─ agent_smith/    the library
   ├─ cli.py       CliArgs: the 4 flags, shared by every entry point
   ├─ agent/       the loop (think → extract → observe), budget, report
   ├─ llm/         LLMClient, Config (.env keys, base URL)
   ├─ display/     Display (colors, debug levels), pretty_format
   ├─ sandbox/     D2's part
   └─ data.py · models.py
```

```sh
make install     # uv sync
make run_gemini  # python -m agent_mbpp on $(TASK), Gemini (see README)
make test        # uv run pytest
make lint        # flake8 + mypy on src/
```

Constraints from the subject:

- CLI: `python -m agent_mbpp --task-file --output --model-name
  --provider-url` (same 4 flags for `agent_swebench`). `--provider-url` is
  a base URL (`…/v1`).
- Sandbox security uses **only the standard library** (no RestrictedPython,
  no Docker as the security mechanism).
- **No API keys in the code**: load them from `.env` via `llm/config.py`.
- MBPP limits: 10 iterations, 6,000 input tokens, 1,500 output tokens, 120 s.

## Code style

- **Small files**: one responsibility per module. If a file does two things,
  propose a split.
- **Small functions**: one job each, with an explicit name.
- **DRY**: no copy-pasted logic. Constants live in `src/agent_smith/data.py`,
  settings in `llm/config.py`. Before adding a helper, check whether one
  exists.
- **Coherence**: new code must look like the existing code. Follow the
  patterns already in the project:
  - Python 3.10, full type hints, must pass `make lint` (flake8 + mypy),
    lines ≤ 79 characters.
  - A docstring on every public class and function (module docstrings are
    optional).
  - Each module raises its own exception (`class LLMClientError(Exception)`)
    instead of returning error codes or printing.
  - `@dataclass` for simple data, Pydantic for config and output models
    (`SandboxConfig`, `StepMetrics`, `SolutionOutput`).
  - Output to the terminal goes through `Display` (`display/`), not bare
    `print`. `Display.debug` filters by `DebugLevel` (`DEBUG_LEVEL` in
    `data.py`).
- **Tests**: pytest. Only write new tests when we ask, but `make test` must
  stay green.

## Documentation

Docs live in `docs/`. Their purpose is to **understand** the project and
**explain it to the other teammate**, so a part one of us built can be
understood and defended by both.

- **English**, in the style of `docs/sprint1.md` and `docs/glossary.md`.
- **Short and concise**: plain words, short sentences, one idea per section.
  Cut anything that doesn't help the reader understand.
- **Explain with ASCII diagrams** (boxes and arrows in a ```` ```text ````
  block). Use Mermaid only when an ASCII diagram would be too messy.
- **Glossary** (`docs/glossary.md`): when a new term comes up, propose an
  entry and **ask before adding it**. Keep alphabetical order and the existing
  format (`### Term`, short definition, links, `---` between entries).
- **Checklists** (`docs/team_plan_blocks.md`, `docs/sprint1.md`,
  `docs/check_list_sujet.md`): when a task looks done (code + tests green),
  say which box could be ticked and **ask before ticking it**. Do the same for
  new tasks to add.

## Commit messages (for reference, we write them)

`<Module> - <Verb> <what>`, e.g. `LLMClient - Add stopsequences`.
