import sys

from agent_smith.agent import Agent
from agent_smith.config import Config, ConfigError
from agent_smith.display import print_error, print_info
from agent_smith.llm_client import LLMClient, LLMClientError
from agent_smith.models import MBPPTaskInput
from agent_smith.prompt import build_task_message
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

    try:
        # config = Config("https://api.mistral.ai/v1/chat/completions")
        config = Config(
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "gemini-3.5-flash-lite",
            # "gemini-3.5-flash",
        )
        print(config)

        with Sandbox(None, None) as sandbox:
            agent = Agent(LLMClient(config), sandbox, task)
            prompt = build_task_message(task)
            print(prompt)

            aaa = agent.solve()
            print(aaa)

    except ConfigError as err:
        print_error("CONFIG", str(err))
        print(Config.usage(), file=sys.stderr)

    except LLMClientError as err:
        print_error("API", str(err))

    print("Hello Flo!")
