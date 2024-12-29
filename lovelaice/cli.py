import os
import dotenv
import asyncio
import argparse
from .core import Agent
from .connectors import OpenAILLM
from .tools import Bash, Chat, Codegen, Interpreter


def run():
    dotenv.load_dotenv()

    parser = argparse.ArgumentParser("lovelaice")
    parser.add_argument(
        "-f", "--file", action="store", help="Add a file to the context"
    )
    parser.add_argument(
        "-m",
        "--model",
        action="store",
        help="Model to use",
        default=os.getenv("LOVELAICE_MODEL"),
    )
    parser.add_argument(
        "--base-url",
        action="store",
        help="API base URL to use",
        default=os.getenv("LOVELAICE_BASE_URL"),
    )
    parser.add_argument(
        "--api-key",
        action="store",
        help="API key to use",
        default=os.getenv("LOVELAICE_API_KEY"),
    )
    parser.add_argument("query", nargs="*", default=None)

    args = parser.parse_args()
    agent = Agent(
        OpenAILLM(args.model, args.api_key, args.base_url),
        tools=[Bash(), Chat(), Interpreter(), Codegen()],
    )

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
            except asyncio.exceptions.CancelledError:
                print("(!) Cancelled")

            print("\n")
        except KeyboardInterrupt:
            break
        except EOFError:
            break
