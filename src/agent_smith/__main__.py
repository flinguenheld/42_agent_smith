from agent_smith.agent import Agent
from agent_smith.agent.prompt import build_task_message
from agent_smith.display import Display
from agent_smith.llm.client import LLMClient, LLMClientError
from agent_smith.llm.config import Config, ConfigError
from agent_smith.models import MBPPTaskInput
from agent_smith.sandbox import Sandbox

if __name__ == "__main__":
    task = MBPPTaskInput(
        task_id=2,
        task_definition="Write a function to find the shared elements "
        "from two lists.",
        function_definition="def similar_elements(a, b):",
        test_list=[
            "assert set(similar_elements((3,4,5,6),(5,7,4,10))) == set((4,5))",
        ],
    )
    Display.debug("ON --")

    try:
        # config = Config("https://api.mistral.ai/v1")
        config = Config(
            "https://generativelanguage.googleapis.com/v1beta/openai",
            "gemini-3.5-flash-lite",
            # "gemini-3.5-flash",
        )
        Display.debug(str(config), "Config")

        with Sandbox(None, None) as sandbox:
            agent = Agent(LLMClient(config), sandbox, task)
            prompt = build_task_message(task)
            Display.debug(prompt, "Initial prompt")

            solution = agent.solve()
            Display.debug(solution, "Solution")

    except ConfigError as err:
        Display.error("CONFIG", str(err))

    except LLMClientError as err:
        Display.error("API", str(err))

    Display.debug("END --")
