# Team Organisation & Roadmap

This page shows how to split the **Agent Smith** project so a team of 3 can work well
together:

1. **Two ways to split the work** (Split by Architecture vs Split by Blocks);
2. **A step-by-step roadmap**, so we know in which order to build the technical parts
   without losing focus.

***

## 1. How to split the work between three people

Here are two complementary ways to organise a team of three developers, refined from
the exact requirements of the subject and this documentation.

{% tabs %}
{% tab title="Approach 1 — Split by Architecture (by layer)" %}

### Approach 1: Split by Architecture

Each member owns one of the three big subsystems of the subject:

| Architectural responsibility           | Detailed technical scope                                                                                                                                                  | Required software deliverables                                                                                                                                                                                              | Focus points                                                                                                                                      |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Developer 1: The Orchestrator**      | LLM API client (OpenRouter, Groq, etc.), multi-format parsing, API key rotation, and the `Thought → Code → Observation` loop.                                              | Retry logic, code extractor (Python, XML, Hermes, ReAct), tracking of the global limits (tokens/iterations/time), `StepMetrics` & `SolutionOutput` models, system prompt engineering and `stop_sequences`.                  | Reliable network requests, parsing that survives LLM hallucinations, and an optimised context window.                                            |
| **Developer 2: The Sandbox**           | The restricted Python environment (CLI REPL + execution engine). Resource limits, static AST analysis, and path isolation.                                               | AST validator, restricted `__builtins__`, network blocking, execution timeout (`30s` per block) and RAM limit (`512 MB`), internal MCP client, dynamic manual generation, and `final_answer` injection.                     | Fully secure execution (pass `exam_sandbox.sh`), precise error capture (clear *tracebacks*), and clean handling of child processes.              |
| **Developer 3: MCP Ecosystem & Tools** | MCP servers (`stdio` and `HTTP` transports) and the tools that handle files, search code and run tests.                                                                   | `mcp_tools_mbpp.py` and `mcp_tools_swebench.py` at the root of the repository. Running and cleaning up the Docker containers for SWE-bench.                                                                                 | Mastery of the MCP / JSON-RPC protocol, the 9 mandatory tools in the exact format (`cat -n`, `grep`), and valid Git patches.                     |

#### The roles in this setup

* **Developer 1 (The Orchestrator)** focuses on intelligence and coordination. They
  handle the requests to remote models, set up smart API key rotation to get around
  the *rate limits* of free providers, and build the extractor that converts mixed
  outputs (Markdown Python blocks, XML `<invoke>` tags, JSON/Hermes `<tool_call>`
  formats, ReAct format) into Python calls for the sandbox. They also make sure the
  global task limits are respected (`120s` / `6k` tokens for MBPP; `900s` / `300k`
  tokens for SWE-bench) and produce the `SolutionOutput`.
* **Developer 2 (The Sandbox)** is the security engineer of the project. Their goal is
  a standard Python execution environment (without `RestrictedPython`) that no code
  can escape. They enforce the per-block limits (`max_execution_time_seconds = 30s`,
  `max_memory_mb = 512`) with isolated processes and system signals (`SIGTERM`,
  `SIGKILL`), validate the AST before running anything, and carefully clean the
  global namespace (`__builtins__`).
* **Developer 3 (MCP & Tools)** is the expert of the outside world and of protocols.
  They master the MCP lifecycle (`stdio` and `Streamable HTTP`) and build standalone
  servers that work with files or with the Docker containers SWE-bench requires
  (`${TESTBED_PATH}`). They turn the tool specifications into reliable functions with
  excellent *docstrings* (ACI).
  {% endtab %}

{% tab title="Approach 2 — Split by Blocks" %}

### Approach 2: Split by Blocks (end-to-end features)

We don't split the work only by technical layer, where each of us would code alone for
3 weeks with nothing to test together. Instead, the team moves forward in **feature
milestones** of growing difficulty:

| Iteration (Sprint)                           | Overall goal                                                                                    | Assigned tasks (D1, D2, D3)                                                                                                                                                                                                                                                                                                                                                                                                                                        | Sprint deliverables                                                                                                              |
| -------------------------------------------- | ----------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| **Sprint 1: The MBPP MVP**                   | Prove the core idea and get a first end-to-end success on a simple algorithm task.              | <p><strong>D1:</strong> Basic iterative loop and first prompt.<br><strong>D2:</strong> Basic isolated <code>exec()</code>, <code>final\_answer()</code> and <code>stdout</code>/<code>stderr</code> capture.<br><strong>D3:</strong> First <code>run\_tests</code> tool for MBPP.</p>                                                                                                                                                                              | An agent that reads an MBPP JSON file, writes code, runs the tests and produces a first valid solution.                          |
| **Sprint 2: Security & MCP Standard**        | Follow the subject's rules strictly, build the sandbox security and the full MCP protocol.      | <p><strong>D1:</strong> Full <code>StepMetrics</code>, <code>SolutionOutput</code>, key rotation and multi-format parser.<br><strong>D2:</strong> AST analysis, blocking of builtins/imports/paths/network, timeouts, REPL <code>uv run sandbox</code>.<br><strong>D3:</strong> <code>mcp\_tools\_mbpp.py</code> server (<code>stdio</code> & <code>HTTP</code>) and dynamic discovery.</p>                                                                       | A robust and secure architecture that passes `exam_sandbox.sh` and `exam_mbpp.sh` (≥ 4/5).                                       |
| **Sprint 3: The SWE-bench Challenge & Benchmark** | Face real repositories inside Docker, navigate their code, and benchmark several models.   | <p><strong>D1:</strong> Tune the SWE-bench prompt, handle long contexts (<code>300k</code> tokens), test campaign on the 5 models and write <code>BENCHMARK\_REPORT.md</code>.<br><strong>D2:</strong> Integrate the sandbox with the Docker workflow and advanced error feedback.<br><strong>D3:</strong> <code>mcp\_tools\_swebench.py</code> server with the 9 mandatory tools and clean lifecycle of the Docker containers.</p>                                  | Solve real GitHub issues on our own (≥ 2/3 on `exam_swebench.sh`), generate clean Git patches and a full evaluation report.      |

#### Why this approach

The team **always has a working version that can be tested end to end**, so nobody
works in a tunnel. From the end of Sprint 1, the agent runs on MBPP; Sprint 2 locks
down security and the MCP standard; Sprint 3 puts all our energy into the big
SWE-bench challenge and the model comparison.
{% endtab %}
{% endtabs %}

***

## 2. Step-by-step roadmap

This is the recommended order to build the project piece by piece without losing
focus:

### Step 0 — Infrastructure Foundations

Before writing any code that calls an LLM over the network, the software
infrastructure must be set up properly:

1. Initialise the repository with **`uv`** and **Python 3.10** (strict requirements of
   chapter IV.1).
2. Set up the **`.env`** file to load the API keys safely, and lock down the
   **`.gitignore`** right away (to exclude `.env`, caches, generated outputs and
   images).
3. Model the data structures by writing all the **Pydantic models** the subject
   requires: `SandboxConfig`, `MBPPTaskInput`, `SWEBenchTaskInput`, `StepMetrics` and
   `SolutionOutput`.

### Step 1 — Local Sandbox Prototype

Build the core of the sandbox:

1. An isolated function that takes any Python code string, checks its syntax tree
   (`ast`), and runs it in a restricted namespace (filtered `__builtins__`, imports
   controlled by `authorized_imports`, file access limited to `allowed_directories`,
   network cut off).
2. Capture `stdout` and `stderr` cleanly, enforce the timeout (`30s`) and the RAM limit
   (`512 MB`) with an isolated process, and return clear error messages without ever
   crashing the parent process.
3. Inject the built-in `final_answer()` function and provide the interactive REPL mode
   (`uv run sandbox`).

### Step 2 — The Orchestrator and the Agent Loop

Move the effort to the agent's brain:

1. Build the **multi-format code extractor**: it reads the raw LLM reply
   (`llm_output`) and pulls out the Python code, or converts the other formats (XML
   `<invoke>`, JSON/Hermes `<tool_call>`, ReAct `Action:`) into Python function calls.
2. Write the **multi-provider LLM client** with smooth API key rotation, *exponential
   backoff* on `429`/`5xx` errors, `stop_sequences` settings, and exact counting of
   tokens and latency (`StepMetrics`).
3. Connect this API loop to the sandbox to check the first autonomous
   `Thought → Code → Observation` sequences.

### Step 3 — The Turning Point: MCP Protocol Integration

Connect the sandbox to the outside world:

1. Add an **MCP client** to the sandbox that supports both the **`stdio`** and
   **`Streamable HTTP`** transports.
2. Create the first MCP server (`mcp_tools_mbpp.py`) exposing `run_tests`, to check the
   full **MCP handshake**.
3. Use dynamic discovery (`tools/list`, `resources/list`, `prompts/list`) to generate
   the **Sandbox Manual** automatically and inject it into the model's system prompt,
   and expose each MCP tool as a Python function the sandbox code can call.

### Step 4 — The Final Challenge: SWE-bench, Docker & Benchmark Report

Tackle the most ambitious part of the subject:

1. Write `mcp_tools_swebench.py` with the **9 mandatory tools** (`read_file`,
   `edit_file`, `list_files`, `search_code`,
   `search_function_or_class_definition_in_code`, `find_references`, `run_tests`,
   `get_patch`, `run_command`), with careful output formats (`cat -n`, `grep`) and
   error messages that guide the LLM.
2. Handle the SWE-bench Docker containers (mount or access `${TESTBED_PATH}`, generate
   the diff with `git -c core.fileMode=false diff`, and **always clean up the
   container** after the run).
3. Test and iterate first on the tasks the subject recommends (`sympy__sympy-14711`,
   `sympy__sympy-13480`, `pydata__xarray-4629`), checking the first 3 to 5 iterations.
4. Run the cross-evaluation of at least **5 models on at least 3 SWE-bench tasks**,
   keep the matching `solution.json` files, and write **`BENCHMARK_REPORT.md`** and the
   final **`README.md`** in English.
