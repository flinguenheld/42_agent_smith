from agent_smith.agent.agent import Agent
from agent_smith.display import Display
from agent_smith.display.progress import TaskProgress


def progress_bars(agent: Agent) -> TaskProgress:
    """Return the time, iteration and token bars that follow agent live."""

    # solve() makes a new Deadline and TokenBudget: each lambda must read
    # agent.<attr> at each refresh, not keep the old object.
    bars = Display.progress()
    bars.add_bar(
        "Time",
        agent.deadline.seconds,
        "seconds",
        lambda: agent.deadline.elapsed,
    )
    bars.add_bar(
        "Iterations",
        agent.max_iterations,
        "",
        lambda: agent.iteration,
    )
    bars.add_bar(
        "Token output",
        agent.budget.max_output,
        "tokens",
        lambda: agent.budget.output_used,
    )
    bars.add_bar(
        "Token input",
        agent.budget.max_input,
        "tokens",
        lambda: agent.budget.input_used,
    )
    return bars
