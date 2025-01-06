import os
import dotenv
import asyncio
import argparse
from rich.prompt import Prompt, Confirm
from rich import print
from .core import Agent
from .connectors import LLM, OpenAILLM
from .tools import Bash, Chat, Codegen, Interpreter
from .config import LovelaiceConfig


def run():
    dotenv.load_dotenv()
    config = LovelaiceConfig.load()

    parser = argparse.ArgumentParser("lovelaice", usage="lovelaice [options] query ...")
    parser.add_argument(
        "--config", action="store_true", help="Run configuration and exit"
    )
    parser.add_argument(
        "-f", "--file", action="store", help="Add a file to the context"
    )
    parser.add_argument(
        "-c",
        "--complete",
        action="store_true",
        help="Instead of full chat interaction, simply run completion on the input prompt.",
        default=False,
    )
    parser.add_argument(
        "-cf", "--complete-files",
        action="store",
        nargs="*",
        help="Similar to completion mode, but instead CLI, it will read these files and replace all instances of `+++` with a completion, using the previous content as prompt.",
        metavar="FILE",
        default=None,
    )
    parser.add_argument(
        "-w", "--watch",
        action="store_true",
        help="Used only with --complete-files, keep watching for file changes until stopped with Ctrl+C.",
        default=None,
    )
    parser.add_argument("query", nargs="*", default=None)

    args = parser.parse_args()

    llm = OpenAILLM(config.model, config.api_key, config.base_url)

    if args.config:
        configure(config)
        return

    if args.complete:
        asyncio.run(complete(args, config, llm))
        return

    if args.complete_files:
        asyncio.run(complete_files(args, config, llm))
        return

    agent = Agent(
        llm,
        tools=[Bash(), Chat(), Interpreter(), Codegen()],
    )

    if args.query:
        asyncio.run(run_once(args, config, agent))
    else:
        asyncio.run(run_forever(args, config, agent))


def configure(config: LovelaiceConfig):
    new_config = {}
    old_config = config.model_dump(mode="json")

    for field, info in config.model_fields.items():
        print(f"[yellow]{info.description}[/yellow]")
        value = Prompt.ask(field, default=old_config[field])

        if value is not None:
            new_config[field] = value

    print(new_config)

    if Confirm.ask("Are you happy with this configuration?"):
        new_config = LovelaiceConfig(**new_config)
        new_config.save()


async def complete(args, config: LovelaiceConfig, llm: LLM):
    prompt = " ".join(args.query)

    print(prompt, end="", flush=True)

    while True:
        generated = False

        async for chunk in llm.complete_stream(prompt, max_tokens=config.max_tokens):
            prompt += chunk
            print(chunk, end="", flush=True)

            if chunk:
                generated = True

        if not generated or len(prompt.split()) > config.min_words:
            break

    print()


async def _detect_file_changes(file, interval=1):
    last_modified = os.path.getmtime(file)

    while True:
        current_modified = os.path.getmtime(file)

        if current_modified != last_modified:
            return

        await asyncio.sleep(interval)


async def complete_files(args, config, llm: LLM):
    for file in args.complete_files:
        await _complete_file(file, args, llm)


async def _complete_file(file, args, config: LovelaiceConfig, llm: LLM):
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
            response = await llm.complete(prompt, max_tokens=config.max_tokens)
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


async def run_once(args, config: LovelaiceConfig, agent: Agent):
    prompt = " ".join(args.query)

    async for response in agent.query(prompt, max_tokens=config.max_tokens):
        print(response, end="", flush=True)

    print()


async def run_forever(args, config: LovelaiceConfig, agent: Agent):
    while True:
        try:
            prompt = input("> ")

            try:
                async for response in agent.query(prompt, max_tokens=config.max_tokens):
                    print(response, end="", flush=True)
            except asyncio.exceptions.CancelledError:
                print("(!) Cancelled")

            print("\n")
        except KeyboardInterrupt:
            break
        except EOFError:
            break
