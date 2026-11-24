import sys

from pydantic import ValidationError

from agent_smith.agent import Agent
from agent_smith.cli import CliArgs
from agent_smith.display import Display
from agent_smith.llm.client import LLMClient
from agent_smith.llm.config import Config, ConfigError
from agent_smith.models import MBPPTaskInput, SolutionOutput
from agent_smith.sandbox import Sandbox


def solve(args: CliArgs) -> SolutionOutput:
    """Load the task, run the agent, and return its solution."""

    task = MBPPTaskInput.model_validate_json(args.task_file.read_text())
    config = Config(args.provider_url, args.model_name)

    with Sandbox() as sandbox:
        agent = Agent(LLMClient(config), sandbox, task)

        # solve() makes a new Deadline: the lambda must read agent.deadline
        # at each refresh, not keep the old one.
        with Display.progress(
            agent.deadline.seconds,
            lambda: agent.deadline.elapsed,
        ):
            return agent.solve()


def main() -> int:
    """Entry point: python -m agent_mbpp --task-file ... --output ...

    Run one MBPP task; return the process exit code.
    """

    args = CliArgs.parse("agent_mbpp")
    Display.set_debug_level(args.debug)
    Display.debug("--- ON ---")
    try:
        solution = solve(args)

    except (OSError, ValidationError) as err:
        Display.error("TASK FILE", str(err))
        return 1

    except ConfigError as err:
        Display.error("CONFIG", str(err))
        return 1

    args.output.write_text(solution.model_dump_json(indent=2))
    Display.debug(solution, "Solution", full=True)

    Display.debug("--- END ---")
    return 0


if __name__ == "__main__":
    sys.exit(main())
