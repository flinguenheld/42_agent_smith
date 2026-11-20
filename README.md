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

Check the environment:

```sh
uv run python --version # → Python 3.10
make run                # → Hello from 42-agent-smith!
```

#### Make rules

```sh
make install         # create .venv (Python 3.10.0) and install dependencies
make install_goinfre # same, but .venv is a symlink to ~/goinfre/.cache_agent_smith/venv
make run             # run the program
make lint            # check code style (flake8) and types (mypy)
make clean           # remove caches (__pycache__, .mypy_cache, .ruff_cache)
make fclean          # clean + remove the virtual environment
```

> On 42 computers, `~/goinfre` is local to each machine and may be wiped:
> if `uv` fails because `.venv` points to nothing, just run `make install_goinfre` again.

#### Documentation

[subject](./docs/subject.md)
[gitbook Théaud Moga](https://tmoga.gitbook.io/doc-agent-smith)
