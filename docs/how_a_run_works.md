# How a run works

What happens between the command and `solution.json`, phase by phase.
The example is MBPP; SWE-bench will reuse phases 1, 3 and 4.

```sh
uv run python -m agent_mbpp --task-file task.json --output solution.json \
    --model-name NAME --provider-url URL
```

---

## The big picture: 4 phases

```text
 ┌─────────────┐   ┌─────────────┐   ┌──────────────────┐   ┌─────────────┐
 │ 1. ARGS     │──►│ 2. PREPARE  │──►│ 3. LOOP          │──►│ 4. WRITE    │
 │ read flags  │   │ task, keys, │   │ think → code →   │   │ solution.   │
 │ check paths │   │ sandbox     │   │ observe (≤ 10×)  │   │ json        │
 └──────┬──────┘   └──────┬──────┘   └────────┬─────────┘   └──────┬──────┘
        │ bad             │ bad               │ API error /        │
        ▼                 ▼                   │ limit reached      ▼
     exit 2            exit 1                 └─► still goes to 4  exit 0
```

If we can't **start**, we stop with an error (exit 2 or 1).  
Once the loop has started, we **always** write `solution.json`, even on failure.

---

## Phase 1 — ARGS: read the command line

```text
   the 4 flags                  checks                      result
 ┌────────────────┐     ┌─────────────────────┐      ┌─────────────────┐
 │ --task-file    │     │ all 4 given?        │ yes  │ typed arguments │
 │ --output       │ ──► │ task file exists?   │ ───► │ ready to use    │
 │ --model-name   │     │ output folder OK?   │      └─────────────────┘
 │ --provider-url │     └──────────┬──────────┘
 └────────────────┘                │ no
                                   ▼
                    error + help, exit 2 (nothing started)
```

Every argument is checked **before** anything expensive starts
([fail fast](glossary.md#fail-fast)).

---

## Phase 2 — PREPARE: task, config, sandbox

```text
           ┌─ task:    read and check the JSON file ─┐
 PREPARE ──┼─ config:  provider (URL), keys (.env) ──┼──► all OK ──► LOOP
           └─ sandbox: start a safe place for code ──┘
                          │ any problem
                          ▼
                 error message, exit 1
```

- The URL given is a **base URL**: we add `/chat/completions` to send
  requests, and keep the base for the report.
- If the keys or the provider are wrong, the message says how to fix it
  ("Add a line: GROQ_API_KEY=...").

---

## Phase 3 — LOOP: think, code, observe

**Before the first step:**

```text
 ┌───────────┐ ┌───────────────┐ ┌──────────────┐ ┌──────────────────┐
 │ clock     │ │ token budget  │ │ empty report │ │ conversation:    │
 │ 120 s     │ │ 6,000 / 1,500 │ │              │ │ rules + the task │
 └───────────┘ └───────────────┘ └──────────────┘ └──────────────────┘
```

**Each step** (up to 10):

```text
        ┌──────────────── no final answer: next step ───────────────┐
        ▼                                                           │
  ┌───────────┐      ┌────────────┐  code   ┌──────────────────┐    │
  │ THINK     │ ───► │ CODE       │ ──────► │ OBSERVE          │ ───┘
  │ ask the   │      │ find the   │         │ run it, send the │
  │ LLM       │      │ Python     │         │ result back      │
  └───────────┘      └─────┬──────┘         └────────┬─────────┘
                           │ no code                 │ final answer
                           ▼                         ▼
               "please answer with a              WRITE ✅
                Python block" → next step

  before each step: time left? tokens left? if not ──► WRITE (failed)
```

**Each step is saved in two places:**

| | Conversation | Report |
|---|---|---|
| For | the LLM | the evaluators |
| When | sent again at **every** call | written **once**, at the end |
| Contains | what was said | what happened, and its cost |

**How the loop ends:**

```text
   final answer given  ─► success                           ✅
   10 steps done       ─► failed: "max iterations reached"
   no tokens left      ─► failed: "token budget exhausted"
   120 s passed        ─► failed: "timeout"
   API keeps failing   ─► failed: "API error: ..."
```

The conversation grows by 2 messages per step (the reply + our answer) and
is sent again each time. That's why input tokens grow fast, and why we have
a budget.

---

## Phase 4 — WRITE: solution.json

```text
 all the steps ──► one summary ──┬──► solution.json   JSON, for the moulinette
 (+ error, if any)   success,    │
                     totals,     └──► terminal        readable, for debugging
                     each step
                                       exit 0, even if the task was not solved
```

Not solving the task is not a crash: the result is in the file.

---

## Example: a task solved in 2 steps

```text
 step 1  THINK    LLM: "Thought: ... run_tests(code, tests)"
         OBSERVE  sandbox: "1 test failed: ..."
         saved    step 1 in the report             conversation: 4 messages

 step 2  THINK    LLM: "Thought: fix the order ... final_answer(code)"
         OBSERVE  sandbox: final answer given       ✅ stop
         saved    step 2 in the report             conversation: 6 messages

 WRITE   summary: success, 2 steps ──► solution.json, exit 0
```

---

## Exit codes

| Code | Meaning | When |
|---|---|---|
| 0 | `solution.json` written (task solved or not) | phase 4 |
| 1 | can't start: bad task file or config | phase 2 |
| 2 | bad arguments: missing flag or wrong path | phase 1 |
