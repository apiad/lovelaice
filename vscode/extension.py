import os
os.environ['LOG_LEVEL'] = "ERROR"

import vscode as vs
from lovelaice.core import Agent
from lovelaice.connectors import MistralLLM
from lovelaice.tools import Chat
import logging


ext = vs.Extension(
    name="Lovelaice", metadata=vs.ExtensionMetadata(version="0.1.8", publisher="apiad"),
    config=[
        vs.Config("mistral-api-key", "An API key for Mistral.ai", str)
    ]
)


@ext.event
async def on_activate():
    vs.log("Lovelaice is online!")


@ext.command("Lovelaice: General Query", keybind="Ctrl+Shift+L")
async def lovelaice(ctx: vs.Context):
    query_box = vs.InputBox("Ask Lovelaice", place_holder="Your question...")

    api_key = await ctx.workspace.get_config_value("mistral-api-key")
    agent = Agent(MistralLLM("mistral-small", api_key), tools=[Chat()])

    res = await ctx.show(query_box)
    if not res:
        return

    response = []

    async for r in agent.query(res):
        response.append(r)

    response = "".join(r)

    return await ctx.show(vs.InfoMessage(response))


ext.run()
