import shlex
import sys

from pydantic import ValidationError

from agent_smith.agent import Agent, progress_bars
from agent_smith.agent.prompt import build_system_prompt
from agent_smith.cli import CliArgs
from agent_smith.data import MBPP_SERVER_SCRIPT
from agent_smith.display import Display
from agent_smith.llm.client import LLMClient
from agent_smith.llm.config import Config, ConfigError
from agent_smith.models import MBPPTaskInput, SolutionOutput
from agent_smith.sandbox import Sandbox
from agent_smith.sandbox.manual import build_manual
from agent_smith.sandbox.mcp_client import McpClient, McpClientError


def solve(args: CliArgs) -> SolutionOutput:
    """Load the task, run the agent, and return its solution."""

    task = MBPPTaskInput.model_validate_json(args.task_file.read_text())
    config = Config(args.provider_url, args.model_name)

    # sys.executable: the server runs with our venv's Python.
    mcp = McpClient(shlex.join([sys.executable, MBPP_SERVER_SCRIPT]))
    tools = mcp.list_tools()
    prompt = build_system_prompt(build_manual(tools))

    with Sandbox(tools=mcp.tool_handlers(tools)) as sandbox:
        agent = Agent(LLMClient(config), sandbox, task, prompt)

        with progress_bars(agent):
            return agent.solve()


def main() -> int:
    """Entry point: python -m agent_mbpp --task-file ... --output ...

    Run one MBPP task; return the process exit code.
    """

    args = CliArgs.parse("agent_mbpp")
    Display.set_debug_level(args.debug)
    Display.debug(f"--- {Display.level.name} ---")
    try:
        solution = solve(args)

    except (OSError, ValidationError) as err:
        Display.error("TASK FILE", str(err))
        return 1

    except ConfigError as err:
        Display.error("CONFIG", str(err))
        return 1

    except McpClientError as err:
        Display.error("MCP", str(err))
        return 1

    args.output.write_text(solution.model_dump_json(indent=2))
    Display.debug(solution, "Solution")

    Display.debug("--- END ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
