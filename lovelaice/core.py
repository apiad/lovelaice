from .connectors import LLM
from .models import Message
from .tools import Chat, Tool


SYSTEM_PROMPT = """
You are Lovelaice, a helpful AI agent that runs in the
user terminal. You can do many things, from casual chat
to helping with concrete tasks that require access to the user filesystem.
You can run programs at the request of the user, and write
code for them.
You have access to the Internet and can answer queries that
require searching online.
"""

TOOLS_PROMPT = """
These are some of the tools you have access to:

{tools}

According to the following query, reply only with the name of the tool that
is most appropriate to solve the problem. Do not reply anything else.

Query: {query}
Tool:
"""


class Agent:
    def __init__(self, client: LLM, tools: list[Tool]) -> None:
        self.client = client
        self.tools = tools
        self.tools_dir = {t.name: t for t in tools}
        self.tools_line = "\n".join(t.describe() for t in tools)

    async def query(
        self,
        prompt: str,
        use_tool=None,
        **kwargs,
    ):
        if use_tool is None:
            messages = [
                Message(role="system", content=SYSTEM_PROMPT),
                Message(
                    role="user",
                    content=TOOLS_PROMPT.format(query=prompt, tools=self.tools_line),
                ),
            ]

            tool_name = await self.client.chat(messages, **kwargs)
            tool_name = tool_name.split()[0].strip(",.:")

            async for response in self.query(prompt, use_tool=tool_name, **kwargs):
                yield response

        else:
            if use_tool not in self.tools_dir:
                tool: Tool = Chat()
            else:
                tool: Tool = self.tools_dir[use_tool]

            if tool.name != "Chat":
                yield f":: Using {tool.name}\n\n"

            messages = [Message(role="user", content=tool.prompt(prompt))]

            if tool.skip_use:
                async for response in self.client.chat_stream(messages, **kwargs):
                    yield response

            else:
                response = await self.client.chat(messages, **kwargs)
                output = []

                for line in tool.use(prompt, response):
                    output.append(line)
                    yield line

                output = "\n".join(output)
                conclusion = tool.conclude(prompt, output)

                if conclusion is None:
                    return

                messages = [Message(role="user", content=conclusion)]

                yield "\n"

                async for response in self.client.chat_stream(messages, **kwargs):
                    yield response
