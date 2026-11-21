# Team Organisation & Roadmap

This page shows how we split the **Agent Smith** project so the two of us can work
well together:

1. **A way to split the work** (Split by Blocks);
2. **A step-by-step roadmap**, so we know in which order to build the technical parts
   without losing focus.

***

## Roles

| Role                       | Scope                                                                                                                                           |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| **D1: The Orchestrator**   | LLM API client, multi-format parsing, API key rotation, the `Thought → Code → Observation` loop, system prompt, benchmark.                      |
| **D2: The Sandbox**        | Restricted Python environment (CLI REPL + execution engine), resource limits, AST analysis, path isolation, internal MCP client.               |
| **D3: MCP Ecosystem & Tools** (D1 + D2 together) | MCP servers (`stdio` and `HTTP`), file / code search / test tools, SWE-bench Docker containers.                           |

***

## 1. How we split the work between two people

### Approach: Split by Blocks (end-to-end features)

We don't split the work only by technical layer, where each of us would code alone for
3 weeks with nothing to test together. Instead, the team moves forward in **feature
milestones** of growing difficulty.

### Sprint 1: The MBPP MVP

**Goal:** Prove the core idea and get a first end-to-end success on a simple
algorithm task.

**D1 — Orchestrator**

- [ ] Basic iterative loop
- [ ] First prompt

**D2 — Sandbox**

- [ ] Basic isolated `exec()`
- [ ] `final_answer()`
- [ ] Capture `stdout` / `stderr`

**D3 — MCP & Tools (together)**

- [ ] First `run_tests` tool for MBPP

**Deliverable:**

- [ ] An agent that reads an MBPP JSON file, writes code, runs the tests and produces
      a first valid solution.

### Sprint 2: Security & MCP Standard

**Goal:** Follow the subject's rules strictly, build the sandbox security and the full
MCP protocol.

**D1 — Orchestrator**

- [ ] Full `StepMetrics`
- [ ] Full `SolutionOutput`
- [ ] Key rotation
- [ ] Multi-format parser

**D2 — Sandbox**

- [ ] AST analysis
- [ ] Block builtins
- [ ] Block imports
- [ ] Block paths
- [ ] Block network
- [ ] Timeouts
- [ ] REPL `uv run sandbox`

**D3 — MCP & Tools (together)**

- [ ] `mcp_tools_mbpp.py` server over `stdio`
- [ ] `mcp_tools_mbpp.py` server over `HTTP`
- [ ] Dynamic discovery

**Deliverables:**

- [ ] A robust and secure architecture that passes `exam_sandbox.sh`
- [ ] … and `exam_mbpp.sh` (≥ 4/5)

### Sprint 3: The SWE-bench Challenge & Benchmark

**Goal:** Face real repositories inside Docker, navigate their code, and benchmark
several models.

**D1 — Orchestrator**

- [ ] Tune the SWE-bench prompt
- [ ] Handle long contexts (`300k` tokens)
- [ ] Test campaign on the 5 models
- [ ] Write `BENCHMARK_REPORT.md`

**D2 — Sandbox**

- [ ] Integrate the sandbox with the Docker workflow
- [ ] Advanced error feedback

**D3 — MCP & Tools (together)**

- [ ] `mcp_tools_swebench.py` server with the 9 mandatory tools
- [ ] Clean lifecycle of the Docker containers

**Deliverables:**

- [ ] Solve real GitHub issues on our own (≥ 2/3 on `exam_swebench.sh`)
- [ ] Generate clean Git patches
- [ ] Full evaluation report

#### Why this approach

The team **always has a working version that can be tested end to end**, so nobody
works in a tunnel. From the end of Sprint 1, the agent runs on MBPP; Sprint 2 locks
down security and the MCP standard; Sprint 3 puts all our energy into the big
SWE-bench challenge and the model comparison.

***

## 2. Step-by-step roadmap

This is the recommended order to build the project piece by piece without losing
focus:

### Step 0 — Infrastructure Foundations *(D1 + D2)*

Before writing any code that calls an LLM over the network, the software
infrastructure must be set up properly:

- [x] 1. Initialise the repository with **`uv`** and **Python 3.10** (strict
      requirements of chapter IV.1).
- [ ] 2. Set up the **`.env`** file to load the API keys safely, and lock down the
      **`.gitignore`** right away (to exclude `.env`, caches, generated outputs and
      images).
- [ ] 3. Model the data structures by writing all the **Pydantic models** the subject
      requires: `SandboxConfig`, `MBPPTaskInput`, `SWEBenchTaskInput`, `StepMetrics`
      and `SolutionOutput`.

### Step 1 — Local Sandbox Prototype *(D2)*

Build the core of the sandbox:

- [ ] 1. An isolated function that takes any Python code string, checks its syntax
      tree (`ast`), and runs it in a restricted namespace (filtered `__builtins__`,
      imports controlled by `authorized_imports`, file access limited to
      `allowed_directories`, network cut off).
- [ ] 2. Capture `stdout` and `stderr` cleanly, enforce the timeout (`30s`) and the RAM
      limit (`512 MB`) with an isolated process, and return clear error messages
      without ever crashing the parent process.
- [ ] 3. Inject the built-in `final_answer()` function and provide the interactive
      REPL mode (`uv run sandbox`).

### Step 2 — The Orchestrator and the Agent Loop *(D1)*

Move the effort to the agent's brain:

- [ ] 1. Build the **multi-format code extractor**: it reads the raw LLM reply
      (`llm_output`) and pulls out the Python code, or converts the other formats
      (XML `<invoke>`, JSON/Hermes `<tool_call>`, ReAct `Action:`) into Python
      function calls.
- [ ] 2. Write the **multi-provider LLM client** with smooth API key rotation,
      *exponential backoff* on `429`/`5xx` errors, `stop_sequences` settings, and
      exact counting of tokens and latency (`StepMetrics`).
- [ ] 3. Connect this API loop to the sandbox to check the first autonomous
      `Thought → Code → Observation` sequences.

### Step 3 — The Turning Point: MCP Protocol Integration *(D2 + D3 together)*

Connect the sandbox to the outside world:

- [ ] 1. Add an **MCP client** to the sandbox that supports both the **`stdio`** and
      **`Streamable HTTP`** transports. *(D2)*
- [ ] 2. Create the first MCP server (`mcp_tools_mbpp.py`) exposing `run_tests`, to
      check the full **MCP handshake**. *(D3 together)*
- [ ] 3. Use dynamic discovery (`tools/list`, `resources/list`, `prompts/list`) to
      generate the **Sandbox Manual** automatically and inject it into the model's
      system prompt, and expose each MCP tool as a Python function the sandbox code
      can call. *(D2)*

### Step 4 — The Final Challenge: SWE-bench, Docker & Benchmark Report *(D1 + D2)*

Tackle the most ambitious part of the subject:

- [ ] 1. Write `mcp_tools_swebench.py` with the **9 mandatory tools**, with careful
      output formats (`cat -n`, `grep`) and error messages that guide the LLM.
      *(D3 together)*
  - [ ] `read_file`
  - [ ] `edit_file`
  - [ ] `list_files`
  - [ ] `search_code`
  - [ ] `search_function_or_class_definition_in_code`
  - [ ] `find_references`
  - [ ] `run_tests`
  - [ ] `get_patch`
  - [ ] `run_command`
- [ ] 2. Handle the SWE-bench Docker containers (mount or access `${TESTBED_PATH}`,
      generate the diff with `git -c core.fileMode=false diff`, and **always clean up
      the container** after the run). *(D3 together)*
- [ ] 3. Test and iterate first on the tasks the subject recommends
      (`sympy__sympy-14711`, `sympy__sympy-13480`, `pydata__xarray-4629`), checking
      the first 3 to 5 iterations. *(D1)*
- [ ] 4. Run the cross-evaluation of at least **5 models on at least 3 SWE-bench
      tasks**, keep the matching `solution.json` files, and write
      **`BENCHMARK_REPORT.md`** and the final **`README.md`** in English.
      *(D1, README together)*
