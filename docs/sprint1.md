# Sprint 1 — The MBPP MVP (D1: Orchestrator)

## The goal

The goal is an agent that reads an MBPP task, asks an LLM to solve it, tests the code
and writes `solution.json`.

An LLM can only take text in and give text out. It can't run code or check its own
work. **The agent is the program around the LLM** that runs the code and shows the
LLM what happened, so the LLM can fix its own mistakes.

```text
                ┌──────────────────────────────────────────────┐
  task.json ──► │                  AGENT (us)                  │ ──► solution.json
                │                                              │
                │   ┌─────────┐    ┌────────┐   ┌───────────┐  │
                │   │ THOUGHT │──► │  CODE  │──►│OBSERVATION│  │
                │   └─────────┘    └────────┘   └─────┬─────┘  │
                │        ▲                            │        │
                │        └────────────────────────────┘        │
                │          repeat until final_answer()         │
                └──────────────────────────────────────────────┘
```

Example task given by the moulinette:

```json
{
  "task_id": 2,
  "task_definition": "Write a function to find the shared elements from two lists.",
  "function_definition": "def similar_elements(a, b):",
  "test_list": ["assert set(similar_elements((3,4,5,6),(5,7,4,10))) == set((4,5))"]
}
```

---

## Step 1 — THOUGHT: ask the LLM

We send the whole conversation to the LLM API: the system prompt, the task and every
previous step. The LLM answers with its reasoning followed by a code block.

```text
   our program                                   LLM API (Groq, OpenRouter…)
 ┌──────────────────────┐   HTTP POST           ┌──────────────────────┐
 │ messages = [         │ ────────────────────► │                      │
 │   system prompt,     │   + stop=["<end_code>"]│     the model        │
 │   task,              │                       │     generates text   │
 │   step 1, step 2 …   │ ◄──────────────────── │                      │
 │ ]                    │   reply text          └──────────────────────┘
 └──────────────────────┘   + input/output tokens
```

LLM reply:

````text
Thought: I'll use a set intersection, then test it.
```python
code = """
def similar_elements(a, b):
    return tuple(set(a) & set(b))
"""
print(run_tests(code, test_list))
```<end_code>
````

**Key points**

- The **system prompt** is the instruction manual. It tells the LLM the reply format
  (Thought, then code, then `<end_code>`), the available functions (`run_tests`,
  `final_answer`) and gives one short example.
- `stop=["<end_code>"]` makes the API stop generating there. Without it, the LLM
  **invents** a fake observation ("tests passed!") instead of waiting for the real one.
- Record the token counts for every call. The MBPP limit is **6,000 input tokens in
  total**, and the whole history is re-sent at every step, so the total grows fast.

---

## Step 2 — CODE: extract the Python

The LLM reply is plain text. We extract only the Python code from it.

```text
 ┌────────────────────────────────┐                 ┌──────────────────────────┐
 │ Thought: I'll use a set ...    │                 │ code = """               │
 │ ```python                      │  extract_code() │ def similar_elements(..  │
 │ code = """ ... """             │ ──────────────► │ """                      │
 │ print(run_tests(code, ...))    │   (regex)       │ print(run_tests(code,..))│
 │ ```<end_code>                  │                 └──────────────────────────┘
 └────────────────────────────────┘                       ready for the sandbox
             llm_output                                      sandbox_input
```

**Key points**

- For Sprint 1, a regex that finds ```` ```python ... ``` ```` is enough. Other formats
  (XML, JSON tool calls, ReAct) come in Sprint 2.
- If there is **no code block**, don't crash. Send a message back to the LLM, such as
  *"No valid code block found, please answer with a \`\`\`python block"*, and continue
  the loop.

---

## Step 3 — OBSERVATION: run it and feed back the result

The sandbox (D2's part) runs the code safely and captures what it printed and any errors.
That result goes back into the conversation, and the loop starts again at Step 1.

```text
 ┌──────────────┐  code   ┌───────────────────────┐  run_tests  ┌───────────┐
 │  our loop    │ ──────► │       SANDBOX (D2)    │ ──────────► │ MCP tool  │
 │              │         │  exec() in a safe     │ ◄────────── │ run_tests │
 │              │ ◄────── │  namespace, captures  │             └───────────┘
 └──────┬───────┘ result  │  stdout / stderr      │
        │                 └───────────────────────┘
        │  messages += [llm reply, "Observation: {success: true, ...}"]
        ▼
   back to Step 1
```

**The loop ends** when one of these happens:

```text
  sandbox result
       │
       ├── final_answer(code) was called ──► DONE: write solution.json  ✅
       ├── step == max_iterations (10)   ──► STOP: write what we have   ⚠️
       ├── token budget almost used      ──► STOP                        ⚠️
       └── otherwise                     ──► next step (back to Step 1)
```

**Key points**

- `final_answer()` is a function **inside the sandbox** (not an MCP tool). Calling it
  tells our loop that the task is finished.
- Every step is saved as a `StepMetrics` entry (`llm_output`, `sandbox_input`,
  `sandbox_output`, tokens, `retries`, `model_name`, `api_url`). Evaluators read
  these to check that the LLM really did the work.
- Until D2's sandbox is ready, use a **stub**: a plain `exec()` that captures `print`.

---

## What D1 builds in Sprint 1

```text
 agent_mbpp (CLI)
   │  --task-file  --output  --model-name  --provider-url
   ▼
 ┌────────────┐   ┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
 │ prompt.py  │   │ llm_client.py│   │  extract.py  │   │    agent.py      │
 │ system     │   │ ask(messages)│   │ extract_code │   │ the loop that    │
 │ prompt     │   │ → text,tokens│   │ (text)→code  │   │ ties it together │
 └────────────┘   └──────────────┘   └──────────────┘   └────────┬─────────┘
                                                                 │
                                                       sandbox.execute(code)
                                                         (stub → D2 later)
```

- [x] `llm_client.py`: call an OpenAI-compatible API and return the text and token counts
- [x] `prompt.py`: a short system prompt plus one example
- [x] `extract.py`: pull out the ```` ```python ```` block and handle the "no code" case
- [ ] `agent.py`: the loop with `max_iterations`, the token budget and `final_answer`
- [ ] Write `solution.json` (`SolutionOutput` + `StepMetrics`)
- [ ] Agree on the `sandbox.execute(code)` interface with D2

**MBPP limits:** 10 iterations · 6,000 input tokens · 1,500 output tokens · 120 s
