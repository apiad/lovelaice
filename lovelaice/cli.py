import dotenv
import argparse
from .core import Agent
from .connectors import MistralLLM
from .tools import Bash, Chat, Interpreter


def run():
    dotenv.load_dotenv()

    parser = argparse.ArgumentParser("lovelaice")
    parser.add_argument(
        "-f", "--file", action="store", help="Add a file to the context"
    )
    parser.add_argument("query", nargs="*", default=None)

    args = parser.parse_args()
    agent = Agent(MistralLLM("mistral-small"), tools=[Bash(), Chat(), Interpreter()])

    if args.query:
        run_once(args, agent)
    else:
        run_forever(args, agent)


def run_once(args, agent):
    prompt = " ".join(args.query)

    for response in agent.query(prompt):
        print(response, end="", flush=True)

    print()


def run_forever(args, agent):
    while True:
        try:
            prompt = input("> ")

            try:
                for response in agent.query(prompt):
                    print(response, end="", flush=True)
            except KeyboardInterrupt:
                print("(!) Cancelled")

            print("\n")
        except KeyboardInterrupt:
            break