import subprocess
import abc
from mistralai.client import MistralClient
from mistralai.models.chat_completion import ChatMessage
from functools import wraps


SYSTEM_PROMPT = """
You are Lovelaice, a helpful AI agent that runs in the
terminal. You can do many things, from general-purpose chat
to helping with concrete tasks that require access to the filesystem.
You can run programs at the request of the user, and write
code for them.
"""

TOOLS_PROMPT = """
These are some of the tools you have access to:

{tools}

According to the following query, reply only with the name of the tool that
is most appropriate to solve the problem. Do not reply anything else.

Query: {query}
Tool:
"""


class Tool(abc.ABC):
    skip_use = False

    @abc.abstractproperty
    def name(self) -> str:
        pass

    @abc.abstractproperty
    def description(self) -> str:
        pass

    def describe(self) -> str:
        return f"- {self.name}: {self.description}."

    @abc.abstractmethod
    def prompt(self, query) -> str:
        pass

    @abc.abstractmethod
    def use(self, query, response):
        pass

    @abc.abstractmethod
    def conclude(self, query, output):
        pass


class Bash(Tool):
    @property
    def name(self):
        return "bash"

    @property
    def description(self):
        return "when the user requests some action in the filesystem or terminal, including git commands"

    def prompt(self, query) -> str:
        return f"""
Given the following user query, generate a bash command line
that performs the indicated functionality.

Reply only with the corresponding bash line.
Do not add any explanation.

Query: {query}
Bash line:
"""

    def use(self, query, response):
        if response.startswith("```bash"):
            response = response[7:-3]

        elif response[0] == '`':
            response = response[1:-1]

        response = [s.strip() for s in response.split("\n")]
        response = [s for s in response if s]

        response = ";".join(s for s in response)

        yield "Running the following code:\n"
        yield "$ "
        yield response
        yield "\n\n"

        p = subprocess.run(response, shell=True, stdout=subprocess.PIPE)
        yield p.stdout.decode('utf8')

    def conclude(self, query, output):
        return f"""
The following is an excerpt of the output from a bash session:

---
{output}
---

Given the previous output, answer the following user query
as succintly as possible.

Query: {query}
Answer:
"""


class Chat(Tool):
    def __init__(self) -> None:
        self.skip_use = True

    @property
    def name(self):
        return "chat"

    @property
    def description(self):
        return "when the user engages in general-purpose or casual conversation"

    def prompt(self, query) -> str:
        return query

    def use(self, query, response):
        raise NotImplementedError()

    def conclude(self, query, response):
        raise NotImplementedError()


TOOLS = [Bash(), Chat()]
TOOLS_DIR = {t.name: t for t in TOOLS}
TOOLS_LINE = "\n".join(t.describe() for t in TOOLS)


class Question:
    def __init__(self, q:str) -> None:
        self.q = q


def query(
    prompt: str,
    client: MistralClient,
    model: str = "mistral-small",
    system_prompt=SYSTEM_PROMPT,
    use_tool=None,
):
    if use_tool is None:
        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=TOOLS_PROMPT.format(query=prompt, tools=TOOLS_LINE))
        ]

        tool_name = client.chat(model, messages).choices[0].message.content
        tool_name = tool_name.split()[0]

        yield from query(prompt, client, model, system_prompt, use_tool=tool_name)

    else:
        tool: Tool = TOOLS_DIR[use_tool]

        if tool.name != "chat":
            yield f":: Using {tool.name}\n\n"

        messages = [
            ChatMessage(role="system", content=system_prompt),
            ChatMessage(role="user", content=tool.prompt(prompt))
        ]

        if tool.skip_use:
            for response in client.chat_stream(model, messages):
                yield response.choices[0].delta.content

        else:
            response = client.chat(model, messages).choices[0].message.content
            output = []

            for line in tool.use(prompt, response):
                output.append(line)
                yield line

            output = "\n".join(output)

            messages = [
                ChatMessage(role="system", content=system_prompt),
                ChatMessage(role="user", content=tool.conclude(prompt, output))
            ]

            yield "\n"

            for response in client.chat_stream(model, messages):
                yield response.choices[0].delta.content



def prompt(function):
    client = MistralClient()

    @wraps(function)
    def wrapper(*args, **kwargs):
        template: str = function(*args, **kwargs)
        return query(template, client)

    return wrapper
