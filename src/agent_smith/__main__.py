import sys

from agent_smith.config import Config, ConfigError
from agent_smith.display import print_error

if __name__ == "__main__":
    try:
        config = Config("https://api.mistral.ai/v1/chat/completions")

        print(config)

    except ConfigError as err:
        print_error(str(err))
        print(Config.usage(), file=sys.stderr)

    print("Hello Flo!")
