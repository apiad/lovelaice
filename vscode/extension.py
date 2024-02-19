import os
os.environ['LOG_LEVEL'] = "INFO"

import vscode as vs
from lovelaice.core import Agent
from lovelaice.connectors import MistralLLM
from lovelaice.tools import Chat


ext = vs.Extension(
    name="Lovelaice", metadata=vs.ExtensionMetadata(version="0.1.8", publisher="apiad"),
    config=[
        vs.Config("Mistral API Key", "An API key for Mistral.ai", str)
    ]
)



@ext.event
async def on_activate():
    vs.log("Lovelaice is online!")


@ext.command("Lovelaice", keybind="Ctrl+Shift+L")
async def lovelaice(ctx: vs.Context):
    query_box = vs.InputBox("Ask Lovelaice", place_holder="Your question...")
    await ctx.show(query_box)

    api_key = await ctx.workspace.get_config_value("Mistral API Key")
    agent = Agent(MistralLLM("mistral-small", api_key), tools=[Chat()])
    response = []

    for r in agent.query(query_box.value):
        response.append(r)

    response = "".join(r)

    return await ctx.show(vs.InfoMessage(response))


ext.run()
