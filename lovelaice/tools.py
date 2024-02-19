import subprocess
import importlib


class Tool:
    skip_use = False

    @property
    def name(self) -> str:
        return self.__class__.__name__

    @property
    def description(self) -> str:
        return self.__class__.__doc__

    def describe(self) -> str:
        return f"- {self.name}: {self.description}."

    def prompt(self, query) -> str:
        return query

    def use(self, query, response):
        pass

    def conclude(self, query, output):
        pass


class Chat(Tool):
    """
    When the user engages in general-purpose or casual conversation.
    """

    def __init__(self) -> None:
        self.skip_use = True


class Bash(Tool):
    """
    When the user requests some action in the filesystem or terminal,
    including git commands, or installing new applications or packages.
    """

    def prompt(self, query) -> str:
        return f"""
Given the following user query, generate a single bash command line
that performs the indicated functionality.

Reply only with the corresponding bash line.
Do not add any explanation.

Query: {query}
Command:
"""

    def use(self, query, response):
        response = response.strip("`")

        if response.startswith("bash"):
            response = response[4:]

        response = response.split("`")[0]
        response = [s.strip() for s in response.split("\n")]
        response = [s for s in response if s]

        response = ";".join(s for s in response)

        yield "Running the following code:\n"
        yield "$ "
        yield response
        yes = input("\n[y]es / [N]o ")

        if yes != "y":
            yield "(!) Operation cancelled by your request.\n"
            return

        yield "\n"

        p = subprocess.run(response, shell=True, stdout=subprocess.PIPE)
        yield p.stdout.decode("utf8")

    def conclude(self, query, output):
        return f"""
The user issued the following query:

Query: {query}

Given that query, you ran the following command which
Add license information here.
produced the given output:

---
{output}
---

If the user query is a question, answer it as succintly
as possible given the output.

If the user query was a request to do something,
explain briefly the result of the operation.
"""


class Interpreter(Tool):
    """
    When the user asks a mathematical question that can
    be solved with a simple Python function.
    """

    def prompt(self, query) -> str:
        return f"""
Given the following user query,
generate a single Python function named `solve`
and the necessary import statements
to perform the indicated functionality.

If you need secondary functions, name them starting with `_`.

Enclose the code in ```python and ```

Reply only with the corresponding Python code.
Do not add any explanation.
Do not execute the function.
Do not add any print statements.

Query: {query}
Function definition:
"""

    def use(self, query, response):
        code = []
        imports = []
        inside = False

        for line in response.split("\n"):
            if line.startswith("```python"):
                inside = True
            elif line.startswith("```"):
                inside = False
            elif inside:
                if line.startswith("import"):
                    imports.append(line.split()[1])
                else:
                    code.append(line)

        code.append("\nresult = solve()")
        code = "\n".join(code).strip()

        yield "Will run the following code:\n\n"
        yield code
        yes = input("\n\n[y]es / [N]o ")

        if yes != "y":
            yield "(!) Operation cancelled by your request.\n"
            return

        globals = {module: importlib.import_module(module) for module in imports}
        locals = {}
        exec(code, globals, locals)
        result = locals["result"]

        yield f"\nResult: {result}"


class Codegen(Tool):
    """
    When the user makes a general question about programming or
    explicitly asks to generate code in a given programming language.
    """

    def __init__(self) -> None:
        self.skip_use = True

    def prompt(self, query) -> str:
        return f"""
Answer the following user query about programming with
a general explanation in broad terms, followed by
one or more examples of code, as necessary.

Enclose all code examples in ``` with the corresponding
programming language identifier.

Query: {query}
"""
