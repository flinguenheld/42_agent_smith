import sys

from agent_smith.config import Config, ConfigError
from agent_smith.display import print_error, print_info
from agent_smith.llm_client import LLMClient, LLMClientError
from agent_smith.sandbox import Sandbox

if __name__ == "__main__":
    try:
        # config = Config("https://api.mistral.ai/v1/chat/completions")
        config = Config(
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            "gemini-3.5-flash-lite",
            # "gemini-3.5-flash",
        )
        print(config)

        client = LLMClient(config)
        messages = [
            {"role": "system", "content": "You are a Python expert."},
            {"role": "user", "content": "How are you?"},
        ]
        answer = client.ask(messages)
        print(answer)

        with Sandbox(None, None) as sandbox:
            blah = sandbox.run("print('hello')")
            # print_info(blah.to_observation())
            print(blah)

    except ConfigError as err:
        print_error("CONFIG", str(err))
        print(Config.usage(), file=sys.stderr)

    except LLMClientError as err:
        print_error("API", str(err))

    print("Hello Flo!")
