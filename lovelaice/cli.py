import os
import dotenv
import asyncio
import argparse
import sys

from pydantic import BaseModel
from rich.prompt import Prompt, Confirm
from rich import print

from argo.cli import loop
from argo import LLM, Message

from .core import Lovelaice
from .config import LovelaiceConfig


def run():
    dotenv.load_dotenv()
    config = LovelaiceConfig.load()

    parser = argparse.ArgumentParser("lovelaice", usage="lovelaice [options] query ...")
    parser.add_argument("--version", action="store_true", help="Print version and exit")
    parser.add_argument(
        "--config", action="store_true", help="Run configuration and exit"
    )
    parser.add_argument(
        "-c",
        "--complete",
        action="store_true",
        help="Instead of full chat interaction, simply run completion on the input prompt.",
        default=False,
    )
    parser.add_argument(
        "-cf",
        "--complete-files",
        action="store",
        nargs="*",
        help="Similar to completion mode, but instead CLI, it will read these files and replace all instances of `+++` with a completion, using the previous content as prompt.",
        metavar="FILE",
        default=None,
    )
    parser.add_argument(
        "-w",
        "--watch",
        action="store_true",
        help="Used only with --complete-files, keep watching for file changes until stopped with Ctrl+C.",
        default=None,
    )
    parser.add_argument(
        "-f", "--file", action="store", help="Add a file to the context"
    )
    parser.add_argument(
        "-j", "--json", action="store_true", help="Force the reply to JSON mode"
    )

    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Runs in debug mode, e.g. more verbose.",
        default=False,
    )
    parser.add_argument("query", nargs="*", default=None)

    args = parser.parse_args()

    if args.config:
        configure(config)
        return

    def callback(chunk: str):
        print(chunk, end="")

    llm = LLM(
        model=config.model.name,
        api_key=config.model.api_key,
        base_url=config.model.base_url,
        callback=callback,
        verbose=args.verbose,
    )

    if args.complete:
        asyncio.run(complete(args, config, llm))
        return

    if args.complete_files:
        asyncio.run(complete_files(args, config, llm))
        return

    agent = Lovelaice(llm)

    if args.query:
        asyncio.run(run_once(args, config, agent))
    else:
        loop(agent)


def _build_config(model: type[BaseModel], old_config, indent=0):
    new_config = {}

    for field, info in model.model_fields.items():
        if isinstance(info.annotation, type) and issubclass(info.annotation, BaseModel):
            print(f"[purple]{indent * "  "}{field}[/purple]: {info.description}\n")
            value = _build_config(
                info.annotation, old_config.get(field, {}), indent + 1
            )
        else:
            print(f"[yellow]{indent * "  "}{info.description}[/yellow]")
            value = Prompt.ask(indent * "  " + field, default=str(old_config[field]))
            print()

        if value is not None:
            new_config[field] = value

    return new_config


def configure(config: LovelaiceConfig):
    old_config = config.model_dump(mode="json")
    new_config = _build_config(LovelaiceConfig, old_config)

    new_config = LovelaiceConfig(**new_config)
    print(new_config.model_dump(mode="json"))

    if Confirm.ask("Are you happy with this configuration?"):
        new_config.save()


async def complete(args, config: LovelaiceConfig, llm: LLM):
    prompt = " ".join(args.query)

    piped = sys.stdin.read()

    if piped:
        prompt = piped + "\n\n" + prompt

    print(prompt, end="", flush=True)
    await llm.complete(prompt, max_tokens=config.max_tokens)

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
        await _complete_file(file, args, config, llm)


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


async def run_once(args, config: LovelaiceConfig, agent: Lovelaice):
    prompt = " ".join(args.query)

    piped = sys.stdin.read()

    if piped:
        prompt = piped + "\n\n" + prompt

    async for m in agent.perform(Message.user(prompt)):
        pass

    print()
