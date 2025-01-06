import os
import dotenv
import asyncio
import argparse
from .core import Agent
from .connectors import LLM, OpenAILLM
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
    parser.add_argument(
        "-c",
        "--complete",
        action="store_true",
        help="Instead of full chat interaction, simply run completion on the input prompt.",
        default=False,
    )
    parser.add_argument(
        "--complete-files",
        action="store",
        nargs="*",
        help="Similar to completion mode, but instead CLI, it will read these files and replace all instances of `+++` with a completion, using the previous content as prompt.",
        default=None,
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Used only with --complete-files, keep watching for file changes until stopped with Ctrl+C.",
        default=None,
    )
    parser.add_argument(
        "--max-tokens",
        action="store",
        type=int,
        help="Max number of tokens allowed to generate. Defaults to 2048.",
        default=int(os.getenv("LOVELAICE_MAX_TOKENS", 2048)),
    )
    parser.add_argument(
        "--min-words",
        action="store",
        type=int,
        help="Only for completion mode, keep running completion until at least this number of words are generated.",
        default=0,
    )
    parser.add_argument("query", nargs="*", default=None)

    args = parser.parse_args()

    llm = OpenAILLM(args.model, args.api_key, args.base_url)

    if args.complete:
        asyncio.run(complete(args, llm))
        return

    if args.complete_files:
        asyncio.run(complete_files(args, llm))
        return

    agent = Agent(
        llm,
        tools=[Bash(), Chat(), Interpreter(), Codegen()],
    )

    if args.query:
        asyncio.run(run_once(args, agent))
    else:
        asyncio.run(run_forever(args, agent))


async def complete(args, llm: LLM):
    prompt = " ".join(args.query)

    print(prompt, end="", flush=True)

    while True:
        generated = False

        async for chunk in llm.complete_stream(prompt, max_tokens=args.max_tokens):
            prompt += chunk
            print(chunk, end="", flush=True)

            if chunk:
                generated = True

        if not generated or len(prompt.split()) > args.min_words:
            break

    print()


async def _detect_file_changes(file, interval=1):
    last_modified = os.path.getmtime(file)

    while True:
        current_modified = os.path.getmtime(file)

        if current_modified != last_modified:
            return

        await asyncio.sleep(interval)


async def complete_files(args, llm: LLM):
    for file in args.complete_files:
        await _complete_file(file, args, llm)


async def _complete_file(file, args, llm: LLM):
    while True:
        prompt = []
        complete = False

        with open(file) as fp:
            for line in fp:
                if line.strip().endswith("+++"):
                    if line.strip() != "+++":
                        prompt.append(line.replace("+++", ""))
                    complete = True
                    break
                else:
                    prompt.append(line)

        prompt = "\n".join(prompt)

        if prompt and complete:
            print(f"Running completion on {file}...")
            response = await llm.complete(prompt, max_tokens=args.max_tokens)
            print(f"Done with completion on {file}.")

            lines = open(file).readlines()

            with open(file, "w") as fp:
                for line in lines:
                    if "+++" in line:
                        line = line.replace("+++", response)

                    fp.write(line)
        else:
            print(f"Nothing to do in {file}.")

        if args.watch:
            print(f"Waiting for changes on {file}.")
            await _detect_file_changes(file)
        else:
            return


async def run_once(args, agent: Agent):
    prompt = " ".join(args.query)

    async for response in agent.query(prompt, max_tokens=args.max_tokens):
        print(response, end="", flush=True)

    print()


async def run_forever(args, agent: Agent):
    while True:
        try:
            prompt = input("> ")

            try:
                async for response in agent.query(prompt, max_tokens=args.max_tokens):
                    print(response, end="", flush=True)
            except asyncio.exceptions.CancelledError:
                print("(!) Cancelled")

            print("\n")
        except KeyboardInterrupt:
            break
        except EOFError:
            break
