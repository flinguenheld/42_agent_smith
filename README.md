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
uv sync                    # creates .venv with Python 3.10.0 and installs dependencies
```

Check the environment:

```sh
uv run python --version    # → Python 3.10.0
uv run 42-agent-smith      # → Hello from 42-agent-smith!
```
