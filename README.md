*This project has been created as part of the 42 curriculum by [rapoggi](https://github.com/cali-pso), [flinguen](https://www.linguenheld.net/)*

## 42_agent_smith

Autonomous reasoning, code generation, and execution.

### Usage

#### Requirements

- [uv](https://docs.astral.sh/uv/) — the **standalone** install:

```sh
    curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Installation

```sh
git clone https://github.com/flinguenheld/42_agent_smith
cd 42_agent_smith
```

Create a `.env` file at the root with the API keys of your providers,
one line per provider (several keys are separated by commas):

```sh
GEMINI_API_KEY=key1,key2,...
GROQ_API_KEY=key1
```

The variable names are listed in `Provider` (`src/agent_smith/data.py`).

> `.env` is in `.gitignore`: never commit your keys.

Check the environment:

```sh
uv run python --version            # → Python 3.10
uv run python -m agent_mbpp --help # → usage of the MBPP agent
```

#### Make rules

```sh
make install         # create .venv (Python 3.10.0) and install dependencies
make install_goinfre # same, but .venv is a symlink to ~/goinfre/.cache_agent_smith/venv
make run_gemini      # solve one MBPP task with Gemini (see MBPP below)
make lint            # check code style (flake8) and types (mypy)
make clean           # remove caches (__pycache__, .mypy_cache, .ruff_cache)
make fclean          # clean + remove the virtual environment
```

> On 42 computers, `~/goinfre` is local to each machine and may be wiped:
> if `uv` fails because `.venv` points to nothing, just run `make install_goinfre` again.

#### MBPP

Solve one MBPP task and write its `solution.json`:

```sh
uv run python -m agent_mbpp --task-file FILE --output FILE \
    --model-name NAME --provider-url URL [--debug LEVEL]
```

```text
-h, --help          show this help message and exit
--task-file FILE    task JSON dumped by the moulinette
--output FILE       where to write solution.json (the folder must exist)
--model-name NAME   model of the provider, e.g. "llama-3.3-70b"
--provider-url URL  base URL, e.g. "https://api.groq.com/openai/v1"
--debug LEVEL       off (default), summary, steps or full
```

Shortcut with Gemini (`TASK` and `OUTPUT` are optional):

```sh
make run_gemini TASK=mbpp_test/task_3_is_not_prime.json OUTPUT=mbpp_test/solution.json
```

Example tasks are in `mbpp_test/` (same format as the moulinette's dump).

#### Documentation

[subject](./docs/subject.md)
[gitbook Théaud Moga](https://tmoga.gitbook.io/doc-agent-smith)
