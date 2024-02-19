import dotenv
import asyncio
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
        asyncio.run(run_once(args, agent))
    else:
        asyncio.run(run_forever(args, agent))


async def run_once(args, agent: Agent):
    prompt = " ".join(args.query)

    async for response in agent.query(prompt):
        print(response, end="", flush=True)

    print()


async def run_forever(args, agent: Agent):
    while True:
        try:
            prompt = input("> ")

            try:
                async for response in agent.query(prompt):
                    print(response, end="", flush=True)
            except KeyboardInterrupt:
                print("(!) Cancelled")

            print("\n")
        except KeyboardInterrupt:
            break