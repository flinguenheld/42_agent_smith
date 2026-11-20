import sys

from agent_smith.config import Config, ConfigError
from agent_smith.display import print_error
from agent_smith.llm_client import LLMClient, LLMClientError

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
        answer = client.ask("How are you?")

        print(answer)

    except ConfigError as err:
        print_error("CONFIG", str(err))
        print(Config.usage(), file=sys.stderr)

    except LLMClientError as err:
        print_error("API", str(err))

    print("Hello Flo!")
